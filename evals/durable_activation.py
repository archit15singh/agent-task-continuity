"""Combine restartable activation, receiver generations, and transactional effects."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from continuity.publish import json_text, request
from continuity.store import Store
from continuity.workspace import ContinuityError, git, restore
from .receiver_restart import SCHEMA, counts, receiver
from .run import PROJECT, invoke, sha

MODULE = "evals.durable_activation"
ACTIVATION_ENV = "CONTINUITY_FIXTURE_ACTIVATION_KEY"
INTENT = """
CREATE TABLE IF NOT EXISTS intent (
    task TEXT PRIMARY KEY, old_owner TEXT NOT NULL, next_owner TEXT NOT NULL,
    destination TEXT NOT NULL, expected INTEGER NOT NULL, checkpoint TEXT NOT NULL,
    complete INTEGER NOT NULL DEFAULT 0
);
"""


def serve(database, port, fault, secret):
    with closing(sqlite3.connect(database)) as db:
        db.executescript(SCHEMA + "CREATE TABLE IF NOT EXISTS epochs(task TEXT PRIMARY KEY, current INTEGER NOT NULL);")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value=None):
            payload = json.dumps(value).encode() if value is not None else b""
            self.send_response(status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def data(self):
            size = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= size <= 65536:
                raise ValueError("Invalid size")
            return json.loads(self.rfile.read(size))

        def do_GET(self):
            operation = re.fullmatch(r"/events/([0-9a-f]{64})", self.path)
            if not operation:
                self.reply(404)
                return
            key = operation[1]
            with closing(sqlite3.connect(database)) as db:
                row = db.execute("SELECT payload FROM receipts WHERE op = ?", (key,)).fetchone()
            self.reply(200, {"id": key, "payload": json.loads(row[0])}) if row else self.reply(404)

        def do_POST(self):
            task = re.fullmatch(r"/activation/([0-9a-f]+)", self.path)
            if not task or not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + secret):
                self.reply(403)
                return
            try:
                body = self.data()
                expected = body["expected"]
                if type(expected) is not int or expected < 0:
                    raise ValueError("Invalid generation")
            except (KeyError, TypeError, ValueError):
                self.reply(400)
                return
            with closing(sqlite3.connect(database)) as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT current FROM epochs WHERE task = ?", (task[1],)).fetchone()
                current = row[0] if row else 0
                target = expected + 1
                if current not in (expected, target):
                    self.reply(409)
                    return
                if current == expected:
                    db.execute(
                        "INSERT INTO epochs VALUES (?, ?) ON CONFLICT(task) DO UPDATE SET current = excluded.current",
                        (task[1], target),
                    )
                db.commit()
            self.reply(200, {"generation": target})

        def do_PUT(self):
            match = re.fullmatch(r"/events/([0-9a-f]{64})", self.path)
            if not match or self.headers.get("Idempotency-Key") != match[1]:
                self.reply(400)
                return
            try:
                body = self.data()
                task = body["task"]
                if not isinstance(task, str):
                    raise ValueError("Invalid task")
                generation = int(self.headers.get("X-Continuity-Generation", "0"))
            except (KeyError, TypeError, ValueError):
                self.reply(400)
                return
            operation = match[1]
            payload = json_text(body)
            with closing(sqlite3.connect(database)) as db:
                db.execute("BEGIN IMMEDIATE")
                epoch = db.execute("SELECT current FROM epochs WHERE task = ?", (task,)).fetchone()
                if epoch != (generation,):
                    self.reply(412)
                    return
                prior = db.execute("SELECT payload FROM receipts WHERE op = ?", (operation,)).fetchone()
                if prior and prior[0] != payload:
                    self.reply(409)
                    return
                if not prior:
                    db.execute("INSERT INTO effects(op) VALUES (?)", (operation,))
                    db.execute("INSERT INTO receipts VALUES (?, ?)", (operation, payload))
                    if fault == "before":
                        os._exit(22)
                    db.commit()
                    if fault == "after":
                        os._exit(23)
            self.reply(200 if prior else 201, {"id": operation, "payload": body})

    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(server.server_port, flush=True)
        server.serve_forever()


def advance(endpoint, key, task, expected):
    req = Request(
        endpoint + "/activation/" + task, data=json_text({"expected": expected}).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urlopen(req, timeout=5) as response:
        return json.load(response)["generation"]


def coordinate(directory, endpoint, fault, secret):
    with closing(sqlite3.connect(directory / "intent.db")) as db:
        task, old, successor, destination, expected, checkpoint, complete = db.execute("SELECT * FROM intent").fetchone()
        if complete:
            return
        if fault == "intent":
            os._exit(31)
        target = advance(endpoint, secret, task, expected)
        if fault == "receiver":
            os._exit(32)
        store = Store(directory / "local.db")
        with store.connection() as conn:
            current = store.task(conn, task)["generation"]
        if current == expected:
            if fault == "workspace":
                with store.connection() as conn:
                    owner = store.task(conn, task, old)
                    snapshot = store.latest(conn, owner)
                assert snapshot["id"] == checkpoint
                restore(owner["workspace"], destination, snapshot["base"], snapshot["patch"])
                os._exit(34)
            store.takeover(
                task, old, destination, replacement_token=successor, expected_checkpoint=checkpoint,
                prepared=Path(destination).exists(),
            )
        with store.connection() as conn:
            verified = store.task(conn, task, successor)
            if (verified["generation"], verified["workspace"], verified["checkpoint"]) != (
                target, str(Path(destination).resolve()), checkpoint,
            ):
                raise RuntimeError("Local generation or workspace differs from the intent")
        if fault == "local":
            os._exit(33)
        db.execute("UPDATE intent SET complete = 1 WHERE task = ?", (task,))
        db.commit()


def trial(root, stage):
    root.mkdir()
    source = root / "source"
    source.mkdir()
    git(source, "init", "--quiet")
    (source / "candidate.txt").write_text("verified payload\n")
    git(source, "add", "candidate.txt")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "-m", "base")
    local, database = root / "local.db", root / "receiver.db"
    task = invoke(local, "start", source, "--objective", "Verify a candidate after durable activation")
    task_id, old = task["task"], task["token"]
    saved = invoke(local, "checkpoint", task_id, "--note", "Verified candidate", owner=old)
    evidence = invoke(local, "verify", task_id, "--command", f"{sys.executable} -c 'print(1)'", owner=old)
    successor, key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    env = dict(os.environ, **{ACTIVATION_ENV: key})

    def read_epochs():
        with closing(sqlite3.connect(database)) as db:
            receiver_epoch = db.execute("SELECT current FROM epochs WHERE task = ?", (task_id,)).fetchone()[0]
        return [invoke(local, "inspect", task_id)["generation"], receiver_epoch]

    def run_coordinator(fault):
        return subprocess.run([sys.executable, "-m", MODULE, "--coordinate", str(root),
                               "--endpoint", endpoint, "--fault", fault],
                              cwd=PROJECT, env=env, timeout=30, check=False).returncode

    with receiver(database, 0, "none", module=MODULE, env=env) as (_, port):
        endpoint = f"http://127.0.0.1:{port}"
        try:
            advance(endpoint, "invalid-fixture-key", task_id, 0)
        except HTTPError as error:
            if error.code != 403:
                raise
            auth_control = error.code
        else:
            raise AssertionError("Unauthenticated activation passed")
        assert advance(endpoint, key, task_id, 0) == 1
        with closing(sqlite3.connect(root / "intent.db")) as db:
            db.executescript(INTENT)
            db.execute("INSERT INTO intent VALUES (?, ?, ?, ?, ?, ?, 0)",
                       (task_id, old, successor, str(root / "replacement"), 1, saved["checkpoint"]))
            db.commit()
        coordinator_exit = run_coordinator(stage if stage in ("intent", "receiver", "workspace", "local") else "none")
        interrupted = read_epochs()
        prepared_at_interruption = (root / "replacement" / ".git").is_file()

    effect_fault = stage if stage in ("before", "after") else "none"
    with receiver(database, port, effect_fault, module=MODULE, env=env) as (active, _):
        assert read_epochs() == interrupted
        assert run_coordinator("none") == 0
        assert run_coordinator("none") == 0
        generations = read_epochs()
        op = sha(f"{task_id}\0candidate".encode())
        payload = json_text({
            "task": task_id, "name": "candidate", "digest": saved["digest"],
            "base": git(source, "rev-parse", "HEAD").decode().strip(),
        })
        try:
            request(endpoint, op, payload, generation=1)
        except ContinuityError as error:
            if str(error) != "Provider returned HTTP 412":
                raise
            delayed_status = 412
        else:
            raise AssertionError("Old generation applied an effect")
        before_publish = counts(database)
        first = invoke(local, "publish", task_id, "--endpoint", endpoint, "--name", "candidate",
                       "--evidence", evidence["evidence"], owner=successor,
                       expected=3 if effect_fault != "none" else 0)
        assert first["operation"] == op
        effect_exit = active.wait(timeout=5) if effect_fault != "none" else None
    after_first = counts(database)
    with receiver(database, port, "none", module=MODULE, env=env):
        assert read_epochs() == generations
        confirmed = invoke(local, "reconcile", task_id, op, "--retry-absent", owner=successor)
        assert request(endpoint, op)["payload"] == json.loads(payload)
    return {
        "fault": stage, "coordinator_exit": coordinator_exit, "epochs_at_interruption": interrupted,
        "epochs_after_restart_and_replay": generations, "worktree_prepared_at_interruption": prepared_at_interruption, "invalid_activation_http": auth_control,
        "delayed_old_generation_http": delayed_status, "effects_and_receipts_before_publish": before_publish,
        "first_publish_status": first["status"], "effect_receiver_exit": effect_exit,
        "effects_and_receipts_after_first_publish": after_first, "final_status": confirmed["status"],
        "final_effects_and_receipts": counts(database),
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--worker", type=Path)
    cli.add_argument("--coordinate", type=Path)
    cli.add_argument("--port", type=int, default=0)
    cli.add_argument("--fault", default="none")
    cli.add_argument("--endpoint")
    cli.add_argument("--workspace-only", action="store_true")
    args = cli.parse_args()
    if args.worker:
        serve(args.worker, args.port, args.fault, os.environ[ACTIVATION_ENV])
        return
    if args.coordinate:
        coordinate(args.coordinate, args.endpoint, args.fault, os.environ[ACTIVATION_ENV])
        return
    if not args.output:
        cli.error("--output is required")
    stages = ("workspace",) if args.workspace_only else ("intent", "receiver", "workspace", "local", "before", "after")
    with tempfile.TemporaryDirectory(prefix="continuity-durable-activation-") as directory:
        rows = [trial(Path(directory) / f"trial-{index}", stage) for index, stage in enumerate(stages * 3, 1)]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()), "trials": rows,
    }, indent=2) + "\n")
    for row in rows:
        stage = row["fault"]
        assert row["coordinator_exit"] == {"intent": 31, "receiver": 32, "workspace": 34, "local": 33}.get(stage, 0), row
        assert row["epochs_at_interruption"] == {"intent": [1, 1], "receiver": [1, 2], "workspace": [1, 2]}.get(stage, [2, 2]), row
        if stage == "workspace":
            assert row["worktree_prepared_at_interruption"], row
        assert row["epochs_after_restart_and_replay"] == [2, 2], row
        assert row["invalid_activation_http"] == 403 and row["delayed_old_generation_http"] == 412, row
        assert row["effects_and_receipts_before_publish"] == [0, 0], row
        assert row["effects_and_receipts_after_first_publish"] == ([0, 0] if stage == "before" else [1, 1]), row
        assert row["effect_receiver_exit"] == {"before": 22, "after": 23}.get(stage), row
        assert row["final_status"] == "confirmed" and row["final_effects_and_receipts"] == [1, 1], row


if __name__ == "__main__":
    main()
