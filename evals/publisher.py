"""Loopback reference provider with a one-shot lost-acknowledgment fault."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import socket
import threading


class Publisher:
    def __init__(self, *, drop_first=False, after_accept=None, before_apply=None, generation_fence=False):
        self.drop_first = drop_first
        self.after_accept = after_accept
        self.before_apply = before_apply
        self.generation_fence = generation_fence
        self.generations = {}
        self.stale_rejections = 0
        self.events = {}
        self.puts = 0
        self.gets = 0
        self.lock = threading.Lock()

    def advance_generation(self, task, generation):
        with self.lock:
            if generation <= self.generations.get(task, 0):
                raise ValueError("Receiver generation must advance")
            self.generations[task] = generation

    def handler(self):
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, status, data=None):
                body = json.dumps(data).encode() if data is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # A client can die after handing off a complete request.

            def operation(self):
                match = re.fullmatch(r"/events/([0-9a-f]{64})", self.path)
                return match[1] if match else None

            def do_GET(self):
                operation = self.operation()
                with provider.lock:
                    provider.gets += 1
                    event = provider.events.get(operation)
                self.reply(404) if event is None else self.reply(200, event)

            def do_PUT(self):
                operation = self.operation()
                if operation is None or self.headers.get("Idempotency-Key") != operation:
                    self.reply(400)
                    return
                try:
                    length = int(self.headers.get("Content-Length", -1))
                    if not 0 <= length <= 65536:
                        raise ValueError("Invalid request length")
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("Expected an object")
                except ValueError:
                    self.reply(400)
                    return
                if provider.before_apply is not None:
                    provider.before_apply()
                with provider.lock:
                    provider.puts += 1
                    if provider.generation_fence:
                        task = payload.get("task")
                        generation = self.headers.get("X-Continuity-Generation", "")
                        expected = provider.generations.get(task) if isinstance(task, str) else None
                        if expected is None or generation != str(expected):
                            provider.stale_rejections += 1
                            self.reply(412)
                            return
                    prior = provider.events.get(operation)
                    if prior is not None and prior["payload"] != payload:
                        self.reply(409)
                        return
                    event = prior or {"id": operation, "payload": payload}
                    provider.events[operation] = event
                    drop = provider.drop_first and prior is None
                    if drop:
                        provider.drop_first = False
                if provider.after_accept and prior is None:
                    provider.after_accept()
                if drop:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                else:
                    self.reply(200 if prior else 201, event)

        return Handler


@contextmanager
def publisher(*, drop_first=True, after_accept=None, before_apply=None, generation_fence=False):
    app = Publisher(
        drop_first=drop_first, after_accept=after_accept,
        before_apply=before_apply, generation_fence=generation_fence,
    )
    with ThreadingHTTPServer(("127.0.0.1", 0), app.handler()) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        try:
            yield app, f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    import argparse

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--port", type=int, default=8765)
    cli.add_argument("--drop-first", action="store_true")
    args = cli.parse_args()
    instance = Publisher(drop_first=args.drop_first)
    with ThreadingHTTPServer(("127.0.0.1", args.port), instance.handler()) as server:
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
