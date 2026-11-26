"""Try one bounded replacement of a known Packaging helper in a frozen worktree."""

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic
import re
import sys
import tempfile
from urllib.request import Request, urlopen

from continuity.workspace import git
from .frozen import CASE, FIXTURE, grade
from .live import NOTE, REPRO, TASKS, replacement_objective
from .provider_trace import trace_provider
from .run import EVALS, download, execute, invoke, sha

FUNCTION = "_is_threaded_cpython"


def target(source):
    (node,) = [node for node in ast.parse(source).body
               if isinstance(node, ast.FunctionDef) and node.name == FUNCTION]
    return node


def section(source):
    node = target(source)
    return "".join(source.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])


def splice(source, code):
    tree = ast.parse(code)
    allowed_nodes = (
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Name, ast.Load, ast.Store,
        ast.Return, ast.If, ast.For, ast.Assign, ast.AnnAssign, ast.NamedExpr, ast.Expr, ast.Constant,
        ast.Call, ast.keyword, ast.Attribute, ast.UnaryOp, ast.Not, ast.BoolOp, ast.Or, ast.And,
        ast.Compare, ast.Eq, ast.NotEq, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Subscript, ast.Slice,
        ast.Tuple, ast.List, ast.Set, ast.IfExp, ast.Break, ast.Continue, ast.Pass,
    )
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("Expected one function")
    original = target(source)
    function = tree.body[0]
    if (function.name != FUNCTION or function.decorator_list or ast.dump(function.args) != ast.dump(original.args)
            or ast.dump(function.returns) != ast.dump(original.returns)):
        raise ValueError("Function signature differs from the frozen helper")
    nodes = tuple(ast.walk(tree))
    if sum(isinstance(node, ast.FunctionDef) for node in nodes) != 1:
        raise ValueError("Nested function is outside the supported edit shape")
    allowed_names = {"abis", "re", "str", "len", "bool", "list"}
    allowed_names.update(node.id for node in nodes if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store))
    for node in nodes:
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"Unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and (node.id not in allowed_names or node.id.startswith("_")):
            raise ValueError("Reference is outside the supported helper inputs")
        if isinstance(node, ast.Attribute) and (
            not isinstance(node.ctx, ast.Load)
            or node.attr not in {"match", "fullmatch", "search", "group", "startswith", "endswith", "isdigit"}
        ):
            raise ValueError("Unsupported attribute access")
        if isinstance(node, ast.Subscript) and not isinstance(node.ctx, ast.Load):
            raise ValueError("Subscript mutation is outside the supported edit shape")
    lines = source.splitlines(keepends=True)
    return "".join(lines[:original.lineno - 1]) + code.rstrip() + "\n" + "".join(lines[original.end_lineno:])


def completion(endpoint, model, prompt, *, effort="none", max_tokens=1500, response_format=None, seed=None):
    started = monotonic()
    with trace_provider(endpoint, reasoning_effort=effort) as (relay, provider_records):
        body = json.dumps({
            "model": model, "messages": [{"role": "user", "content": prompt}], "stream": True,
            "max_tokens": max_tokens,
            **({"response_format": response_format} if response_format is not None else {}),
            **({"seed": seed} if seed is not None else {}),
        }).encode()
        request = Request(relay + "/chat/completions", data=body, headers={"Content-Type": "application/json"})
        chunks = []
        with urlopen(request, timeout=180) as response:
            for line in response:
                if monotonic() - started > 180:
                    raise TimeoutError("Provider exceeded the diagnostic deadline")
                if line.startswith(b"data: {"):
                    event = json.loads(line[6:])
                    for choice in event.get("choices", []):
                        content = choice.get("delta", {}).get("content")
                        if content:
                            chunks.append(content)
    return "".join(chunks), provider_records


def apply_completion(endpoint, model, prompt, source_path, original):
    result = {"prompt_sha256": sha(prompt.encode())}
    try:
        output, records = completion(endpoint, model, prompt)
        result["provider_requests"] = records
        result["output_sha256"] = sha(output.encode())
        match = re.search(r"```(?:python)?\s*\n(.*?)```", output, flags=re.DOTALL)
        candidate = (match[1] if match else output).strip()
        source_path.write_text(splice(original, candidate))
        result["candidate_applied"] = True
    except (SyntaxError, ValueError, OSError) as error:
        result["candidate_applied"] = False
        result["failure_type"] = type(error).__name__
    return result


def behavior(workspace):
    process = execute([sys.executable, str(EVALS / "packaging_behavior.py")], cwd=workspace)
    return json.loads(process.stdout) if process.returncode == 0 else None


def finished(result):
    grade = result["grade"]
    return (
        result["candidate_applied"] and grade["files_restored"]
        and grade["changed_files"] == sorted([REPRO, NOTE, CASE["source"]])
        and all(grade[gate] == 0 for gate in ("predicate_exit", "repro_exit", "native_exit"))
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--endpoint")
    cli.add_argument("--model", default="continuity-qwen3:4b")
    cli.add_argument("--dry-run", action="store_true")
    feedback = cli.add_mutually_exclusive_group()
    feedback.add_argument("--feedback-once", action="store_true")
    feedback.add_argument("--seed-base-feedback", action="store_true")
    args = cli.parse_args()
    measure_behavior = args.feedback_once or args.seed_base_feedback
    if not args.endpoint and not args.dry_run:
        cli.error("a live run requires an endpoint")
    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "base": CASE["base"],
        "model": args.model,
        "mode": "dry_run" if args.dry_run else "live",
        **({"seed": "unchanged_helper"} if args.seed_base_feedback else {}),
    }
    with tempfile.TemporaryDirectory(prefix="continuity-bounded-") as directory:
        temp = Path(directory)
        source = download(CASE, temp / "source", reference=False)
        oracle = download(CASE, temp / "oracle", reference=True)
        git(oracle, "checkout", "--quiet", "--detach", CASE["reference"])
        for name in (NOTE, REPRO):
            (source / name).write_bytes((FIXTURE / name).read_bytes())
        db = temp / "task.db"
        task = invoke(db, "start", source, "--objective", replacement_objective(CASE, True))
        checkpoint = invoke(db, "checkpoint", task["task"], "--include", REPRO, "--include", NOTE,
                            "--note", (FIXTURE / NOTE).read_text().strip(), owner=task["token"])
        workspace = temp / "replacement"
        invoke(db, "continue", task["task"], "--into", workspace, owner=task["token"])
        source_path = workspace / CASE["source"]
        before = source_path.read_text()
        original = section(before)
        report["checkpoint"] = checkpoint["digest"]
        assert splice(before, original) == before
        report["unchanged_control"] = grade(workspace)
        if measure_behavior:
            report["unchanged_behavior"] = behavior(workspace)
            assert any(row["observed"] != row["expected"] for row in report["unchanged_behavior"])
        assert report["unchanged_control"]["predicate_exit"] == report["unchanged_control"]["repro_exit"] == 1
        upstream = section((oracle / CASE["source"]).read_text())
        # Inline the upstream companion regex so the positive control obeys the one-function contract.
        upstream = upstream.replace("_CPYTHON_ABI_RE.match(", r're.match(r"cp\d+(.*)", ')
        source_path.write_text(splice(before, upstream))
        report["upstream_function_control"] = grade(workspace)
        if measure_behavior:
            report["upstream_behavior"] = behavior(workspace)
            assert all(row["observed"] == row["expected"] for row in report["upstream_behavior"])
        assert all(report["upstream_function_control"][gate] == 0
                   for gate in ("predicate_exit", "repro_exit", "native_exit"))
        source_path.write_text(before)
        if not args.dry_run:
            prompt = (
                f"{TASKS['packaging']}\nFrozen note: {(FIXTURE / NOTE).read_text()}\n"
                "Return the complete replacement Python function in one fenced code block. "
                "Keep the same signature. The module already imports re. Use only local variables and "
                "simple string or regex matching.\n\n"
                f"```python\n{original}```\n"
            )
            if args.seed_base_feedback:
                report["candidate_applied"] = False
            else:
                report.update(apply_completion(args.endpoint, args.model, prompt, source_path, before))
            report["grade"] = grade(workspace)
            report["complete"] = finished(report)
            if measure_behavior:
                observed = behavior(workspace)
                report["behavior"] = observed
                failures = [item for item in observed or [] if item["observed"] != item["expected"]]
                report["complete"] = report["complete"] and observed is not None and not failures
                if (report["candidate_applied"] or args.seed_base_feedback) and failures:
                    first = failures[0]
                    revised = (
                        f"{TASKS['packaging']}\nA check of your replacement used {first['abis']!r} "
                        f"and observed {first['observed']!r}; it should return {first['expected']!r}.\n"
                        "Return the corrected complete Python function in one fenced code block. "
                        "The module already imports re. Keep the same signature.\n"
                        f"```python\n{section(source_path.read_text())}```"
                    )
                    repair = apply_completion(args.endpoint, args.model, revised, source_path, before)
                    repair["counterexample"] = first
                    repair["grade"] = grade(workspace)
                    repair["behavior"] = behavior(workspace)
                    repair["complete"] = (
                        finished(repair) and repair["behavior"] is not None
                        and all(item["observed"] == item["expected"] for item in repair["behavior"])
                    )
                    report["feedback"] = repair
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
