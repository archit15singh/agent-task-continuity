"""Qualify the paired worker configurations with one scripted local edit per runtime."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread

from continuity.runner import run
from continuity.workspace import git
from .live import read_summary
from .opencode_boundary import mock_server
from .paired_continuation import worker_command
from .run import execute, sha

FILENAME = "fixture.txt"
BEFORE = b"fixture A\n"
AFTER = b"fixture B\n"


def responses_server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path != "/v1/responses":
                self.send_error(404)
                return
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            input_items = body.get("input", [])
            tools = {tool.get("name"): tool.get("type") for tool in body.get("tools", []) if tool.get("name")}
            index = len(requests)
            observed = {
                "exec_command_offered": tools.get("exec_command") == "function",
                "tool_result_present": any(
                    item.get("type") == "function_call_output" and item.get("call_id") == "call_fixture"
                    for item in input_items if isinstance(item, dict)
                ),
            }
            requests.append(observed)
            if index == 0 and observed["exec_command_offered"]:
                item = {
                    "type": "function_call", "id": "fc_fixture", "call_id": "call_fixture",
                    "name": "exec_command", "arguments": json.dumps({
                        "cmd": "printf 'fixture B\\n' > fixture.txt",
                    }),
                }
            elif index == 1:
                item = {"type": "message", "id": "msg_fixture", "role": "assistant",
                        "content": [{"type": "output_text", "text": "Done", "annotations": []}]}
            else:
                self.send_error(400)
                return
            response = {"id": f"resp_fixture_{index}", "model": body["model"], "object": "response",
                        "created_at": 0, "output": []}
            completed = {**response, "output": [{**item, "status": "completed"}], "status": "completed",
                         "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
                                   "input_tokens_details": {"cached_tokens": 0},
                                   "output_tokens_details": {"reasoning_tokens": 0}}}
            events = [
                ("response.created", {"response": {**response, "status": "in_progress"}}),
                ("response.output_item.added", {"output_index": 0, "item": {**item, "status": "in_progress"}}),
                ("response.output_item.done", {"output_index": 0, "item": {**item, "status": "completed"}}),
                ("response.completed", {"response": completed}),
            ]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for sequence, (event, fields) in enumerate(events):
                packet = {"type": event, "sequence_number": sequence, **fields}
                self.wfile.write(f"event: {event}\ndata: {json.dumps(packet)}\n\n".encode())

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler), requests


@contextmanager
def serve(runtime):
    if runtime == "codex":
        server, records = responses_server()
    else:
        server, records = mock_server([
            {"tool": "edit", "arguments": {"path": FILENAME, "oldString": BEFORE.decode(), "newString": AFTER.decode()}},
            {"text": "Done"},
        ])
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", records
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def trial(root, runtime):
    workspace, state, log = root / "workspace", root / "state", root / "worker.log"
    workspace.mkdir(parents=True)
    state.mkdir()
    git(workspace, "init", "--quiet")
    target = workspace / FILENAME
    target.write_bytes(BEFORE)
    with serve(runtime) as (local, requests):
        command, env = worker_command(runtime, "Update fixture.txt to say fixture B and finish.", local, state)
        outcome = run(command, workspace, seconds=35, environment=env, log=log)
    return {"runtime": runtime, "version": execute([runtime, "--version"]).stdout.decode().strip(),
            "requests": requests, "worker": {**outcome, **read_summary(log)},
            "expected_bytes": target.read_bytes() == AFTER, "source_sha256": sha(target.read_bytes())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-paired-tool-control-") as directory:
        root = Path(directory).resolve()
        results = [trial(root / runtime, runtime) for runtime in ("codex", "opencode")]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_sha256": sha(Path(__file__).read_bytes()), "trials": results,
    }, indent=2) + "\n")
    assert all(row["expected_bytes"] and row["worker"]["exit_code"] == 0 and len(row["requests"]) == 2
               and row["requests"][1]["tool_result_present"] for row in results)
