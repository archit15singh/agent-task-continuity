"""Compare capped and default read results on the frozen Click task."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from .paired_continuation import CASES, attempt, calibrate, local_provider_metadata, save
from .provider_trace import cap_read_observations
from .run import PROJECT, sha


def check_policy():
    def call(name):
        return {"id": name, "function": {"name": name}}

    messages = [
        {"role": "assistant", "tool_calls": [call("read"), call("grep")]},
        *({"role": "tool", "tool_call_id": name, "content": "a" * 5000} for name in ("read", "grep")),
    ]
    assert cap_read_observations(messages, 4096) == [[5000, 4096]]
    assert messages[1]["content"].startswith("a") and messages[1]["content"].endswith("a")
    assert messages[2]["content"] == "a" * 5000


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--endpoint", default="http://127.0.0.1:14687/v1")
    args = cli.parse_args()
    check_policy()
    case = next(case for case in CASES if case["id"] == "click-help")
    model = local_provider_metadata(args.endpoint)
    report = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": model,
              "source_sha256": {name: sha((PROJECT / name).read_bytes()) for name in
                                ("evals/capped_reads.py", "evals/provider_trace.py", "evals/paired_continuation.py")},
              "policy_control": "passed", "attempts": []}
    with tempfile.TemporaryDirectory(prefix="continuity-capped-reads-") as directory:
        root = Path(directory).resolve()
        expected, report["calibration"] = calibrate(case, root / "control")
        for index, limit in enumerate((None, 4096, 4096, None)):
            print(f"Attempt {index + 1}/4, read cap {limit}", flush=True)
            result = attempt(case, root / str(index), "opencode", args.endpoint, expected,
                             reasoning_effort="none", read_limit=limit)
            report["attempts"].append({"read_limit": limit, **result})
            save(args.output, report)
    for field in ("prompt_sha256", "checkpoint_sha256"):
        assert len({row[field] for row in report["attempts"]}) == 1


if __name__ == "__main__":
    main()
