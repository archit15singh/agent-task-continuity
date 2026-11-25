"""Measure handoff and recovery on pinned public upstream worktrees."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time

from continuity.workspace import fingerprint, git
from .publisher import publisher

EVALS = Path(__file__).resolve().parent
PROJECT = EVALS.parent
NOTE = "continuity-eval-note.txt"
CASES = json.loads((EVALS / "cases.json").read_text())


def execute(command, *, cwd=PROJECT, env=None, timeout=180):
    return subprocess.run(
        command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
    )


def invoke(db, *arguments, owner=None, expected=0):
    env = dict(os.environ)
    env.pop("CONTINUITY_OWNER", None)
    if owner:
        env["CONTINUITY_OWNER"] = owner
    result = execute([sys.executable, "-m", "continuity", "--db", str(db), *map(str, arguments)],
                     env=env, timeout=420)
    if result.returncode != expected:
        raise RuntimeError(f"{arguments[0]} returned {result.returncode}, expected {expected}: "
                           f"{result.stderr.decode(errors='replace')}")
    return json.loads(result.stdout if result.stdout else result.stderr)


def download(case, path, *, reference):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "fetch", "--quiet", "--depth=2" if reference else "--depth=1",
        f"https://github.com/{case['repository']}.git",
        case["reference"] if reference else case["base"])
    if reference and git(path, "rev-parse", "FETCH_HEAD^").decode().strip() != case["base"]:
        raise RuntimeError("Pinned parent does not match reference")
    git(path, "checkout", "--quiet", "--detach", case["base"])
    return path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_argv(case):
    return [sys.executable, str(EVALS / "check_case.py"), case["id"]]


def grade(case, workspace, expected_source, expected_note):
    source = (workspace / case["source"]).read_bytes()
    note = workspace / NOTE
    checked = execute(check_argv(case), cwd=workspace)
    return {
        "tracked_matches": source == expected_source,
        "selected_untracked_matches": note.is_file() and note.read_bytes() == expected_note,
        "source_predicate_passes": checked.returncode == 0,
        "tracked_sha256": sha(source),
        "selected_untracked_sha256": sha(note.read_bytes()) if note.is_file() else None,
        "grader_exit": checked.returncode,
    }


def crash_after_publish(db, task, owner, evidence, destination):
    started = threading.Event()
    client = None

    def kill_client():
        if not started.wait(timeout=5):
            raise RuntimeError("Publishing client never started")
        client.kill()

    with publisher(after_accept=kill_client) as (service, endpoint):
        env = dict(os.environ, CONTINUITY_OWNER=owner)
        command = [sys.executable, "-m", "continuity", "--db", str(db), "publish", task,
                   "--endpoint", endpoint, "--name", "kill-after-accept", "--evidence", evidence]
        with subprocess.Popen(command, cwd=PROJECT, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as client:
            started.set()
            try:
                client.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                client.kill()
                client.communicate()
                raise
        operations = invoke(db, "operations", task)
        reserved = [item["id"] for item in operations if item["status"] == "reserved"]
        if len(reserved) != 1:
            raise RuntimeError("The killed client did not leave one durable reservation")
        recovered = invoke(db, "continue", task, "--into", destination, owner=owner)
        settled = invoke(db, "reconcile", task, reserved[0], owner=recovered["token"])
        return {
            "client_sigkill": client.returncode == -signal.SIGKILL,
            "intent_reserved": len(reserved) == 1,
            "replacement_confirmed": settled["status"] == "confirmed",
            "puts": service.puts, "gets": service.gets, "effects": len(service.events),
        }


def transport_case(case, temp):
    db = temp / "ledger.db"
    initial = download(case, temp / "initial", reference=True)
    source_patch = git(initial, "diff", "--binary", "--full-index", case["base"],
                       case["reference"], "--", case["source"])
    git(initial, "apply", "--binary", "-", data=source_patch)
    source = (initial / case["source"]).read_bytes()
    note = f"Task {case['id']}: review the saved changes and run the case predicate.\n".encode()
    (initial / NOTE).write_bytes(note)
    objective = f"Continue the scoped {case['id']} implementation and verify the restored workspace."
    arms = {}
    for arm in ("brief-only", "manual-git"):
        started = time.monotonic()
        destination = temp / arm
        git(initial, "worktree", "add", "--quiet", "--detach", str(destination), case["base"])
        if arm == "manual-git":
            exported = git(initial, "diff", "--binary", "--full-index", "HEAD", "--", case["source"])
            git(destination, "apply", "--binary", "-", data=exported)
            (destination / NOTE).write_bytes((initial / NOTE).read_bytes())
        arms[arm] = grade(case, destination, source, note)
        arms[arm]["seconds_including_grade"] = round(time.monotonic() - started, 4)

    started = time.monotonic()
    task = invoke(db, "start", initial, "--objective", objective)
    task_id, old = task["task"], task["token"]
    seed = invoke(db, "checkpoint", task_id, "--include", NOTE, "--note", note.decode(),
                  "--next", "Run the case predicate", owner=old)
    manifest = invoke(db, "manifest", task_id, "--with-patch")
    exported = manifest["artifact"]
    manifest_roundtrip = (
        manifest["version"] == 1 and manifest["context"]["next_actions"] == ["Run the case predicate"]
        and fingerprint(exported["base"], base64.b64decode(exported["git_binary_patch_base64"]))
        == seed["digest"] == exported["sha256"]
    )
    before = invoke(db, "inspect", task_id)
    worker = [sys.executable, str(EVALS / "worker.py")]
    worktree = temp / "replacement"
    supervised = invoke(
        db, "supervise", task_id, "--first", shlex.join([*worker, "crash"]),
        "--replacement", shlex.join([*worker, "recover", str(EVALS / "check_case.py"), case["id"]]),
        "--into", worktree, "--timeout", "30", "--recovery-timeout", "30", owner=old,
    )
    new = supervised["takeover"]["token"]
    managed = grade(case, worktree, source, note)
    managed["seconds_including_grade"] = round(time.monotonic() - started, 4)
    arms["managed"] = managed

    stale_checkpoint = invoke(db, "checkpoint", task_id, "--note", "stale attempt",
                              owner=old, expected=2)
    (initial / NOTE).write_text("retired owner edited its own worktree\n")
    isolated = invoke(db, "inspect", task_id)
    receipt = invoke(db, "verify", task_id, "--command", shlex.join(check_argv(case)), owner=new)
    verified = invoke(db, "inspect", task_id)
    with publisher() as (service, url):
        arguments = ["publish", task_id, "--endpoint", url, "--name", "candidate",
                     "--evidence", receipt["evidence"]]
        uncertain = invoke(db, *arguments, owner=new, expected=3)
        published_snapshot = worktree
        worktree = temp / "reconciler"
        takeover = invoke(db, "continue", task_id, "--into", worktree, owner=new)
        stale_publish = invoke(db, *arguments, owner=new, expected=2)
        final_owner = takeover["token"]
        disposition = invoke(db, "reconcile", task_id, uncertain["operation"], owner=final_owner)
        repeated = invoke(db, *arguments, owner=final_owner)
        puts, gets, events = service.puts, service.gets, len(service.events)
        with (worktree / case["source"]).open("ab") as current:
            current.write(b"\n# changed after verification\n")
        changed = invoke(db, "inspect", task_id)
        # The baseline publication names an immutable snapshot. Scratch edits stay local.
        invoke(db, "checkpoint", task_id, "--include", NOTE, "--note", "new revision",
               owner=final_owner)
        mismatch = invoke(db, "publish", task_id, "--endpoint", url, "--name", "changed",
                          "--evidence", receipt["evidence"], owner=final_owner, expected=2)
        assert published_snapshot.is_dir()
    # Restore the previously verified bytes as the input to the additional fault probe.
    git(worktree, "apply", "-R", "--binary", "-", data=git(worktree, "diff", "--binary",
                                                        "--", case["source"]))
    git(worktree, "apply", "--binary", "-", data=source_patch)
    invoke(db, "checkpoint", task_id, "--include", NOTE, "--note", "restore verified content",
           owner=final_owner)
    killed_client = crash_after_publish(db, task_id, final_owner, receipt["evidence"],
                                       temp / "publish-recovery")
    native = execute([sys.executable, str(EVALS / "native_tests.py"), case["native_test"]],
                     cwd=published_snapshot)
    return {
        "id": case["id"], "split": case["split"], "base": case["base"], "reference": case["reference"],
        "arms": arms,
        "faults": {
            "sigkill": supervised["initial"]["exit_code"] == -9,
            "late_change_lost_at_documented_boundary": (
                (initial / "continuity-late-edit.txt").exists()
                and not (worktree / "continuity-late-edit.txt").exists()
            ),
            "replacement_passed": supervised["replacement"]["exit_code"] == 0,
            "snapshot_matches": before["clean_match"] and isolated["clean_match"],
            "stale_checkpoint_rejected": "Stale" in stale_checkpoint["error"],
            "stale_publish_rejected": "Stale" in stale_publish["error"],
            "lost_ack_recorded_unknown": uncertain["status"] == "unknown",
            "lookup_reconciled": disposition["status"] == "confirmed",
            "receipt_reused": disposition["receipt"] == repeated["receipt"],
            "single_put_single_effect": puts == events == 1,
            "verification_bound": verified["verification"][0]["passed"] and
                                  verified["verification"][0]["matches"] and
                                  receipt["digest"] == seed["digest"],
            "drift_invalidates_verification": not changed["verification"][0]["matches"],
            "wrong_revision_publish_rejected": "passing evidence" in mismatch["error"],
        },
        "provider": {"puts": puts, "gets": gets, "effects": events},
        "publication_client_killed": killed_client,
        "manifest_roundtrip": manifest_roundtrip,
        "verification": {"exit": receipt["exit_code"], "snapshot_sha256": seed["digest"],
                         "log_sha256": receipt["output_sha256"]},
        "native": {"exit": native.returncode, "log_sha256": sha(native.stdout + native.stderr),
                   "summary": (native.stdout + native.stderr).decode(errors="replace").splitlines()[-1:]},
    }


def gate(row):
    graded = ("tracked_matches", "selected_untracked_matches", "source_predicate_passes")
    return (not any(row["arms"]["brief-only"][key] for key in graded)
            and all(row["arms"][arm][key] for arm in ("manual-git", "managed") for key in graded)
            and all(row["faults"].values()) and row["native"]["exit"] == 0
            and row["manifest_roundtrip"]
            and row["publication_client_killed"]["client_sigkill"]
            and row["publication_client_killed"]["intent_reserved"]
            and row["publication_client_killed"]["replacement_confirmed"]
            and row["publication_client_killed"]["puts"] == row["publication_client_killed"]["effects"] == 1)


def git_version():
    return execute(["git", "--version"]).stdout.decode().strip()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--set", choices=("development", "held-out", "all"), default="all")
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    selected = [case for case in CASES if args.set in ("all", case["split"])]
    revision = git(PROJECT, "rev-parse", "HEAD").decode().strip()
    rows = []
    with tempfile.TemporaryDirectory(prefix="continuity-study-") as directory:
        for case in selected:
            temp = Path(directory) / case["id"]
            temp.mkdir()
            rows.append(transport_case(case, temp))
            print(f"{case['id']}: {'pass' if gate(rows[-1]) else 'fail'}", flush=True)
    document = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_commit": revision,
        "set": args.set, "python": platform.python_version(), "os": platform.system(),
        "architecture": platform.machine(), "git": git_version(), "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n")
    sys.exit(0 if all(gate(row) for row in rows) else 1)


if __name__ == "__main__":
    main()
