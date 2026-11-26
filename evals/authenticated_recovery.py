"""Compare worker-authenticated publication and interrupted checkout recovery."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import secrets
import sqlite3
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from continuity.publish import json_text, operation_id, publication_bearer, request
from continuity.workspace import git
from .durable_activation import (
    ACTIVATION_ENV, AUTH_ENV, INTENT, MODULE, advance, trial,
)
from .receiver_restart import counts, receiver
from .run import CASES, NOTE, PROJECT, download, execute, grade, invoke, sha


def fixture_env(key, authenticated):
    return dict(os.environ, **{ACTIVATION_ENV: key, AUTH_ENV: str(int(authenticated))})


def http_status(action):
    try:
        action()
    except HTTPError as error:
        return error.code
    return 200  # Successful activation endpoint replies are HTTP 200.


def credential_trial(db, authenticated):
    key = secrets.token_urlsafe(32)
    env = fixture_env(key, authenticated)
    task, other_task = secrets.token_hex(16), secrets.token_hex(16)
    old, successor = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    retired = publication_bearer(old, task, 1)
    active = publication_bearer(successor, task, 2)
    other = publication_bearer(successor, other_task, 2)
    with receiver(db, 0, "none", module=MODULE, env=env) as (_, port):
        endpoint = f"http://127.0.0.1:{port}"
        assert advance(endpoint, key, task, 0, bearer=retired) == 1
        assert advance(endpoint, key, task, 1, bearer=active) == 2
    with receiver(db, port, "none", module=MODULE, env=env):
        repeated = http_status(lambda: advance(endpoint, key, task, 1, bearer=active))
        conflicting = http_status(lambda: advance(endpoint, key, task, 1, bearer=retired))
        assert advance(endpoint, key, other_task, 0, bearer=publication_bearer(old, other_task, 1)) == 1
        assert advance(endpoint, key, other_task, 1, bearer=other) == 2

        def send(name, generation, bearer, *, operation=None, for_task=task):
            operation = operation or operation_id(for_task, name)
            payload = {"task": for_task, "name": name}
            headers = {"Content-Type": "application/json", "Idempotency-Key": operation,
                       "X-Continuity-Generation": str(generation)}
            if bearer is not None:
                headers["Authorization"] = "Bearer " + bearer
            put = Request(f"{endpoint}/events/{operation}", method="PUT",
                          data=json_text(payload).encode(), headers=headers)
            try:
                with urlopen(put, timeout=5) as response:
                    assert json.load(response) == {"id": operation, "payload": payload}
                    return response.status
            except HTTPError as error:
                return error.code

        observed = {
            "retired_generation": send("delayed", 1, retired),
            "retired_bearer_current_generation": send("retired-current", 2, retired),
            "no_bearer_current_generation": send("absent-current", 2, None),
            "other_task_bearer_current_generation": send("other-current", 2, other),
            "other_task_operation_with_valid_bearer": send(
                "wrong-key", 2, other, for_task=other_task, operation=operation_id(task, "wrong-key"),
            ),
            "active_bearer": send("active", 2, active),
            "active_retry": send("active", 2, active),
        }
        assert request(endpoint, operation_id(task, "active"))["payload"] == {"task": task, "name": "active"}
    effects = counts(db)
    assert repeated == 200 and conflicting == (409 if authenticated else 200)
    assert observed == {
        "retired_generation": 412,
        "retired_bearer_current_generation": 403 if authenticated else 201,
        "no_bearer_current_generation": 403 if authenticated else 201,
        "other_task_bearer_current_generation": 403 if authenticated else 201,
        "other_task_operation_with_valid_bearer": 400 if authenticated else 201,
        "active_bearer": 201,
        "active_retry": 200,
    }, observed
    assert effects == ([1, 1] if authenticated else [5, 5]), effects
    return {
        "authenticated": authenticated, "activation_replay": repeated, "activation_conflict": conflicting,
        "request_dispositions": observed, "effects_and_receipts": effects,
    }


def partial_trial(directory, case):
    directory.mkdir()
    source = download(case, directory / "source", reference=True)
    git(source, "apply", "--binary", "-", data=git(
        source, "diff", "--binary", "--full-index", case["base"], case["reference"], "--", case["source"],
    ))
    expected_source = git(source, "show", f"{case['reference']}:{case['source']}")
    note = f"Continuity checkpoint for {case['id']}.\n".encode()
    (source / NOTE).write_bytes(note)
    local, database = directory / "local.db", directory / "receiver.db"
    started = invoke(local, "start", source, "--objective", "Recover the implementation and selected note")
    task, old = started["task"], started["token"]
    saved = invoke(local, "checkpoint", task, "--note", "Preserve both files", "--include", NOTE, owner=old)
    successor, key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    original = directory / "replacement"
    intent = directory / "intent.db"
    with closing(sqlite3.connect(intent)) as db:
        db.executescript(INTENT)
        db.execute("INSERT INTO intent VALUES (?, ?, ?, ?, ?, ?, 0)",
                   (task, old, successor, str(original), 1, saved["checkpoint"]))
        db.commit()

    def run(endpoint, *flags):
        return execute([sys.executable, "-m", MODULE, "--coordinate", str(directory),
                        "--endpoint", endpoint, *flags], env=env, timeout=45)

    env = fixture_env(key, True)
    with receiver(database, 0, "none", module=MODULE, env=env) as (_, port):
        endpoint = f"http://127.0.0.1:{port}"
        assert advance(endpoint, key, task, 0, bearer=publication_bearer(old, task, 1)) == 1
        interrupted = run(endpoint, "--partial-path", case["source"])
        assert interrupted.returncode == 35, interrupted.stderr.decode(errors="replace")
        before = grade(case, original, expected_source, note)
        assert before["tracked_matches"] and not before["selected_untracked_matches"]
    with receiver(database, port, "none", module=MODULE, env=env):
        control = run(endpoint)
        assert control.returncode == 1 and b"PreparedSnapshotMismatch" in control.stderr
        generation_after_control = invoke(local, "inspect", task)["generation"]
        assert generation_after_control == 1
        retry_exit = run(endpoint, "--recover-partial", "--fault", "retry-path")
        assert retry_exit.returncode == 36, retry_exit.stderr.decode(errors="replace")
    with closing(sqlite3.connect(intent)) as db:
        retry, complete = db.execute("SELECT destination, complete FROM intent").fetchone()
    retry = Path(retry)
    assert retry != original and not retry.exists() and complete == 0
    with receiver(database, port, "none", module=MODULE, env=env):
        recovered = run(endpoint, "--recover-partial")
        assert recovered.returncode == 0, recovered.stderr.decode(errors="replace")
        assert run(endpoint, "--recover-partial").returncode == 0
    with closing(sqlite3.connect(intent)) as db:
        assert db.execute("SELECT destination, complete FROM intent").fetchone() == (str(retry), 1)
    current = invoke(local, "inspect", task)
    after = grade(case, retry, expected_source, note)
    assert current["generation"] == 2 and current["checkpoint"] == saved["checkpoint"] and current["clean_match"]
    assert current["workspace_digest"] == saved["digest"]
    assert after["tracked_matches"] and after["selected_untracked_matches"] and after["source_predicate_passes"]
    assert grade(case, original, expected_source, note) == before
    return {
        "repository": case["repository"], "base": case["base"], "reference": case["reference"],
        "partial_exit": interrupted.returncode, "partial_grade": before, "control_exit": control.returncode,
        "control_generation": generation_after_control, "retry_path_exit": retry_exit.returncode,
        "prior_checkout_preserved": True, "new_destination": True, "recovery_generation": current["generation"],
        "saved_and_restored_digests_match": current["workspace_digest"] == saved["digest"],
        "recovery_grade": after,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    stages = ("intent", "receiver", "workspace", "local", "before", "after")
    with tempfile.TemporaryDirectory(prefix="continuity-authenticated-recovery-") as temp:
        root = Path(temp)
        credential_controls = [credential_trial(root / f"control-{i}.db", bool(i % 2)) for i in range(6)]
        with ThreadPoolExecutor(max_workers=3) as pool:
            restore_trials = pool.map(lambda case: partial_trial(root / case["id"], case), CASES)
            fault_trials = pool.map(
                lambda item: trial(root / f"fault-{item[0]}", item[1], authenticated=True),
                enumerate(stages * 3),
            )
            restored, faults = list(restore_trials), list(fault_trials)
    for row in faults:
        stage = row["fault"]
        assert row["coordinator_exit"] == {"intent": 31, "receiver": 32, "workspace": 34, "local": 33}.get(stage, 0)
        assert row["epochs_at_interruption"] == {
            "intent": [1, 1], "receiver": [1, 2], "workspace": [1, 2],
        }.get(stage, [2, 2])
        assert row["epochs_after_restart_and_replay"] == [2, 2]
        if stage == "workspace":
            assert row["worktree_prepared_at_interruption"]
        assert row["invalid_activation_http"] == 403 and row["delayed_old_generation_http"] == 412
        assert row["effects_and_receipts_before_publish"] == [0, 0]
        assert row["effects_and_receipts_after_first_publish"] == ([0, 0] if stage == "before" else [1, 1])
        assert row["effect_receiver_exit"] == {"before": 22, "after": 23}.get(stage)
        assert row["final_status"] == "confirmed" and row["final_effects_and_receipts"] == [1, 1]
    files = ("evals/authenticated_recovery.py", "evals/durable_activation.py",
             "continuity/publish.py", "continuity/store.py")
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": {"os": platform.system(), "architecture": platform.machine(),
                        "python": platform.python_version(), "git": git(PROJECT, "--version").decode().strip()},
        "source_sha256": {name: sha((PROJECT / name).read_bytes()) for name in files},
        "credential_controls": credential_controls, "fault_trials": faults, "restore_trials": restored,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
