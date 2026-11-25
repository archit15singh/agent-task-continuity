"""Command-line interface for local coding-task continuity."""

import argparse
import json
import os
import shlex
import sqlite3
import sys

from .publish import publish, settle
from .runner import launch, supervise, verify
from .store import Store
from .workspace import ContinuityError


def parser():
    cli = argparse.ArgumentParser(prog="python -m continuity", description=__doc__)
    cli.add_argument("--db", default=os.environ.get("CONTINUITY_DB", ".continuity/tasks.sqlite"))
    commands = cli.add_subparsers(dest="action", required=True)
    start = commands.add_parser("start", help="create a task rooted at an existing Git worktree")
    start.add_argument("workspace")
    start.add_argument("--objective", required=True)

    def task_command(name, help_text, owner=True):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("task")
        if owner:
            command.add_argument("--owner", default=os.environ.get("CONTINUITY_OWNER"),
                                 help="prefer setting CONTINUITY_OWNER")
        return command

    checkpoint = task_command("checkpoint", "capture a recoverable workspace revision")
    checkpoint.add_argument("--include", action="append", default=[], metavar="FILE")
    checkpoint.add_argument("--note", required=True)
    examine = task_command("inspect", "compare a workspace with its checkpoint", owner=False)
    examine.add_argument("--workspace")

    handoff = task_command("continue", "restore a task in an isolated worktree and transfer ownership")
    handoff.add_argument("--into", required=True)
    handoff.add_argument("--runtime", choices=("codex", "opencode"))
    handoff.add_argument("--model")
    handoff.add_argument("--timeout", type=int, default=180)
    handoff.add_argument("--log")

    watcher = task_command("supervise", "replace a failed or timed-out worker from its last checkpoint")
    watcher.add_argument("--first", required=True, help="shell-quoted argv, executed without a shell")
    watcher.add_argument("--replacement", required=True, help="shell-quoted argv, without a shell")
    watcher.add_argument("--into", required=True)
    watcher.add_argument("--timeout", type=int, default=180)
    watcher.add_argument("--recovery-timeout", type=int, default=180)
    watcher.add_argument("--logs", nargs=2)

    rotate = task_command("recover-owner", "recover a task if the current owner token is lost", owner=False)
    rotate.add_argument("--into", required=True)

    check = task_command("verify", "run a verification command in a disposable copy of the checkpoint")
    check.add_argument("--command", required=True, help="shell-quoted argv, executed without a shell")
    check.add_argument("--timeout", type=int, default=120)
    check.add_argument("--log")

    send = task_command("publish", "publish a verified checkpoint to a loopback service")
    send.add_argument("--endpoint", required=True)
    send.add_argument("--name", required=True)
    send.add_argument("--evidence", required=True)
    recover = task_command("reconcile", "look up an operation using the current owner")
    recover.add_argument("operation")
    recover.add_argument("--retry-absent", action="store_true")
    task_command("operations", "list operation IDs and dispositions for this task", owner=False)
    return cli


def execute(args, store):
    if args.action == "start":
        return store.create(args.workspace, args.objective), 0
    task = args.task
    if args.action == "inspect":
        return store.inspect(task, args.workspace), 0
    if args.action == "operations":
        with store.connection() as conn:
            store.task(conn, task)
            rows = conn.execute("SELECT id, status FROM operation WHERE task=? ORDER BY rowid", (task,))
            return [dict(row) for row in rows], 0
    if args.action == "recover-owner":
        recovery = os.environ.get("CONTINUITY_RECOVERY_KEY")
        if not recovery:
            raise ContinuityError("Set CONTINUITY_RECOVERY_KEY to the operator recovery key")
        return store.recover_owner(task, recovery, args.into), 0
    token = args.owner
    if not token:
        raise ContinuityError("Set CONTINUITY_OWNER to the current owner token")
    if args.action == "checkpoint":
        return store.checkpoint(task, token, args.include, args.note), 0
    if args.action == "continue":
        result = store.takeover(task, token, args.into)
        if args.runtime:
            try:
                result["run"] = launch(args.runtime, result, args.model, args.timeout, args.log)
            except (ContinuityError, OSError, ValueError) as error:
                # Still return the new owner credential after an adapter launch failure.
                result["run"] = {"exit_code": 2, "error": str(error)}
        return result, result.get("run", {}).get("exit_code", 0)
    if args.action == "supervise":
        result = supervise(store, task, token, shlex.split(args.first), shlex.split(args.replacement),
                           args.into, args.timeout, args.recovery_timeout, args.logs)
        return result, result.get("replacement", result["initial"])["exit_code"]
    if args.action == "verify":
        result = verify(store, task, token, shlex.split(args.command), args.timeout, args.log)
        return result, result["exit_code"]
    if args.action == "publish":
        result = publish(store, task, token, args.endpoint, args.name, args.evidence)
    else:
        result = settle(store, task, token, args.operation, retry_absent=args.retry_absent)
    return result, 0 if result["status"] == "confirmed" else 3


def main():
    args = parser().parse_args()
    try:
        result, status = execute(args, Store(args.db))
    except (ContinuityError, OSError, ValueError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    sys.exit(main())
