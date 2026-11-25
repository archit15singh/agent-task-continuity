"""Live two-stage handoff with public upstream code and an out-of-band grader."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

from continuity.runner import run, runtime_command
from continuity.workspace import git
from .run import CASES, EVALS, PROJECT, check_argv, download, execute, invoke, sha

REPRO = "continuity-live-repro.py"
NOTE = "continuity-live-note.md"
TASKS = {
    "click": (
        "Add an optional context_settings mapping to CliRunner.invoke. Its keys become "
        "context kwargs and override command defaults, while invoke's own color argument "
        "keeps its existing meaning. Leave unrelated code alone."
    ),
    "packaging": (
        "Fix free-threaded CPython wheel tags when a generic ABI precedes the first "
        "version-specific ABI, or when abi3t appears alone. The first version-specific "
        "CPython ABI or abi3t decides. A recognized version-specific CPython ABI without "
        "a t flag still decides it is not threaded. Ordinary CPython retains abi3 tags."
    ),
    "attrs": (
        "In attr._funcs.astuple, skip expensive has() lookups for dictionary keys and "
        "values whose exact type belongs to _ATOMIC_TYPES. Preserve dict results, exact "
        "types of subclasses, and recursion into attrs class instances for active options."
    ),
}


def source_prompt(case):
    return (
        f"This is stage one of a coding handoff. Objective: {TASKS[case['id']]}\n"
        f"Inspect {case['source']}. Write only {REPRO} and {NOTE} at the repository root. "
        f"{REPRO} must be a standalone, small Python source regression. Insert the checkout's "
        "src directory into sys.path before project imports, then make an assertion about the "
        "requested behavior. It should exit 1 against this checkout and 0 after the fix. "
        "For a performance-only change, assert the exact-type probe behavior with a mock. "
        f"Write {NOTE} with the concrete next edit and the command to check it. "
        "Do not edit the implementation, inspect outside the repository, use the network, "
        "create commits, or add any other files."
    )


def replacement_objective(case):
    return (
        f"{TASKS[case['id']]} Edit only {case['source']}; leave the restored {REPRO} "
        "and the note intact. Complete the implementation in the working tree. "
        "Use public source within this checkout and the prior note. Do not access Git history, "
        "network resources, other workspaces, external services, or credentials."
    )


def read_summary(log):
    counts = {}
    input_tokens = output_tokens = cached_tokens = 0
    rate_limited = False
    provider_error = None
    for line in log.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        event_type = event.get("type", "")
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}", event_type):
            continue
        counts[event_type] = counts.get(event_type, 0) + 1
        usage = event.get("usage", {})
        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)
        cached_tokens += usage.get("cached_input_tokens", 0)
        error = event.get("error", {})
        if isinstance(error, dict):
            rate_limited |= error.get("status") == 429
            error_type = error.get("type")
            if isinstance(error_type, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,48}", error_type):
                provider_error = error_type
    return {
        "runtime_events": counts, "reported_input_tokens": input_tokens,
        "reported_cached_input_tokens": cached_tokens, "reported_output_tokens": output_tokens,
        "provider_rate_limited": rate_limited, "provider_error_type": provider_error,
    }


def worker_environment(endpoint):
    env = dict(os.environ)
    if endpoint:
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps({
            "provider": {"continuity-local": {
                "npm": "@ai-sdk/openai-compatible", "name": "Local Ollama",
                "options": {"baseURL": endpoint},
                "models": {"qwen3:4b": {
                    "name": "Qwen3 4B", "limit": {"context": 16384, "output": 2048}, "tool_call": True,
                }},
            }},
            "permission": {
                "*": "deny", "read": "allow", "glob": "allow", "grep": "allow", "edit": "allow",
                "list": "allow", "external_directory": "deny",
            },
        })
    return env


def staged_files(workspace):
    changed = git(workspace, "diff", "--name-only", "-z", "HEAD").decode().split("\0")
    untracked = git(workspace, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    return sorted(set(changed + untracked) - {""})


def live_case(case, temp, source_model, runtime, model, timeout):
    source = download(case, temp / "source", reference=False)
    db = temp / "ledger.db"
    before_log, after_log = temp / "first.log", temp / "replacement.log"
    first = run(runtime_command("codex", source_prompt(case), source_model), source,
                seconds=timeout, log=before_log)
    first.update(read_summary(before_log))
    scope = staged_files(source)
    first["artifacts"] = scope
    report = {
        "id": case["id"], "split": case["split"], "base": case["base"], "source": first,
        "replacement": None, "grade": {"complete": False},
    }
    if first["exit_code"] or scope != sorted([NOTE, REPRO]):
        report["grade"]["failure"] = "source worker did not produce exactly the scoped files"
        return report
    note = (source / NOTE).read_bytes()
    repro = (source / REPRO).read_bytes()
    baseline = execute([sys.executable, REPRO], cwd=source)
    report["grade"]["repro_baseline_exit"] = baseline.returncode
    report["grade"]["repro_sha256"] = sha(repro)
    report["grade"]["note_sha256"] = sha(note)
    if baseline.returncode != 1 or b"AssertionError" not in baseline.stderr:
        report["grade"]["failure"] = "source reproduction did not fail with an assertion on the base"
        return report
    task = invoke(db, "start", source, "--objective", replacement_objective(case))
    task_id, token = task["task"], task["token"]
    checkpoint = invoke(db, "checkpoint", task_id, "--include", REPRO, "--include", NOTE,
                        "--note", note.decode(), owner=token)
    destination = temp / "replacement"
    # Invoke the shipping continuation CLI. Its exit code can mirror a runtime failure, so read
    # the receipt on stdout and preserve the failed attempt in the public aggregate.
    env = dict(os.environ, CONTINUITY_OWNER=token)
    command = [
        sys.executable, "-m", "continuity", "--db", str(db), "continue", task_id,
        "--into", str(destination), "--runtime", runtime, "--timeout", str(timeout),
        "--log", str(after_log),
    ]
    if model:
        command.extend(["--model", model])
    completed = execute(command, env=env, timeout=timeout + 60)
    try:
        handoff = json.loads(completed.stdout)
    except ValueError:
        report["grade"]["failure"] = "continuation CLI did not return a handoff receipt"
        return report
    replacement = handoff["run"]
    report["replacement"] = {
        "runtime": runtime, **replacement,
        **(read_summary(after_log) if after_log.exists() else {}),
    }
    current_files = staged_files(destination)
    grader = execute(check_argv(case), cwd=destination)
    after_repro = execute([sys.executable, REPRO], cwd=destination) if (
        (destination / REPRO).is_file()
    ) else None
    native = execute([sys.executable, str(EVALS / "native_tests.py"), case["native_test"]],
                     cwd=destination)
    report["grade"].update({
        "checkpoint_sha256": checkpoint["digest"], "restored_repro": (
            (destination / REPRO).is_file() and (destination / REPRO).read_bytes() == repro
        ),
        "restored_note": (destination / NOTE).is_file() and (destination / NOTE).read_bytes() == note,
        "scope_exact": current_files == sorted([case["source"], NOTE, REPRO]),
        "source_predicate_exit": grader.returncode,
        "source_predicate_log_sha256": sha(grader.stdout + grader.stderr),
        "repro_after_exit": after_repro.returncode if after_repro else None,
        "native_exit": native.returncode,
        "native_summary": (native.stdout + native.stderr).decode(errors="replace").splitlines()[-1:],
        "changed_source_sha256": sha((destination / case["source"]).read_bytes()),
    })
    grade = report["grade"]
    grade["complete"] = (
        runtime == "opencode" and replacement["exit_code"] == 0 and grade["restored_repro"]
        and grade["restored_note"] and grade["scope_exact"] and grade["source_predicate_exit"] == 0
        and grade["repro_after_exit"] == 0 and grade["native_exit"] == 0
    )
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--set", choices=("development", "held-out"), required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--source-model", default="gpt-6.2-sol")
    cli.add_argument("--runtime", choices=("codex", "opencode"), default="opencode")
    cli.add_argument("--model")
    cli.add_argument("--local-endpoint")
    cli.add_argument("--timeout", type=int, default=180)
    args = cli.parse_args()
    if args.local_endpoint:
        os.environ["OPENCODE_CONFIG_CONTENT"] = worker_environment(args.local_endpoint)[
            "OPENCODE_CONFIG_CONTENT"
        ]
    reports = []
    with tempfile.TemporaryDirectory(prefix="continuity-live-") as directory:
        for case in CASES:
            if case["split"] != args.set:
                continue
            temp = Path(directory) / case["id"]
            temp.mkdir()
            report = live_case(case, temp, args.source_model, args.runtime, args.model, args.timeout)
            reports.append(report)
            print(f"{case['id']}: {'pass' if report['grade']['complete'] else 'incomplete'}",
                  flush=True)
    document = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_commit": git(PROJECT, "rev-parse", "HEAD").decode().strip(), "set": args.set,
        "python": platform.python_version(), "source_model_requested": args.source_model,
        "replacement_runtime": args.runtime, "replacement_model_requested": args.model,
        "worker_timeout_seconds": args.timeout,
        "codex": execute(["codex", "--version"]).stdout.decode().strip(),
        "opencode": execute(["opencode", "--version"]).stdout.decode().strip()
                    if args.runtime == "opencode" else None,
        "cases": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
