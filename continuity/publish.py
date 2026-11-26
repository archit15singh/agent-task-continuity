"""Fence managed writes and reconcile uncertain responses by operation ID."""

import hashlib
import http.client
import json
from urllib.parse import urlsplit

from .workspace import ContinuityError


def json_text(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def endpoint_url(endpoint):
    url = urlsplit(endpoint)
    if (
        url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port
        or url.username or url.password or url.path not in ("", "/") or url.query or url.fragment
    ):
        raise ContinuityError("Provide a loopback fixture endpoint, such as http://127.0.0.1:8000")
    return f"http://127.0.0.1:{url.port}"


def request(endpoint, operation, payload=None, *, generation=None):
    conn = http.client.HTTPConnection("127.0.0.1", urlsplit(endpoint).port, timeout=3)
    try:
        route = f"/events/{operation}"
        if payload is None:
            conn.request("GET", route)
        else:
            headers = {"Content-Type": "application/json", "Idempotency-Key": operation}
            if generation is not None:
                headers["X-Continuity-Generation"] = str(generation)
            conn.request("PUT", route, body=payload.encode(), headers=headers)
        response = conn.getresponse()
        body = response.read(65537)
        if payload is None and response.status == 404:
            return None
        if response.status not in (200, 201) or len(body) > 65536:
            raise ContinuityError(f"Provider returned HTTP {response.status}")
        receipt = json.loads(body)
        if not isinstance(receipt, dict) or receipt.get("id") != operation:
            raise ContinuityError("Provider returned a receipt for the wrong operation")
        return receipt
    finally:
        conn.close()


def publish(store, task_id, token, endpoint, name, evidence):
    endpoint = endpoint_url(endpoint)
    operation = hashlib.sha256(f"{task_id}\0{name}".encode()).hexdigest()
    with store.connection(write=True) as conn:
        task = store.task(conn, task_id, token)
        checkpoint = store.latest(conn, task)
        verified = conn.execute(
            """SELECT evidence.exit_code, checkpoint.digest FROM evidence
               JOIN checkpoint ON checkpoint.id = evidence.checkpoint
               WHERE evidence.id = ? AND evidence.task = ?""", (evidence, task_id),
        ).fetchone()
        if not verified or verified["exit_code"] or verified["digest"] != checkpoint["digest"]:
            raise ContinuityError("Publishing requires passing evidence for this snapshot")
        payload = json_text({
            "task": task_id, "name": name, "digest": checkpoint["digest"], "base": checkpoint["base"],
        })
        row = conn.execute("SELECT * FROM operation WHERE id = ?", (operation,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO operation VALUES (?, ?, ?, ?, 'reserved', NULL)",
                         (operation, task_id, endpoint, payload))
        elif (row["payload"], row["endpoint"]) != (payload, endpoint):
            raise ContinuityError("This operation name already refers to a different write")
    return settle(store, task_id, token, operation, retry_absent=True)


def settle(store, task_id, token, operation, *, retry_absent=False):
    # Serialize send initiation against takeover. A started request can outlive a killed owner.
    # A stable provider key handles that race after SQLite releases the local writer lock.
    with store.connection(write=True) as conn:
        task = store.task(conn, task_id, token)
        row = conn.execute("SELECT * FROM operation WHERE id = ? AND task = ?",
                           (operation, task_id)).fetchone()
        if row is None:
            raise ContinuityError("Unknown operation for this task")
        if row["status"] == "confirmed":
            return {"operation": operation, "status": "confirmed", "receipt": json.loads(row["receipt"])}
        try:
            receipt = request(row["endpoint"], operation)
            if receipt is None and retry_absent:
                receipt = request(
                    row["endpoint"], operation, row["payload"], generation=task["generation"],
                )
            if receipt is not None and json_text(receipt.get("payload")) != row["payload"]:
                raise ContinuityError("Provider receipt does not match the reserved payload")
        except (ContinuityError, OSError, http.client.HTTPException, ValueError) as error:
            conn.execute("UPDATE operation SET status = 'unknown' WHERE id = ?", (operation,))
            return {"operation": operation, "status": "unknown", "reason": str(error)}
        if receipt is None:
            return {"operation": operation, "status": "absent"}
        conn.execute("UPDATE operation SET status = 'confirmed', receipt = ? WHERE id = ?",
                     (json_text(receipt), operation))
    return {"operation": operation, "status": "confirmed", "receipt": receipt}
