"""Check documented thinking controls on one local alias across three endpoints."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from time import monotonic
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from . import paired_continuation, provider_trace
from .paired_continuation import CASES, MODEL, attempt as run_worker, calibrate, local_provider_metadata, warm_provider
from .run import sha

PROMPT = "Calculate 6 multiplied by 7. Return exactly the number, with no other text."
CAP = 32


def post(root, path, packet):
    req = Request(root + path, data=json.dumps(packet).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=40) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, {}


def attempt(root, route, off):
    messages = [{"role": "user", "content": PROMPT}]
    body = {"model": MODEL, "stream": False}
    if route == "/api/chat":
        body.update(messages=messages, options={"temperature": 0, "num_predict": CAP})
        if off:
            body["think"] = False
    elif route == "/v1/chat/completions":
        body.update(messages=messages, temperature=0, max_tokens=CAP)
        if off:
            body["reasoning_effort"] = "none"
    else:
        body.update(input=PROMPT, temperature=0, max_output_tokens=CAP)
        if off:
            body["reasoning"] = {"effort": "none"}

    started = monotonic()
    status, data = post(root, route, body)
    row = {"path": route, "off_requested": off, "http": status, "seconds": round(monotonic() - started, 4)}
    if status != 200:
        return row
    if route == "/v1/responses":
        items = data["output"]
        text = "".join(part.get("text", "") for item in items if item["type"] == "message"
                       for part in item["content"] if part["type"] == "output_text")
        thinking = "".join(part.get("text", "") for item in items if item["type"] == "reasoning"
                           for part in item.get("summary") or [])
        usage = data.get("usage") or {}
        tokens = usage.get("output_tokens")
        details = usage.get("output_tokens_details") or {}
        row.update(reasoning_items=sum(item["type"] == "reasoning" for item in items),
                   reasoning_tokens=details.get("reasoning_tokens"), end=data.get("status"))
    else:
        container = data if route == "/api/chat" else data["choices"][0]
        message = container["message"]
        text = message.get("content") or ""
        thinking = message.get("thinking") or message.get("reasoning") or message.get("reasoning_content") or ""
        tokens = data.get("eval_count") if route == "/api/chat" else data["usage"]["completion_tokens"]
        row["end"] = container.get("done_reason") or container.get("finish_reason")
    return {**row, "visible_characters": len(text), "reasoning_characters": len(thinking),
            "literal_think_tag": "<think>" in text or "</think>" in text,
            "exact_answer": text.strip() == "42", "output_tokens": tokens}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:14687/v1")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--click-output", type=Path)
    parser.add_argument("--codex-click-output", type=Path)
    args = parser.parse_args()
    model = local_provider_metadata(args.endpoint)
    root = args.endpoint.removesuffix("/v1")
    status, info = post(root, "/api/show", {"model": MODEL})
    assert status == 200
    warm_provider(args.endpoint)
    routes = ("/api/chat", "/v1/chat/completions", "/v1/responses")
    rows = [attempt(root, route, off=off) for route in routes for off in (False, True)]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runner_sha256": sha(Path(__file__).read_bytes()), "model": model, "thinking": info.get("thinking"),
        "prompt": PROMPT, "cap": CAP, "trials": rows,
    }, indent=2) + "\n")
    for runtime, route, output in (
        ("opencode", "/v1/chat/completions", args.click_output),
        ("codex", "/v1/responses", args.codex_click_output),
    ):
        if output is not None:
            off = next(row for row in rows if row["path"] == route and row["off_requested"])
            click_followup(args.endpoint, model, runtime, off, output)


def click_followup(endpoint, model, runtime, smoke, output):
    qualified = (smoke["http"] == 200 and smoke["exact_answer"] and not smoke["reasoning_characters"]
                 and not smoke["literal_think_tag"] and not smoke.get("reasoning_items"))
    followup = {"qualified": qualified, "attempt": None,
                "runner_sha256": sha(Path(__file__).read_bytes()),
                "paired_runner_sha256": sha(Path(paired_continuation.__file__).read_bytes()),
                "relay_sha256": sha(Path(provider_trace.__file__).read_bytes()), "model": model}
    output.write_text(json.dumps(followup, indent=2) + "\n")
    if not qualified:
        return
    case = next(item for item in CASES if item["id"] == "click-help")
    with tempfile.TemporaryDirectory(prefix="continuity-paired-off-") as directory:
        root = Path(directory).resolve()
        expected, followup["calibration"] = calibrate(case, root / "controls")
        print(f"Qualified reasoning off: running the matched {runtime} Click follow-up", flush=True)
        followup["attempt"] = run_worker(case, root / runtime, runtime, endpoint, expected,
                                         reasoning_effort="none")
    output.write_text(json.dumps(followup, indent=2) + "\n")


if __name__ == "__main__":
    main()
