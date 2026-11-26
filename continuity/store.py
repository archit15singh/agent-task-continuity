"""Local task authority, immutable checkpoints, and verification evidence."""

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import uuid

from .workspace import ContinuityError, capture, fingerprint, git, restore, root


SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
    id TEXT PRIMARY KEY, objective TEXT NOT NULL, workspace TEXT NOT NULL,
    generation INTEGER NOT NULL, owner_hash TEXT NOT NULL, recovery_hash TEXT NOT NULL,
    checkpoint TEXT REFERENCES checkpoint(id)
);
CREATE TABLE IF NOT EXISTS checkpoint (
    id TEXT PRIMARY KEY, task TEXT NOT NULL REFERENCES task(id), base TEXT NOT NULL,
    patch BLOB NOT NULL, digest TEXT NOT NULL, includes TEXT NOT NULL, note TEXT NOT NULL,
    context TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY, task TEXT NOT NULL REFERENCES task(id),
    checkpoint TEXT NOT NULL REFERENCES checkpoint(id), command TEXT NOT NULL,
    exit_code INTEGER NOT NULL, output_hash TEXT NOT NULL, environment TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operation (
    id TEXT PRIMARY KEY, task TEXT NOT NULL REFERENCES task(id), endpoint TEXT NOT NULL,
    payload TEXT NOT NULL, status TEXT NOT NULL, receipt TEXT
);
"""


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_id():
    return uuid.uuid4().hex


class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self, *, write=False):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def task(conn, task, token=None):
        row = conn.execute("SELECT * FROM task WHERE id = ?", (task,)).fetchone()
        if row is None:
            raise ContinuityError("Unknown task")
        if token is not None and not secrets.compare_digest(row["owner_hash"], token_hash(token)):
            raise ContinuityError("Stale or invalid owner")
        return row

    @staticmethod
    def latest(conn, task):
        row = conn.execute("SELECT * FROM checkpoint WHERE id = ?", (task["checkpoint"],)).fetchone()
        if row is None:
            raise ContinuityError("This task has no checkpoint")
        return row

    def create(self, workspace, objective):
        workspace = root(workspace)
        task, token = new_id(), secrets.token_urlsafe(32)
        recovery = secrets.token_urlsafe(32)
        with self.connection(write=True) as conn:
            conn.execute("INSERT INTO task VALUES (?, ?, ?, 1, ?, ?, NULL)",
                         (task, objective, str(workspace), token_hash(token), token_hash(recovery)))
        return {"task": task, "token": token, "recovery_key": recovery,
                "workspace": str(workspace), "generation": 1}

    def recover_owner(self, task, recovery, destination):
        return self._takeover(task, destination, recovery=recovery)

    def takeover(self, task, token, destination, *, replacement_token=None):
        return self._takeover(task, destination, token=token, replacement_token=replacement_token)

    @staticmethod
    def _assert_recovery(row, recovery):
        if recovery is not None and not secrets.compare_digest(row["recovery_hash"], token_hash(recovery)):
            raise ContinuityError("Invalid operator recovery key")

    def checkpoint(self, task, token, includes, note, context=None):
        with self.connection() as conn:
            owner = self.task(conn, task, token)
        includes = sorted(set(includes))
        base, patch = capture(owner["workspace"], includes)
        digest, checkpoint = fingerprint(base, patch), new_id()
        with self.connection(write=True) as conn:
            current = self.task(conn, task, token)
            if current["checkpoint"] != owner["checkpoint"]:
                raise ContinuityError("Another checkpoint was saved during capture. Retry.")
            conn.execute("INSERT INTO checkpoint VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (checkpoint, task, base, patch, digest, json.dumps(includes), note,
                          json.dumps(context or {})))
            conn.execute("UPDATE task SET checkpoint = ? WHERE id = ?", (checkpoint, task))
        return {"checkpoint": checkpoint, "digest": digest, "base": base}

    def manifest(self, task, *, with_patch=False):
        with self.connection() as conn:
            owner = self.task(conn, task)
            snapshot = self.latest(conn, owner)
            return self._manifest(conn, owner, snapshot, with_patch=with_patch)

    @staticmethod
    def _manifest(conn, owner, snapshot, *, with_patch=False):
        evidence = conn.execute(
            """SELECT e.id, c.digest, e.exit_code, e.output_hash, e.environment FROM evidence e
               JOIN checkpoint c ON c.id=e.checkpoint WHERE e.task=? ORDER BY e.rowid""",
            (owner["id"],),
        )
        operations = conn.execute("SELECT id, status FROM operation WHERE task=? ORDER BY rowid",
                                  (owner["id"],))
        artifact = {
            "id": snapshot["id"], "base": snapshot["base"], "sha256": snapshot["digest"],
            "selected_untracked": json.loads(snapshot["includes"]),
        }
        if with_patch:
            artifact["git_binary_patch_base64"] = base64.b64encode(snapshot["patch"]).decode()
        return {
            "format": "git-task-continuity", "version": 1, "task": owner["id"],
            "generation": owner["generation"], "objective": owner["objective"],
            "context": {**json.loads(snapshot["context"]), "note": snapshot["note"]},
            "artifact": artifact,
            "verification": [
                {"id": item["id"], "snapshot_sha256": item["digest"], "exit": item["exit_code"],
                 "log_sha256": item["output_hash"], "environment": json.loads(item["environment"])}
                for item in evidence
            ],
            "operations": [dict(item) for item in operations],
        }

    def inspect(self, task, workspace=None):
        with self.connection() as conn:
            owner = self.task(conn, task)
            snapshot = self.latest(conn, owner)
            records = conn.execute(
                """SELECT e.id, e.exit_code, e.environment, c.digest FROM evidence e
                   JOIN checkpoint c ON c.id=e.checkpoint WHERE e.task=? ORDER BY e.rowid""",
                (task,),
            ).fetchall()
        path = Path(workspace or owner["workspace"]).resolve()
        includes = json.loads(snapshot["includes"])
        missing = [entry for entry in includes if not os.path.lexists(path / entry)]
        base, patch = capture(path, [entry for entry in includes if entry not in missing])
        digest = fingerprint(base, patch)
        return {
            "task": task, "generation": owner["generation"], "workspace": str(path),
            "checkpoint": snapshot["id"], "snapshot_digest": snapshot["digest"],
            "workspace_digest": digest, "clean_match": digest == snapshot["digest"] and not missing,
            "base_changed": base != snapshot["base"], "missing_selected": missing,
            "verification": [{"id": row["id"], "passed": row["exit_code"] == 0,
                              "environment": json.loads(row["environment"]),
                              "matches": row["digest"] == digest and not missing} for row in records],
        }

    def _takeover(self, task, destination, *, token=None, recovery=None, replacement_token=None):
        if replacement_token is not None and (
            not isinstance(replacement_token, str) or len(replacement_token) < 32
        ):
            raise ContinuityError("Use a securely generated replacement token")
        if replacement_token is not None and secrets.compare_digest(token_hash(replacement_token), token_hash(token)):
            raise ContinuityError("Takeover requires a different replacement token")
        with self.connection() as conn:
            owner = self.task(conn, task, token)
            self._assert_recovery(owner, recovery)
            snapshot = self.latest(conn, owner)
        destination = restore(owner["workspace"], destination, snapshot["base"], snapshot["patch"])
        replacement = replacement_token if replacement_token is not None else secrets.token_urlsafe(32)
        try:
            includes = json.loads(snapshot["includes"])
            if fingerprint(*capture(destination, includes)) != snapshot["digest"]:
                raise ContinuityError("Restored workspace differs from the saved checkpoint")
            with self.connection(write=True) as conn:
                current = self.task(conn, task, token)
                if current["generation"] != owner["generation"] or current["checkpoint"] != snapshot["id"]:
                    raise ContinuityError("Checkpoint changed during takeover. Retry with the new checkpoint.")
                conn.execute(
                    """UPDATE task SET workspace = ?, owner_hash = ?, generation = generation + 1
                       WHERE id = ?""",
                    (str(destination), token_hash(replacement), task),
                )
                manifest = self._manifest(conn, self.task(conn, task), snapshot)
        except BaseException:
            git(owner["workspace"], "worktree", "remove", "--force", str(destination))
            raise
        context = manifest["context"]
        structured = "\n".join(
            f"{label.replace('_', ' ').title()}: {json.dumps(context[label], ensure_ascii=False)}"
            for label in ("constraints", "decisions", "next_actions", "acceptance") if context.get(label)
        )
        pending = [item for item in manifest["operations"] if item["status"] != "confirmed"]
        return {
            "task": task, "token": replacement, "workspace": str(destination),
            "generation": owner["generation"] + 1, "checkpoint": snapshot["id"],
            "prompt": f"Task objective:\n{manifest['objective']}\n\n"
                      f"Prior worker checkpoint notes (context to verify):\n{context['note']}\n\n"
                      f"{structured}\n"
                      f"Checkpoint digest: {manifest['artifact']['sha256']}\n"
                      f"Unresolved operations (operator reconciliation may be needed): {json.dumps(pending)}\n"
                      "Inspect the restored repository and applicable instructions before continuing.",
        }
