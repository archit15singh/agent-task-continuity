"""Record the completion boundary of local model calls without saving prompts."""

from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from time import monotonic
from urllib.parse import urlsplit


@contextmanager
def trace_provider(endpoint, *, reasoning_effort=None):
    backend = urlsplit(endpoint)
    if backend.scheme != "http" or backend.hostname != "127.0.0.1" or backend.path != "/v1":
        raise ValueError("Expected an HTTP loopback provider ending in /v1")
    records = []
    started = monotonic()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path not in ("/v1/chat/completions", "/v1/responses"):
                self.send_error(404)
                return
            payload = self.rfile.read(int(self.headers["Content-Length"]))
            body = json.loads(payload)
            if reasoning_effort is not None:
                if self.path == "/v1/chat/completions":
                    body["reasoning_effort"] = reasoning_effort
                else:
                    body["reasoning"] = {**(body.get("reasoning") or {}), "effort": reasoning_effort}
                payload = json.dumps(body).encode()
            messages = body.get("messages", [])
            compact = "you must summarize the conversation above" in json.dumps(messages).lower()
            record = {
                "path": self.path,
                "request_at_seconds": round(monotonic() - started, 3),
                "compaction_summary": compact,
                "messages": len(messages),
                "tool_count": len(body.get("tools") or []),
                "reasoning_effort": body.get("reasoning_effort", (body.get("reasoning") or {}).get("effort")),
                **({"seed_forwarded": body["seed"]} if "seed" in body else {}),
                "reasoning_characters": 0,
                "visible_characters": 0,
                "requested_max_tokens": body.get("max_tokens", body.get("max_output_tokens")),
            }
            records.append(record)
            connection = HTTPConnection(backend.hostname, backend.port, timeout=240)
            try:
                connection.request("POST", self.path, payload, {"Content-Type": "application/json"})
                response = connection.getresponse()
                record["http_status"] = response.status
                self.send_response(response.status)
                self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
                self.end_headers()
                while line := response.readline():
                    if line.startswith(b"data: {"):
                        event = json.loads(line[6:])
                        for choice in event.get("choices", []):
                            delta = choice.get("delta") or {}
                            record["reasoning_characters"] += len(delta.get("reasoning") or delta.get("reasoning_content") or "")
                            record["visible_characters"] += len(delta.get("content") or "")
                            if choice.get("finish_reason"):
                                record["finish_reason"] = choice["finish_reason"]
                        if event.get("type") in ("response.completed", "response.incomplete", "response.failed"):
                            record["response_event"] = event["type"]
                        usage = event.get("usage") or (event.get("response") or {}).get("usage")
                        if usage:
                            record["usage"] = {key: value for key, value in usage.items() if type(value) is int}
                    self.wfile.write(line)
                    self.wfile.flush()
                record["ended"] = "provider_eof"
            except (BrokenPipeError, ConnectionResetError):
                record["ended"] = "downstream_closed"
            except (OSError, ValueError) as error:
                record["ended"] = type(error).__name__
            finally:
                record["duration_seconds"] = round(monotonic() - started - record["request_at_seconds"], 3)
                connection.close()

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1", records
        finally:
            server.shutdown()
            thread.join()
