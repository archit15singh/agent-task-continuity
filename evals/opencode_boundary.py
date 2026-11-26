"""Exercise OpenCode's edit and compaction boundaries with a scripted provider."""

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread

from continuity.runner import run, runtime_command
from continuity.workspace import git
from .live import read_summary, worker_environment
from .run import CASES, check_argv, download, execute, sha

CLICK = next(case for case in CASES if case["id"] == "click")
MODEL = "continuity-local/fixture"


def mock_server(replies):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            messages = body.get("messages", [])
            index = len(requests)
            requests.append({
                "messages": len(messages),
                "tools": sorted(tool["function"]["name"] for tool in body.get("tools", [])),
                "tool_result_present": any(message.get("role") == "tool" for message in messages),
                "summary_present": any(
                    "Fixture summary marker" in json.dumps(message.get("content")) for message in messages
                ),
                "compaction_request": any(
                    "you must summarize the conversation above" in json.dumps(message.get("content")).lower()
                    for message in messages
                ),
            })
            reply = replies[index] if index < len(replies) else {"error": True}
            requests[-1]["scripted_response"] = (
                "http_400" if reply.get("error") else reply.get("finish", "stop" if "text" in reply else "tool_calls")
            )
            if reply.get("error"):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"fixture provider declined the request"}}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            delta = {"content": reply["text"]} if "text" in reply else {"tool_calls": [{
                "index": 0, "id": f"call_{index}", "type": "function",
                "function": {"name": reply["tool"], "arguments": json.dumps(reply["arguments"])},
            }]}
            used = reply.get("tokens", 200)
            chunks = [
                {"choices": [{"index": 0, "delta": {"role": "assistant", **delta}, "finish_reason": None}]},
                {"choices": [{"index": 0, "delta": {}, "finish_reason": (
                    reply.get("finish", "stop" if "text" in reply else "tool_calls")
                )}], "usage": {"prompt_tokens": used, "completion_tokens": 20, "total_tokens": used + 20}},
            ]
            for chunk in chunks:
                chunk.update(id=f"fixture-{index}", object="chat.completion.chunk", model="fixture", created=0)
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler), requests


def run_arm(workspace, temp, label, replies, *, auto, prompt):
    server, requests = mock_server(replies)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}/v1"
        env = worker_environment(endpoint, MODEL, None)
        config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        config["compaction"] = {"auto": auto, "background": False, "buffer": "50%", "keep": {"tokens": 0}}
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        log = temp / f"{label}.log"
        output = run(runtime_command("opencode", prompt, MODEL), workspace, seconds=35, log=log, environment=env)
        output.update(read_summary(log))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    return {"arm": label, "auto_compaction": auto, "requests": requests, "worker": output}


def click_arms(temp):
    source = download(CLICK, temp / "click", reference=False)
    target = CLICK["source"]
    full = (source / target).read_text()
    # Use intentionally distinct fake tokens. No fuzzy edit locator should match the negative.
    exact = next(line for line in full.splitlines() if line.strip() == "return cli.name or \"root\"")
    if full.count(exact + "\n") != 1:
        raise RuntimeError("Edit fixture anchor is not unique")
    title = {"text": "Click edit fixture"}
    reports = []
    for label, anchor in (("inexact", "__nonexistent_fixture_anchor__"), ("exact", exact)):
        workspace = temp / label
        git(source, "worktree", "add", "--quiet", "--detach", str(workspace), CLICK["base"])
        reply = {"tool": "edit", "arguments": {
            "path": target, "oldString": anchor,
            "newString": exact + "  # fixture changed",
        }}
        report = run_arm(workspace, temp, label, [title, reply, {"text": "Done"}], auto=False,
                         prompt="Follow the scripted edit request for the scoped Click file.")
        report["source_changed"] = (workspace / target).read_text() != full
        report["expected_bytes"] = (workspace / target).read_text() == (
            full.replace(exact + "\n", exact + "  # fixture changed\n") if label == "exact" else full
        )
        report["historical_predicate_exit"] = execute(check_argv(CLICK), cwd=workspace).returncode
        reports.append(report)
    return reports


def compaction_arms(temp):
    reports = []
    summary = "## Objective\nFixture summary marker.\n\n## Next Move\nFinish the task."
    for label, auto, tokens, summary_replies in (
        ("low_usage", True, 200, []),
        ("high_usage_auto_off", False, 16000, []),
        ("high_usage_summary_ok", True, 16000, [{"text": summary}]),
        ("high_usage_summary_error", True, 16000, [{"error": True}]),
        ("high_usage_summary_truncated", True, 16000, [{"text": summary, "finish": "length"}]),
    ):
        workspace = temp / label
        workspace.mkdir()
        (workspace / "input.txt").write_text("fixture\n")
        first = {"tool": "read", "arguments": {"path": "input.txt"}, "tokens": tokens}
        done = {"text": "Fixture task finished."}
        replies = [first, *summary_replies, done]
        reports.append(run_arm(workspace, temp, label, [{"text": "Compaction fixture"}, *replies], auto=auto,
                               prompt="Read input.txt and then finish. Keep the fixture unchanged."))
    return reports


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-boundary-") as directory:
        temp = Path(directory)
        report = {
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
            "opencode": execute(["opencode", "--version"]).stdout.decode().strip(),
            "click_base": CLICK["base"],
            "edit": click_arms(temp),
            "compaction": compaction_arms(temp),
        }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if [item["source_changed"] for item in report["edit"]] != [False, True] or not all(
        item["expected_bytes"] and item["historical_predicate_exit"] == 1 for item in report["edit"]
    ):
        raise RuntimeError("Edit outcomes differed from the fixture expectations")
    outcomes = [item["worker"]["provider_error_type"] for item in report["compaction"]]
    if outcomes != [None, None, None, "provider.invalid-request", "compaction.failed"]:
        raise RuntimeError(f"Compaction outcomes differed from the fixture expectations: {outcomes}")
    summary_counts = [sum(r["compaction_request"] for r in item["requests"]) for item in report["compaction"]]
    if summary_counts != [0, 0, 1, 1, 1] or not report["compaction"][2]["requests"][-1]["summary_present"]:
        raise RuntimeError("Compaction request and continuation sequence differed from expectations")


if __name__ == "__main__":
    main()
