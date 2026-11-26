"""Observe a Git ref after a publisher dies before the push command returns."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from continuity.runner import stop
from continuity.workspace import git
from .run import execute, sha


REF = "refs/heads/continuity-operation"
HOOK = """#!/bin/sh
while IFS= read -r update; do
    printf '%s\n' "$update" >> hooks/continuity-updates
done
while test ! -e hooks/continuity-release; do sleep 0.1; done
"""


def trial(temp):
    temp.mkdir()
    receiver, sender = temp / "receiver.git", temp / "sender"
    receiver.mkdir()
    sender.mkdir()
    git(receiver, "init", "--quiet", "--bare")
    git(sender, "init", "--quiet")
    git(sender, "config", "user.name", "Continuity Fixture")
    git(sender, "config", "user.email", "fixture@example.invalid")
    git(sender, "commit", "--quiet", "--allow-empty", "-m", "candidate")
    candidate = git(sender, "rev-parse", "HEAD").decode().strip()
    git(sender, "commit", "--quiet", "--allow-empty", "-m", "alternative")
    alternative = git(sender, "rev-parse", "HEAD").decode().strip()
    hooks = receiver / "hooks"
    script = hooks / "post-receive"
    script.write_text(HOOK)
    script.chmod(0o755)
    changes = hooks / "continuity-updates"
    release = hooks / "continuity-release"

    def push(commit):
        return ["git", "push", "--porcelain", f"--force-with-lease={REF}:", str(receiver), f"{commit}:{REF}"]

    def readback():
        result = git(sender, "ls-remote", "--refs", str(receiver), REF).decode().strip()
        return result == f"{candidate}\t{REF}"

    with tempfile.TemporaryFile() as output:
        with subprocess.Popen(
            push(candidate), cwd=sender, stdin=subprocess.DEVNULL, stdout=output,
            stderr=subprocess.STDOUT, start_new_session=True,
        ) as active:
            try:
                deadline = time.monotonic() + 12
                while not changes.exists() and active.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                visible = changes.is_file() and readback()
                pending = active.poll() is None
                if not visible or not pending:
                    raise RuntimeError("Receiver did not expose the ref while the publishing command remained pending")
            finally:
                stop(active)
    release.touch()
    duplicate = execute(push(candidate), cwd=sender, timeout=12)
    conflict = execute(push(alternative), cwd=sender, timeout=12)
    updates = changes.read_text().splitlines()
    return {
        "ref_visible_before_kill": visible,
        "command_pending_at_kill": pending,
        "publisher_signal": -active.returncode,
        "same_target_retry_exit": duplicate.returncode,
        "same_target_already_up_to_date": b"[up to date]" in duplicate.stdout,
        "different_target_retry_exit": conflict.returncode,
        "different_target_rejected_as_stale": b"stale info" in conflict.stdout + conflict.stderr,
        "ref_still_matches_candidate": readback(),
        "receiver_updates": len(updates),
        "only_update_was_expected_creation": updates == [f"{'0' * len(candidate)} {candidate} {REF}"],
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-git-publish-") as directory:
        temp = Path(directory).resolve()
        report = {
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
            "git": git(temp, "--version").decode().strip(),
            "trials": [trial(temp / f"trial-{index}") for index in range(1, 4)],
        }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if not all(
        item["publisher_signal"] == signal.SIGKILL and item["same_target_retry_exit"] == 0
        and item["same_target_already_up_to_date"] and item["different_target_retry_exit"] != 0
        and item["different_target_rejected_as_stale"] and item["ref_still_matches_candidate"]
        and item["only_update_was_expected_creation"] for item in report["trials"]
    ):
        raise RuntimeError("Git ref readback or conditional retry differed from expectations")


if __name__ == "__main__":
    main()
