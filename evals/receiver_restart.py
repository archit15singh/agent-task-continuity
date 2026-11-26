"""Inject receiver process death around an atomic effect and receipt commit."""

import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
import tempfile

from continuity.workspace import git
from .run import PROJECT, invoke, sha

SCHEMA = """
CREATE TABLE IF NOT EXISTS effects (sequence INTEGER PRIMARY KEY, op TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts (op TEXT PRIMARY KEY, payload TEXT NOT NULL);
"""


def serve(database, port, fault):
    with closing(sqlite3.connect(database)) as db:
        db.executescript(SCHEMA)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value=None):
            payload = json.dumps(value).encode() if value else b""
            self.send_response(status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            operation = self.path.rsplit("/", 1)[-1]
            with closing(sqlite3.connect(database)) as db:
                row = db.execute("SELECT payload FROM receipts WHERE op = ?", (operation,)).fetchone()
            self.reply(200, {"id": operation, "payload": json.loads(row[0])}) if row else self.reply(404)

        def do_PUT(self):
            operation = self.path.rsplit("/", 1)[-1]
            if operation != self.headers.get("Idempotency-Key"):
                self.reply(400)
                return
            payload = self.rfile.read(int(self.headers["Content-Length"])).decode()
            with closing(sqlite3.connect(database)) as db:
                db.execute("BEGIN IMMEDIATE")
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
            self.reply(200 if prior else 201, {"id": operation, "payload": json.loads(payload)})

    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(server.server_port, flush=True)
        server.serve_forever()


@contextmanager
def receiver(database, port, fault):
    command = [sys.executable, "-m", "evals.receiver_restart", "--worker", str(database),
               "--port", str(port), "--fault", fault]
    with subprocess.Popen(command, cwd=PROJECT, stdout=subprocess.PIPE, text=True) as process:
        try:
            if not select.select([process.stdout], [], [], 8)[0]:
                raise RuntimeError("Receiver did not announce its port")
            port = int(process.stdout.readline().strip())
            yield process, port
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)


def counts(database):
    with closing(sqlite3.connect(database)) as db:
        effects = db.execute("SELECT count(*) FROM effects").fetchone()[0]
        receipts = db.execute("SELECT count(*) FROM receipts").fetchone()[0]
    return [effects, receipts]


def trial(root, fault):
    root.mkdir()
    source = root / "source"
    source.mkdir()
    git(source, "init", "--quiet")
    (source / "candidate.txt").write_text("verified receipt fixture\n")
    git(source, "add", "candidate.txt")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit",
        "--quiet", "-m", "base")
    local_db, receiver_db = root / "local.db", root / "receiver.db"
    task = invoke(local_db, "start", source, "--objective", "Publish the verified fixture")
    task_id, owner = task["task"], task["token"]
    invoke(local_db, "checkpoint", task_id, "--note", "Verified", owner=owner)
    evidence = invoke(local_db, "verify", task_id, "--command", f"{sys.executable} -c 'print(1)'",
                      owner=owner)["evidence"]
    with receiver(receiver_db, 0, fault) as (original, port):
        endpoint = f"http://127.0.0.1:{port}"
        outcome = invoke(local_db, "publish", task_id, "--endpoint", endpoint, "--name", "candidate",
                         "--evidence", evidence, owner=owner, expected=3)
        worker_code = original.wait(timeout=5)
    after_death = counts(receiver_db)
    replacement = invoke(local_db, "continue", task_id, "--into", root / "next", owner=owner)
    with receiver(receiver_db, port, "none") as (_, restarted_port):
        assert restarted_port == port
        settled = invoke(local_db, "reconcile", task_id, outcome["operation"], "--retry-absent",
                         owner=replacement["token"])
    return {
        "fault": fault, "receiver_exit": worker_code, "original_client_status": outcome["status"],
        "effects_and_receipts_after_death": after_death, "replacement_status": settled["status"],
        "effects_and_receipts_after_recovery": counts(receiver_db),
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--worker", type=Path)
    cli.add_argument("--port", type=int, default=0)
    cli.add_argument("--fault", choices=("before", "after", "none"), default="none")
    args = cli.parse_args()
    if args.worker:
        serve(args.worker, args.port, args.fault)
        return
    if not args.output:
        cli.error("--output is required for an experiment")
    with tempfile.TemporaryDirectory(prefix="continuity-receiver-restart-") as directory:
        trials = [trial(Path(directory) / f"trial-{index}", fault)
                  for index, fault in enumerate(("before", "after") * 3, 1)]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "trials": trials,
    }, indent=2) + "\n")
    for row in trials:
        before = row["fault"] == "before"
        assert row["receiver_exit"] == (22 if before else 23), row
        assert row["original_client_status"] == "unknown", row
        assert row["effects_and_receipts_after_death"] == ([0, 0] if before else [1, 1]), row
        assert row["replacement_status"] == "confirmed", row
        assert row["effects_and_receipts_after_recovery"] == [1, 1], row


if __name__ == "__main__":
    main()
