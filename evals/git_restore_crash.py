"""Kill one native Git apply halfway through a multi-path restoration."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time

TEXT = "a-text.txt"
BINARY = "b-bytes.bin"
DELETION = "c-delete.txt"
NOTE = "d-note.txt"


def pause_filter():
    data = sys.stdin.buffer.read()
    if ready := os.environ.get("CONTINUITY_FIXTURE_GIT_READY"):
        Path(ready).write_text(hashlib.sha256(data).hexdigest())
        # The orchestrator normally kills the entire Git group at this barrier.
        time.sleep(30)
    sys.stdout.buffer.write(data)


def observe(workspace):
    names = (TEXT, BINARY, DELETION, NOTE)
    return {name: hashlib.sha256((workspace / name).read_bytes()).hexdigest()
            if (workspace / name).is_file() else None for name in names}


def trial(root):
    from continuity.store import PreparedSnapshotMismatch, Store
    from continuity.workspace import capture, fingerprint, git

    source, interrupted, fresh = root / "source", root / "interrupted", root / "fresh"
    source.mkdir(parents=True)
    git(source, "init", "--quiet")
    (source / ".gitattributes").write_text(BINARY + " -diff filter=continuity-crash\n")
    git(source, "config", "filter.continuity-crash.smudge",
        shlex.join([sys.executable, str(Path(__file__).resolve()), "--filter"]))
    (source / TEXT).write_bytes(b"old text\n")
    (source / BINARY).write_bytes(bytes(range(256)))
    (source / DELETION).write_bytes(b"tracked file to delete\n")
    git(source, "add", "--", ".")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "-m", "Base")
    base_contents = observe(source)
    (source / TEXT).write_bytes(b"new text\n")
    (source / BINARY).write_bytes(bytes(range(255, -1, -1)))
    (source / DELETION).unlink()
    (source / NOTE).write_bytes(b"carry this note\n")
    expected = observe(source)

    store = Store(root / "tasks.db")
    created = store.create(source, "Restore all four file dispositions")
    task, owner = created["task"], created["token"]
    saved = store.checkpoint(task, owner, [NOTE], "Verify all paths")
    base, patch = capture(source, [NOTE])
    assert b"GIT binary patch" in patch
    git(source, "worktree", "add", "--quiet", "--detach", str(interrupted), base)
    ready = root / "barrier"
    with tempfile.TemporaryFile() as output:
        env = dict(os.environ, CONTINUITY_FIXTURE_GIT_READY=str(ready))
        command = ["git", "--literal-pathspecs", "-c", "core.hooksPath=/dev/null",
                   "apply", "--binary", "--whitespace=nowarn", "-"]
        with subprocess.Popen(command, cwd=interrupted, env=env, stdin=subprocess.PIPE,
                              stdout=output, stderr=output, start_new_session=True) as child:
            child.stdin.write(patch)
            child.stdin.close()
            deadline = time.monotonic() + 8
            try:
                while not (ready.exists() and ready.stat().st_size == 64):
                    if child.poll() is not None or time.monotonic() >= deadline:
                        output.seek(0)
                        raise AssertionError(f"Git never reached filter barrier: {output.read()!r}")
                    time.sleep(0.01)
                during = observe(interrupted)
                assert ready.read_text() == expected[BINARY]
                assert during[TEXT] == expected[TEXT]
                assert during[BINARY] != expected[BINARY]
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
    assert child.returncode == -signal.SIGKILL and observe(interrupted) == during
    try:
        store.takeover(task, owner, interrupted, prepared=True)
    except PreparedSnapshotMismatch:
        declined = True
    else:
        raise AssertionError("Partial Git output became authoritative")
    with store.connection() as connection:
        generation_after_rejection = store.task(connection, task, owner)["generation"]
    resumed = store.takeover(task, owner, fresh)
    assert generation_after_rejection == 1 and resumed["generation"] == 2
    assert observe(fresh) == expected
    assert fingerprint(*capture(fresh, [NOTE])) == saved["digest"]
    assert observe(interrupted) == during
    return {"git_exit": child.returncode, "partial_rejected": declined,
            "generation_after_partial_rejection": generation_after_rejection,
            "recovered_generation": resumed["generation"], "checkpoint_sha256": saved["digest"],
            "base": base_contents, "during_and_after_kill": during, "expected_and_recovered": expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filter", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.filter:
        pause_filter()
        return
    if args.output is None:
        parser.error("--output is required")
    from continuity.workspace import git

    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="continuity-native-git-crash-") as directory:
        root = Path(directory)
        trials = [trial(root / f"trial-{count}") for count in range(3)]
        version = git(root, "--version").decode().strip()
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": version,
        "source_sha256": source_sha, "trials": trials,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
