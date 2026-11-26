"""Run the frozen Packaging handoff with a paired compaction setting."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

from continuity.runner import run, runtime_command
from continuity.workspace import git
from .live import NOTE, REPRO, read_summary, replacement_objective, staged_files, worker_environment
from .provider_trace import trace_provider
from .run import CASES, EVALS, PROJECT, check_argv, download, execute, invoke, sha

CASE = next(case for case in CASES if case["id"] == "packaging")
FIXTURE = EVALS / "fixtures" / "packaging"


def grade(workspace):
    pred = execute(check_argv(CASE), cwd=workspace)
    repro = execute([sys.executable, REPRO], cwd=workspace)
    native = execute(
        [sys.executable, str(EVALS / "native_tests.py"), CASE["native_test"]], cwd=workspace,
    )
    return {
        "files_restored": all(
            (workspace / name).is_file() and (workspace / name).read_bytes() == (FIXTURE / name).read_bytes()
            for name in (NOTE, REPRO)
        ),
        "changed_files": staged_files(workspace),
        "predicate_exit": pred.returncode,
        "repro_exit": repro.returncode,
        "native_exit": native.returncode,
        "native_summary": (native.stdout + native.stderr).decode(errors="replace").splitlines()[-1:],
        "source_sha256": sha((workspace / CASE["source"]).read_bytes()),
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--model")
    cli.add_argument("--endpoint")
    cli.add_argument("--dry-run", action="store_true")
    cli.add_argument("--trace-single-auto", action="store_true",
                     help="Run one additional auto-compaction arm through a metadata-only provider trace")
    cli.add_argument("--fixed-title", action="store_true",
                     help="Provide a fixed OpenCode title on the single traced attempt")
    cli.add_argument("--reasoning-matrix", action="store_true",
                     help="Trace four fixed-title attempts in default, none, none, default order")
    cli.add_argument("--timeout", type=int, default=180)
    args = cli.parse_args()
    if not args.dry_run and (not args.endpoint or not args.model):
        cli.error("live runs need --endpoint and --model")
    if args.reasoning_matrix and (args.trace_single_auto or args.fixed_title):
        cli.error("--reasoning-matrix already traces and applies a fixed title")
    if args.fixed_title and not args.trace_single_auto:
        cli.error("--fixed-title requires --trace-single-auto")
    if args.endpoint and not args.endpoint.startswith("http://127.0.0.1:"):
        cli.error("use a loopback provider")
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "continuity_head": git(PROJECT, "rev-parse", "HEAD").decode().strip(),
        "case": CASE["id"],
        "base": CASE["base"],
        "reference": CASE["reference"],
        "opencode": execute(["opencode", "--version"]).stdout.decode().strip(),
        "model": args.model,
        "timeout": args.timeout,
        **({"fixed_title": True} if args.fixed_title or args.reasoning_matrix else {}),
        "fixture_hashes": {name: sha((FIXTURE / name).read_bytes()) for name in (NOTE, REPRO)},
        "arms": [],
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    with tempfile.TemporaryDirectory(prefix="continuity-frozen-") as directory:
        temp = Path(directory)
        source = download(CASE, temp / "source", reference=False)
        oracle = download(CASE, temp / "oracle", reference=True)
        git(oracle, "checkout", "--quiet", "--detach", CASE["reference"])
        for workspace in (source, oracle):
            for name in (NOTE, REPRO):
                (workspace / name).write_bytes((FIXTURE / name).read_bytes())
        report["negative_control"] = grade(source)
        report["positive_control"] = grade(oracle)
        save()
        gates = ("predicate_exit", "repro_exit", "native_exit")
        if (
            tuple(report["negative_control"][key] for key in gates) != (1, 1, 0)
            or tuple(report["positive_control"][key] for key in gates) != (0, 0, 0)
        ):
            raise RuntimeError("Frozen grading controls did not produce the expected results")
        if args.dry_run:
            return

        if args.reasoning_matrix:
            arms = [(True, effort) for effort in (None, "none", "none", None)]
        else:
            arms = [(auto, None) for auto in ((True,) if args.trace_single_auto else (True, False, False, True))]
        traced = args.trace_single_auto or args.reasoning_matrix
        for index, (auto, effort) in enumerate(arms, 1):
            db = temp / f"ledger-{index}.db"
            task = invoke(db, "start", source, "--objective", replacement_objective(CASE, True))
            checkpoint = invoke(
                db, "checkpoint", task["task"], "--include", NOTE, "--include", REPRO, "--note",
                (FIXTURE / NOTE).read_text().strip(), owner=task["token"],
            )
            destination = temp / f"attempt-{index}"
            handoff = invoke(db, "continue", task["task"], "--into", destination, owner=task["token"])
            tracer = trace_provider(args.endpoint, reasoning_effort=effort) if traced else nullcontext((args.endpoint, []))
            with tracer as (endpoint, provider_requests):
                env = worker_environment(endpoint, args.model, None)
                env.pop("CONTINUITY_OWNER", None)
                env.pop("CONTINUITY_RECOVERY_KEY", None)
                config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
                config["compaction"] = {"auto": auto}
                env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
                log = temp / f"attempt-{index}.log"
                command = runtime_command("opencode", handoff["prompt"], args.model)
                if args.fixed_title or args.reasoning_matrix:
                    command[-1:-1] = ["--title", "Frozen Packaging handoff"]
                worker = run(
                    command,
                    destination, seconds=args.timeout, environment=env, log=log,
                )
            worker.update(read_summary(log))
            result = grade(destination)
            result["complete"] = (
                result["files_restored"] and result["changed_files"] == sorted([NOTE, REPRO, CASE["source"]])
                and all(result[key] == 0 for key in gates) and worker["exit_code"] == 0
            )
            report["arms"].append({
                "attempt": index, "auto_compaction": auto, "checkpoint_sha256": checkpoint["digest"],
                "worker": worker, "grade": result,
                **({"provider_requests": provider_requests} if traced else {}),
                **({"reasoning_effort": effort} if args.reasoning_matrix else {}),
            })
            save()
            print(f"{index} auto={auto}: {worker['exit_code']} / complete={result['complete']}", flush=True)
            git(source, "worktree", "remove", "--force", str(destination))


if __name__ == "__main__":
    main()
