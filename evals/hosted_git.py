"""Exercise ref reconciliation after a publisher dies against the public study remote."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import select
import signal
import subprocess
import sys

from .run import PROJECT, sha


REPOSITORY = "git@github.com:archit15singh/worktree-ledger.git"
INTENDED = "899e0637b4bf68f89c54d119711795ea2f9d676a"
DIFFERENT = "b289080180e4f8b5e9b93d9b6d70b62fb17831d4"


def git_remote(*arguments):
    return subprocess.run(["git", *arguments], cwd=PROJECT, check=False, capture_output=True,
                          text=True, timeout=35)


def query(ref):
    result = git_remote("ls-remote", "--refs", REPOSITORY, ref)
    result.check_returncode()
    rows = result.stdout.splitlines()
    if not rows:
        return None
    assert len(rows) == 1 and rows[0].endswith("\t" + ref)
    return rows[0].split()[0]


def push(ref, source, *, expected=""):
    return git_remote("push", "--porcelain", f"--force-with-lease={ref}:{expected}",
                      REPOSITORY, f"{source}:{ref}")


def publish_and_pause(ref):
    result = push(ref, INTENDED)
    print(json.dumps({"exit": result.returncode}), flush=True)
    signal.pause()


def trial():
    ref = "refs/heads/continuity-eval/" + secrets.token_hex(8)
    if query(ref) is not None:
        raise RuntimeError("Generated ref already exists")
    with subprocess.Popen([sys.executable, "-m", "evals.hosted_git", "--worker", ref],
                          cwd=PROJECT, text=True, stdout=subprocess.PIPE) as worker:
        try:
            if not select.select([worker.stdout], [], [], 40)[0]:
                raise TimeoutError("Publisher did not reach the acknowledgment barrier")
            volatile_ack = json.loads(worker.stdout.readline())
            assert volatile_ack["exit"] == 0
            accepted = query(ref)
            assert accepted == INTENDED and worker.poll() is None
            worker.kill()
            worker_exit = worker.wait(timeout=5)
            assert worker_exit == -signal.SIGKILL
            replay = push(ref, INTENDED)
            replay_sha = query(ref)
            conflict = push(ref, DIFFERENT)
            final = query(ref)
            observations = {
                "namespace": ref, "observed_before_worker_death": accepted,
                "worker_exit": worker_exit, "same_target_retry_exit": replay.returncode,
                "same_target_up_to_date": "[up to date]" in replay.stdout,
                "same_target_readback": replay_sha,
                "different_target_retry_exit": conflict.returncode,
                "different_target_rejected_as_stale": "stale info" in conflict.stdout + conflict.stderr,
                "final_independent_readback": final,
            }
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=5)
            observed = query(ref)
            if observed == INTENDED:
                push(ref, "", expected=INTENDED).check_returncode()
            final_cleanup = query(ref)
            if final_cleanup is not None:
                raise RuntimeError(f"Fixture ref retained because its value changed: {ref}")
    assert replay.returncode == 0 and observations["same_target_up_to_date"] and replay_sha == INTENDED
    assert conflict.returncode != 0 and observations["different_target_rejected_as_stale"] and final == INTENDED
    return {**observations, "removed_with_matching_lease": final_cleanup is None}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--worker")
    args = cli.parse_args()
    if args.worker:
        assert args.worker.startswith("refs/heads/continuity-eval/")
        publish_and_pause(args.worker)
        return
    if not args.output:
        cli.error("--output is required")
    report = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "receiver": "GitHub Git receive-pack over SSH", "base_revision": INTENDED,
              "conflicting_revision": DIFFERENT, "source_sha256": sha(Path(__file__).read_bytes()), "trials": []}
    for number in range(3):
        report["trials"].append(trial())
        print(f"Hosted trial {number + 1}/3 passed", flush=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
