"""Evaluate matched Codex and OpenCode replacements from three frozen task artifacts."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from continuity.runner import run, runtime_command
from continuity.workspace import git
from .live import NOTE, REPRO, read_summary, staged_files
from .provider_trace import trace_provider
from .run import EVALS, PROJECT, download, execute, invoke, sha

FIXTURE = EVALS / "fixtures" / "paired"
MODEL = "continuity-paired:8b"
TIMEOUT = 180
CASES = json.loads((FIXTURE / "cases.json").read_text())


def packet_digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def oracle(case, workspace):
    checked = execute([sys.executable, EVALS / "paired_oracle.py", case["id"]], cwd=workspace, timeout=20)
    return (json.loads(checked.stdout) if checked.returncode == 0 else None, checked.returncode)


def repro(workspace):
    checked = execute([sys.executable, REPRO], cwd=workspace, timeout=20)
    return {"exit": checked.returncode, "assertion": b"AssertionError" in checked.stderr}


def native(case, workspace):
    modules = {}
    for name in case["native_tests"]:
        checked = execute([sys.executable, EVALS / "native_tests.py", name], cwd=workspace, timeout=90)
        output = (checked.stdout + checked.stderr).decode(errors="replace").splitlines()
        modules[name] = {"exit": checked.returncode,
                         "test_summary": [line for line in output if re.fullmatch(
                             r"[0-9]+ (?:passed|failed|skipped|errors?).* in [0-9.]+s", line,
                         )][-1:]}
    return modules


def seed(case, workspace):
    (workspace / REPRO).write_bytes((FIXTURE / (case["id"] + ".py")).read_bytes())
    (workspace / NOTE).write_text(case["note"] + "\n")


def calibrate(case, root):
    root.mkdir()
    reference = download(case, root / "control", reference=True)
    seed(case, reference)
    baseline_repro = repro(reference)
    baseline, baseline_exit = oracle(case, reference)
    base_tests = native(case, reference)
    git(reference, "checkout", "--quiet", "--detach", case["reference"])
    expected, reference_exit = oracle(case, reference)
    reference_repro = repro(reference)
    reference_tests = native(case, reference)

    assert baseline_exit == reference_exit == 0 and baseline.keys() == expected.keys(), case["id"]
    differences = [key for key, value in expected.items() if baseline[key] != value]
    assert differences and baseline_repro == {"exit": 1, "assertion": True}, (case["id"], baseline_repro)
    assert reference_repro["exit"] == 0 and all(report["exit"] == 0 for report in reference_tests.values()), (
        case["id"], reference_repro, reference_tests,
    )
    assert all(report["exit"] == 0 for report in base_tests.values()), (case["id"], base_tests)
    return expected, {
        "id": case["id"], "repository": case["repository"], "parent": case["base"], "reference": case["reference"],
        "parent_repro": baseline_repro, "reference_repro": reference_repro,
        "parent_native": base_tests, "reference_native": reference_tests,
        "hidden_probe_count": len(expected), "parent_hidden_disagreements": len(differences),
        "reference_hidden_sha256": packet_digest(expected),
    }


def local_provider_metadata(endpoint):
    parsed = urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/v1":
        raise ValueError("Provider must be an HTTP loopback endpoint ending in /v1")
    root = endpoint.removesuffix("/v1")
    with urlopen(root + "/api/tags", timeout=5) as connection:
        tags = json.load(connection)["models"]
    model = next(tag for tag in tags if tag["name"] == MODEL)
    request = Request(root + "/api/show", data=json.dumps({"model": MODEL}).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=5) as connection:
        metadata = json.load(connection)
    settings = metadata["parameters"]
    assert re.search(r"(?m)^num_ctx\s+16384\s*$", settings)
    assert re.search(r"(?m)^num_predict\s+2048\s*$", settings)
    return {"alias": MODEL, "digest": model["digest"], "settings": settings,
            "family": model["details"]["family"], "quantization": model["details"]["quantization_level"],
            "base_model_digest": next((tag["digest"] for tag in tags if tag["name"] == "qwen3:8b"), None)}


def warm_provider(endpoint):
    request = Request(
        endpoint.removesuffix("/v1") + "/api/generate",
        data=json.dumps({"model": MODEL, "keep_alive": "30m"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as connection:
        assert json.load(connection)["done"]


def worker_command(runtime, prompt, relay, state):
    environment = {"PATH": os.environ["PATH"], "LANG": "en_US.UTF-8"}
    if runtime == "codex":
        command = runtime_command("codex", prompt, MODEL)
        environment["CODEX_HOME"] = str(state)
        command[-1:-1] = [
            "-c", 'model_provider="continuity_local"',
            "-c", 'model_providers.continuity_local.name="Continuity local Ollama"',
            "-c", f'model_providers.continuity_local.base_url="{relay}"',
            "-c", 'model_providers.continuity_local.wire_api="responses"',
            "-c", "model_providers.continuity_local.requires_openai_auth=false",
            "-c", "model_providers.continuity_local.supports_websockets=false",
            "-c", "model_context_window=16384",
            "-c", 'web_search="disabled"',
        ]
    else:
        command = runtime_command("opencode", prompt, f"continuity-local/{MODEL}")
        command[-1:-1] = ["--title", "Continuity paired evaluation"]
        for name in ("CONFIG", "CACHE", "DATA", "STATE"):
            environment[f"XDG_{name}_HOME"] = str(state / name.lower())
        environment["OPENCODE_CONFIG_CONTENT"] = json.dumps({
            "autoupdate": False,
            "compaction": {"auto": False},
            "provider": {"continuity-local": {
                "npm": "@ai-sdk/openai-compatible", "name": "Local Ollama", "options": {"baseURL": relay},
                "models": {MODEL: {"name": MODEL, "limit": {"context": 16384, "output": 2048}, "tool_call": True}},
            }},
            "permission": {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow",
                           "edit": "allow", "list": "allow", "external_directory": "deny"},
        })
    return command, environment


def grade(case, destination, expected):
    observed, oracle_exit = oracle(case, destination)
    expected_files = sorted([*case["source"], NOTE, REPRO])
    files = staged_files(destination)
    if observed is None:
        differences = None
    else:
        differences = sorted(key for key in expected.keys() | observed.keys() if expected.get(key) != observed.get(key))
    reproduction = repro(destination) if (destination / REPRO).is_file() else {"exit": None}
    native_tests = native(case, destination)
    preserved = {
        NOTE: (destination / NOTE).is_file() and (destination / NOTE).read_text() == case["note"] + "\n",
        REPRO: (destination / REPRO).is_file()
        and (destination / REPRO).read_bytes() == (FIXTURE / (case["id"] + ".py")).read_bytes(),
    }
    return {
        "scope_exact": files == expected_files, "changed_files": files, "artifact_preserved": preserved,
        "repro": reproduction, "native": native_tests, "oracle_exit": oracle_exit,
        "hidden_count": len(expected), "hidden_disagreements": len(differences) if differences is not None else None,
        "hidden_first_disagreements": differences[:8] if differences is not None else [],
        "observed_oracle_sha256": packet_digest(observed) if observed is not None else None,
        "source_sha256": {path: sha((destination / path).read_bytes()) if (destination / path).is_file() else None
                          for path in case["source"]},
        "verified": files == expected_files and all(preserved.values()) and reproduction["exit"] == 0
        and differences == [] and all(test["exit"] == 0 for test in native_tests.values()),
    }


def attempt(case, root, runtime, endpoint, expected, *, reasoning_effort=None, read_limit=None):
    root.mkdir()
    source = download(case, root / "parent", reference=False)
    seed(case, source)
    objective = (
        "/no_think\n" + case["objective"]
        + "\nEdit only " + ", ".join(case["source"]) + ". Read the saved note and reproduction first. "
        "Apply the requested fix in this workspace. Preserve both handoff files exactly. "
        "Do not inspect Git history, contact any external endpoint, or open files outside the checkout."
    )
    db = root / "state.db"
    task = invoke(db, "start", source, "--objective", objective)
    checkpoint = invoke(db, "checkpoint", task["task"], "--include", NOTE, "--include", REPRO,
                        "--note", case["note"], owner=task["token"])
    destination = root / "replacement"
    handoff = invoke(db, "continue", task["task"], "--into", destination, owner=task["token"])
    inspected = invoke(db, "inspect", task["task"])
    assert inspected["clean_match"] and inspected["workspace_digest"] == checkpoint["digest"]
    log = root / "worker.log"
    state = root / "worker-state"
    state.mkdir()
    warm_provider(endpoint)
    with trace_provider(endpoint, reasoning_effort=reasoning_effort, read_limit=read_limit) as (relay, requests):
        command, environment = worker_command(runtime, handoff["prompt"], relay, state)
        outcome = run(command, destination, environment=environment, seconds=TIMEOUT, log=log)
    summary = read_summary(log)
    errors = sum(row.get("http_status", 0) >= 400 for row in requests)
    return {
        "runtime": runtime, "checkpoint_sha256": checkpoint["digest"],
        "prompt_sha256": sha(handoff["prompt"].encode()), "restored_before_launch": inspected["clean_match"],
        "worker": {**outcome, **summary}, "provider_http_errors": errors, "provider_requests": requests,
        "grade": grade(case, destination, expected),
    }


def save(path, report):
    path.write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--endpoint", default="http://127.0.0.1:14687/v1")
    args = parser.parse_args()
    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {"platform": platform.system(), "arch": platform.machine(), "python": platform.python_version(),
                 "codex": execute(["codex", "--version"]).stdout.decode().strip(),
                 "opencode": execute(["opencode", "--version"]).stdout.decode().strip(),
                 "git": git(PROJECT, "--version").decode().strip()},
        "per_worker_timeout_s": TIMEOUT, "model": None, "calibration": [], "attempts": {},
    }
    paths = [Path(__file__), EVALS / "paired_oracle.py", EVALS / "provider_trace.py",
             *sorted(FIXTURE.iterdir())]
    report["source_sha256"] = {str(p.relative_to(PROJECT)): sha(p.read_bytes()) for p in paths}
    with tempfile.TemporaryDirectory(prefix="continuity-paired-") as directory:
        root = Path(directory).resolve()
        frozen = {}
        for case in CASES:
            expected, calibration = calibrate(case, root / case["id"])
            frozen[case["id"]] = expected
            report["calibration"].append(calibration)
        save(args.output, report)
        if args.verify_only:
            return
        report["model"] = local_provider_metadata(args.endpoint)
        for index, case in enumerate(CASES):
            attempts = []
            report["attempts"][case["id"]] = attempts
            order = ("opencode", "codex") if index == 1 else ("codex", "opencode")
            for runtime in order:
                print(f"{case['id']}: running {runtime}", flush=True)
                attempts.append(attempt(case, root / case["id"] / runtime, runtime, args.endpoint, frozen[case["id"]]))
                save(args.output, report)
            assert all(attempts[0][key] == attempts[1][key] for key in ("checkpoint_sha256", "prompt_sha256"))


if __name__ == "__main__":
    main()
