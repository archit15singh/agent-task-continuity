"""Release a previously sent publication after an ownership transfer."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from threading import Event
from time import monotonic, sleep

from continuity.workspace import git
from .publisher import publisher
from .run import PROJECT, execute, invoke, sha


def trial(root, arm):
    fenced = arm != "idempotency_only"
    lagged = arm == "fenced_lagged"
    receiver_first = arm == "receiver_first"
    root.mkdir()
    source = root / "source"
    source.mkdir()
    git(source, "init", "--quiet")
    (source / "candidate.txt").write_text("verified payload\n")
    git(source, "add", "candidate.txt")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "-m", "base")
    ledger = root / "task.db"
    task = invoke(ledger, "start", source, "--objective", "Publish the verified test checkpoint")
    task_id, token = task["task"], task["token"]
    invoke(ledger, "checkpoint", task_id, "--note", "Candidate ready", owner=token)
    evidence = invoke(
        ledger, "verify", task_id, "--command", f"{sys.executable} -c 'print(1)'", owner=token,
    )["evidence"]
    reached, release = Event(), Event()

    def hold():
        if not reached.is_set():
            reached.set()
            release.wait(timeout=15)

    with publisher(drop_first=False, before_apply=hold, generation_fence=fenced) as (service, endpoint):
        service.advance_generation(task_id, task["generation"])
        command = [sys.executable, "-m", "continuity", "--db", str(ledger), "publish", task_id,
                   "--endpoint", endpoint, "--name", "candidate", "--evidence", evidence]
        with subprocess.Popen(command, cwd=PROJECT, env=dict(os.environ, CONTINUITY_OWNER=token),
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL) as active:
            try:
                if not reached.wait(timeout=8):
                    raise RuntimeError("First request did not reach the receiver")
                active.kill()
                active.wait(timeout=3)
                activation_boundary = None
                puts_before_release = 0
                if receiver_first:
                    service.advance_generation(task_id, task["generation"] + 1)
                    (reserved,) = invoke(ledger, "operations", task_id)
                    blocked = invoke(ledger, "reconcile", task_id, reserved["id"], "--retry-absent", owner=token, expected=3)
                    activation_boundary = {
                        "old_owner_local_generation": invoke(ledger, "inspect", task_id)["generation"],
                        "old_owner_result": blocked["status"],
                        "old_owner_http_412": blocked.get("reason") == "Provider returned HTTP 412",
                    }
                    recovery = execute(
                        [sys.executable, "-m", "continuity", "--db", str(ledger), "recover-owner",
                         task_id, "--into", str(root / "resumed")],
                        env=dict(os.environ, CONTINUITY_RECOVERY_KEY=task["recovery_key"]),
                    )
                    recovery.check_returncode()
                    replacement = json.loads(recovery.stdout)
                    puts_before_release = 1
                else:
                    replacement = invoke(ledger, "continue", task_id, "--into", root / "resumed", owner=token)
                    if not lagged:
                        service.advance_generation(task_id, replacement["generation"])
                stale = invoke(ledger, *command[5:], owner=token, expected=2)
            finally:
                if active.poll() is None:
                    active.kill()
                    active.wait(timeout=3)
                release.set()
        deadline = monotonic() + 5
        while monotonic() < deadline:
            with service.lock:
                if service.puts > puts_before_release:
                    break
            sleep(0.01)
        with service.lock:
            if service.puts != puts_before_release + 1:
                raise RuntimeError("Delayed request did not reach the application boundary")
            effects_before = len(service.events)
            rejected_before = service.stale_rejections
        if lagged:
            service.advance_generation(task_id, replacement["generation"])
        (reserved,) = invoke(ledger, "operations", task_id)
        settled = invoke(ledger, "reconcile", task_id, reserved["id"], "--retry-absent",
                         owner=replacement["token"])
        with service.lock:
            return {
                "arm": arm,
                **({"activation_boundary": activation_boundary} if receiver_first else {}),
                "generation_fence": fenced,
                "receiver_advanced_before_release": not lagged,
                "publisher_sigkill": active.returncode == -signal.SIGKILL,
                "generation_before": task["generation"],
                "generation_after": replacement["generation"],
                "stale_local_owner_rejected": "Stale" in stale["error"],
                "local_operation_before_recovery": reserved["status"],
                "receiver_effects_before_recovery": effects_before,
                "receiver_stale_rejections_before_recovery": rejected_before,
                "replacement_confirmed": settled["status"] == "confirmed",
                "receiver_puts": service.puts,
                "receiver_effects_total": len(service.events),
            }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--receiver-first", action="store_true")
    args = cli.parse_args()
    arms = ("receiver_first",) if args.receiver_first else ("idempotency_only", "fenced_current", "fenced_lagged")
    with tempfile.TemporaryDirectory(prefix="continuity-delay-") as directory:
        reports = [
            trial(Path(directory) / f"attempt-{index}", arm)
            for index, arm in enumerate(arms * 3, 1)
        ]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "trials": reports,
    }, indent=2) + "\n")
    for row in reports:
        fenced = row["arm"] in ("fenced_current", "receiver_first")
        assert row["publisher_sigkill"] and row["stale_local_owner_rejected"], row
        assert row["generation_after"] == row["generation_before"] + 1, row
        assert row["receiver_effects_before_recovery"] == (0 if fenced else 1), row
        expected_rejections = 2 if args.receiver_first else int(fenced)
        assert row["receiver_stale_rejections_before_recovery"] == expected_rejections, row
        if args.receiver_first:
            assert row["activation_boundary"] == {
                "old_owner_local_generation": 1, "old_owner_result": "unknown", "old_owner_http_412": True,
            }, row
        assert row["replacement_confirmed"] and row["receiver_effects_total"] == 1, row


if __name__ == "__main__":
    main()
