"""Check whether reasoning moves into ordinary content in a short local response."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .bounded_receiver import completion
from .run import sha


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--endpoint", required=True)
    cli.add_argument("--model", default="continuity-qwen3:4b")
    args = cli.parse_args()
    prompt = "Calculate 3+5. Reply with only the number."
    trials = []
    for effort in (None, "none"):
        output, requests = completion(args.endpoint, args.model, prompt, effort=effort, max_tokens=64)
        (receipt,) = requests
        assert receipt["http_status"] == 200 and receipt["reasoning_effort"] == effort, receipt
        trials.append({
            **receipt,
            "literal_think_tag": bool(re.search(r"</?think\s*>", output, flags=re.IGNORECASE)),
            "exact_answer": output.strip() == "8",
        })
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "model": args.model,
        "trials": trials,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
