"""Compare bounded whole-function and function-body output contracts."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from textwrap import dedent, indent

from continuity.workspace import git
from .bounded_receiver import CASE, FIXTURE, behavior, completion, finished, grade, section, splice, target
from .live import NOTE, REPRO, TASKS, replacement_objective
from .run import download, invoke, sha


def apply_code(source, code, contract):
    if contract == "body":
        lines = source.splitlines(keepends=True)
        node = target(source)
        signature = "".join(lines[node.lineno - 1:node.body[0].lineno - 1])
        code = signature + indent(dedent(code).strip("\n"), "    ")
    return splice(source, code.strip())


def body_from(code):
    # The pinned helper has a single-line signature. Its docstring is part of the body.
    return dedent(code.split("\n", 1)[1])


def reject_reason(error):
    if isinstance(error, SyntaxError):
        return "python_syntax"
    text = str(error)
    if text == "Expected one function":
        return "function_shape"
    if "signature differs" in text:
        return "signature"
    if text.startswith("Unsupported syntax: "):
        return "unsupported_syntax:" + text.split(": ", 1)[1]
    if text == "Unsupported attribute access":
        return "unsupported_attribute"
    if "supported helper inputs" in text:
        return "unsupported_reference"
    return "edit_scope"


def run_trial(workspace, original, contract, seed, args):
    requirement = {
        "whole": "The code string must contain the entire replacement function with its original signature.",
        "body": "The code string must contain only the function body, without a def line. The receiver attaches the original signature.",
    }[contract]
    prompt = (
        f"{TASKS['packaging']}\nFrozen note: {(FIXTURE / NOTE).read_text()}\n"
        "Return exactly one JSON object with a code string. " + requirement
        + "\nThe module imports re. Use local variables and simple string or regex matching.\n"
        + section(original)
    )
    receipt = {"contract": contract, "seed_requested": seed, "prompt_sha256": sha(prompt.encode())}
    try:
        output, requests = completion(args.endpoint, args.model, prompt,
                                      response_format={"type": "json_object"}, seed=seed)
        receipt.update(output_sha256=sha(output.encode()), provider_requests=requests)
    except OSError as error:
        receipt.update(disposition="provider_error", error_type=type(error).__name__)
        return receipt
    try:
        value = json.loads(output)
    except ValueError:
        receipt["disposition"] = "invalid_json"
        return receipt
    if not isinstance(value, dict) or set(value) != {"code"} or not isinstance(value["code"], str):
        receipt["disposition"] = "invalid_schema"
        return receipt
    try:
        candidate = apply_code(original, value["code"], contract)
    except (SyntaxError, ValueError) as error:
        receipt["disposition"] = reject_reason(error)
        return receipt
    (workspace / CASE["source"]).write_text(candidate)
    receipt.update(candidate_applied=True, disposition="applied", grade=grade(workspace), behavior=behavior(workspace))
    receipt["complete"] = finished(receipt) and receipt["behavior"] is not None and all(
        row["expected"] == row["observed"] for row in receipt["behavior"]
    )
    return receipt


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--endpoint")
    cli.add_argument("--model", default="continuity-coder:7b")
    cli.add_argument("--dry-run", action="store_true")
    args = cli.parse_args()
    if not args.endpoint and not args.dry_run:
        cli.error("live runs require --endpoint")
    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": args.model, "base": CASE["base"],
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()), "trials": [],
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    with tempfile.TemporaryDirectory(prefix="continuity-contract-") as directory:
        temp = Path(directory)
        source = download(CASE, temp / "base", reference=False)
        oracle = download(CASE, temp / "oracle", reference=True)
        git(oracle, "checkout", "--quiet", "--detach", CASE["reference"])
        for name in (NOTE, REPRO):
            (source / name).write_bytes((FIXTURE / name).read_bytes())
        original = (source / CASE["source"]).read_text()
        upstream = section((oracle / CASE["source"]).read_text()).replace(
            "_CPYTHON_ABI_RE.match(", r're.match(r"cp\d+(.*)", ',
        )
        orders = (("whole", 31), ("body", 31), ("body", 32), ("whole", 32))
        for index, (contract, seed) in enumerate(orders, 1):
            db = temp / f"task-{index}.db"
            task = invoke(db, "start", source, "--objective", replacement_objective(CASE, True))
            checkpoint = invoke(db, "checkpoint", task["task"], "--include", REPRO, "--include", NOTE,
                                "--note", (FIXTURE / NOTE).read_text().strip(), owner=task["token"])
            workspace = temp / f"case-{index}"
            invoke(db, "continue", task["task"], "--into", workspace, owner=task["token"])
            path = workspace / CASE["source"]
            if index < 3:
                negative = grade(workspace)
                assert negative["predicate_exit"] == negative["repro_exit"] == 1
                try:
                    apply_code(original, upstream.replace("abis: list[str]", "abis"), "whole")
                except ValueError as error:
                    assert reject_reason(error) == "signature"
                else:
                    raise AssertionError("Wrong signature was accepted")
                path.write_text(apply_code(original, upstream if contract == "whole" else body_from(upstream), contract))
                positive = grade(workspace)
                assert all(positive[gate] == 0 for gate in ("predicate_exit", "repro_exit", "native_exit"))
                assert all(row["expected"] == row["observed"] for row in behavior(workspace))
                report.setdefault("controls", {})[contract] = {
                    "wrong_signature_rejected": True, "positive": positive, "baseline_rejected": True,
                }
                path.write_text(original)
            if not args.dry_run:
                receipt = run_trial(workspace, original, contract, seed, args)
                receipt.setdefault("grade", grade(workspace))
                report["trials"].append({"checkpoint": checkpoint["digest"], **receipt})
                save()
        save()


if __name__ == "__main__":
    main()
