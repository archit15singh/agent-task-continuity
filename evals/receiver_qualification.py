"""Qualify the signed-in Codex receiver on the three frozen Round 5 artifacts."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile

from continuity.runner import run, runtime_command
from .live import NOTE, REPRO, read_summary
from .paired_continuation import CASES, TIMEOUT, calibrate, grade, save, seed, task_objective
from .run import download, invoke, sha


def attempt(case, root, expected):
    source = download(case, root / "parent", reference=False)
    seed(case, source)
    db = root / "state.db"
    task = invoke(db, "start", source, "--objective", task_objective(case))
    checkpoint = invoke(db, "checkpoint", task["task"], "--include", NOTE, "--include", REPRO,
                        "--note", case["note"], owner=task["token"])
    target = root / "replacement"
    handoff = invoke(db, "continue", task["task"], "--into", target, owner=task["token"])
    assert invoke(db, "inspect", task["task"])["workspace_digest"] == checkpoint["digest"]
    # Reuse the signed-in CLI account, without forwarding API-key overrides or ownership tokens.
    environment = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "TMPDIR") if key in os.environ}
    log = root / "worker.log"
    command = runtime_command("codex", handoff["prompt"], "gpt-6.2-sol")
    command[-1:-1] = ["-c", 'web_search="disabled"']
    outcome = run(command, target, seconds=TIMEOUT, environment=environment, log=log)
    return {"case": case["id"], "checkpoint_sha256": checkpoint["digest"],
            "prompt_sha256": sha(handoff["prompt"].encode()), "worker": {**outcome, **read_summary(log)},
            "grade": grade(case, target, expected)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    report = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seconds_per_worker": TIMEOUT,
              "model_requested": "gpt-6.2-sol", "source_sha256": sha(Path(__file__).read_bytes()), "attempts": []}
    with tempfile.TemporaryDirectory(prefix="continuity-qualification-") as directory:
        root = Path(directory).resolve()
        for case in CASES:
            print(f"Qualifying Codex on {case['id']}", flush=True)
            expected, calibration = calibrate(case, root / case["id"])
            result = attempt(case, root / case["id"], expected)
            report["attempts"].append({"calibration": calibration, **result})
            save(args.output, report)


if __name__ == "__main__":
    main()
