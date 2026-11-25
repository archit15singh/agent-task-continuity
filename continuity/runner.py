"""Subprocess boundaries for runtime handoffs, supervision, and verification."""

import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time

from .store import new_id
from .workspace import ContinuityError, capture, fingerprint, git, restore


def run(command, workspace, *, seconds, environment=None, log=None):
    if not command or seconds <= 0:
        raise ContinuityError("Specify a command and a positive timeout")
    started = time.monotonic()
    with tempfile.TemporaryFile() as output:
        with subprocess.Popen(
            command, cwd=workspace, env=environment, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
        ) as process:
            timed_out = False
            try:
                status = process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                status = 124
            finally:
                # A worker can leave background descendants even after its main process exits.
                stop(process)
        output.seek(0)
        digest = hashlib.sha256()
        if log is None:
            for chunk in iter(lambda: output.read(65536), b""):
                digest.update(chunk)
        else:
            with Path(log).open("xb") as destination:
                for chunk in iter(lambda: output.read(65536), b""):
                    digest.update(chunk)
                    destination.write(chunk)
    return {
        "exit_code": status, "timed_out": timed_out, "output_sha256": digest.hexdigest(),
        "seconds": round(time.monotonic() - started, 4),
    }


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def verify(store, task_id, token, command, seconds, log=None):
    with store.connection() as conn:
        task = store.task(conn, task_id, token)
        snapshot = store.latest(conn, task)
    includes = json.loads(snapshot["includes"])
    if fingerprint(*capture(task["workspace"], includes)) != snapshot["digest"]:
        raise ContinuityError("Workspace differs from the checkpoint. Save a new checkpoint first.")
    with tempfile.TemporaryDirectory(prefix="continuity-verify-") as temp:
        checked = restore(task["workspace"], Path(temp) / "snapshot", snapshot["base"], snapshot["patch"])
        try:
            if fingerprint(*capture(checked, includes)) != snapshot["digest"]:
                raise ContinuityError("Verification checkout differs from the saved checkpoint")
            result = run(command, checked, seconds=seconds, log=log)
            if fingerprint(*capture(checked, includes)) != snapshot["digest"]:
                raise ContinuityError("Verification command changed the selected artifact")
        finally:
            git(task["workspace"], "worktree", "remove", "--force", str(checked))
    evidence = new_id()
    environment = {
        "os": platform.system(), "architecture": platform.machine(),
        "runner_python": platform.python_version(),
        "git": git(task["workspace"], "--version").decode().strip(),
    }
    with store.connection(write=True) as conn:
        current = store.task(conn, task_id, token)
        if current["checkpoint"] != snapshot["id"]:
            raise ContinuityError("Checkpoint changed during verification. Run verification again.")
        conn.execute("INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?)", (
            evidence, task_id, snapshot["id"], json.dumps(command), result["exit_code"],
            result["output_sha256"], json.dumps(environment),
        ))
    return {**result, "evidence": evidence, "checkpoint": snapshot["id"],
            "digest": snapshot["digest"], "environment": environment}


def supervise(store, task_id, token, first, replacement, workspace, seconds, recovery_seconds, logs):
    with store.connection() as conn:
        task = store.task(conn, task_id, token)
        store.latest(conn, task)
    env = dict(
        os.environ, CONTINUITY_DB=str(store.path), CONTINUITY_TASK=task_id,
        CONTINUITY_OWNER=token,
    )
    env.pop("CONTINUITY_RECOVERY_KEY", None)
    result = run(first, task["workspace"], seconds=seconds, environment=env,
                 log=logs[0] if logs else None)
    if result["exit_code"] == 0:
        return {"initial": result, "recovered": False}
    resumed = store.takeover(task_id, token, workspace)
    env.update(CONTINUITY_OWNER=resumed["token"], CONTINUITY_PROMPT=resumed["prompt"])
    recovery = run(replacement, resumed["workspace"], seconds=recovery_seconds, environment=env,
                   log=logs[1] if logs else None)
    return {"initial": result, "recovered": True, "takeover": resumed, "replacement": recovery}


def runtime_command(runtime, prompt, model=None):
    if runtime == "codex":
        command = [
            "codex", "-a", "never", "exec", "--ignore-user-config", "--ignore-rules",
            "--sandbox", "workspace-write", "--ephemeral", "--json",
        ]
    elif runtime == "opencode":
        command = ["opencode", "run", "--standalone", "--format", "json"]
    else:
        raise ContinuityError(f"Unsupported runtime: {runtime}")
    if model:
        command.extend(["-m", model])
    return [*command, prompt]


def launch(runtime, handoff, model, seconds, log):
    # Keep ownership credentials out of the resumed worker's environment.
    environment = {key: value for key, value in os.environ.items() if key not in {"CONTINUITY_OWNER", "CONTINUITY_RECOVERY_KEY"}}
    return run(runtime_command(runtime, handoff["prompt"], model), handoff["workspace"],
               seconds=seconds, environment=environment, log=log)
