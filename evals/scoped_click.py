"""Qualify a structured two-block replacement using the frozen Click grader."""

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from textwrap import dedent, indent
from time import monotonic
from urllib.request import Request, urlopen

from .paired_continuation import CASES, MODEL, calibrate, grade, local_provider_metadata, save, seed
from .run import download, sha


BLOCKS = {
    "command": '        if self.deprecated:\n            text = f"{_(text)} {_format_deprecated_label(self.deprecated)}"',
    "option": ('        if deprecated:\n            label = _format_deprecated_label(deprecated)\n'
               '            help = f"{help} {label}" if help is not None else label'),
}
METHODS = {"command": ("Command", "format_help_text"), "option": ("Option", "__init__")}
NODES = (
    ast.Module, ast.If, ast.Assign, ast.Name, ast.Load, ast.Store, ast.Attribute, ast.Call, ast.IfExp,
    ast.JoinedStr, ast.FormattedValue, ast.Constant, ast.BinOp, ast.Add, ast.Compare, ast.Is, ast.IsNot,
    ast.Eq, ast.NotEq, ast.UnaryOp, ast.Not, ast.BoolOp, ast.And, ast.Or,
)


def replacement(value):
    if not isinstance(value, str) or len(value) > 1500:
        raise ValueError("Expected a short block")
    source = dedent(value).strip()
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.If):
        raise ValueError("Expected one conditional block")
    for node in ast.walk(tree):
        if not isinstance(node, NODES):
            raise ValueError(f"Unsupported edit syntax: {type(node).__name__}")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name)
                                          or node.func.id not in ("_", "_format_deprecated_label")):
            raise ValueError("Unsupported call")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id not in ("text", "label", "help"):
            raise ValueError("Unsupported assignment")
    return indent(source, " " * 8)


def method_region(source, label):
    class_name, method_name = METHODS[label]
    cls = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    return method, source.splitlines(keepends=True)


def apply_blocks(source, packet):
    if not isinstance(packet, dict) or packet.keys() != BLOCKS.keys():
        raise ValueError("Expected exactly both named blocks")
    for label, block in BLOCKS.items():
        method, lines = method_region(source, label)
        first, last = method.lineno - 1, method.end_lineno
        region = "".join(lines[first:last])
        if region.count(block) != 1:
            raise ValueError("Ambiguous source anchor within method")
        updated = region.replace(block, replacement(packet[label]), 1)
        source = "".join(lines[:first]) + updated + "".join(lines[last:])
    ast.parse(source)
    return source


def known_good_blocks(reference):
    packet = {}
    tests = {"command": "self.deprecated", "option": "deprecated"}
    for label, test in tests.items():
        method, lines = method_region(reference, label)
        found = next(node for node in method.body if isinstance(node, ast.If) and ast.unparse(node.test) == test)
        packet[label] = "".join(lines[found.lineno - 1:found.end_lineno])
    return packet


def model_response(endpoint, case, seed_number, *, explicit=False):
    brief = {"objective": case["objective"], "command": dedent(BLOCKS["command"]),
             "option": dedent(BLOCKS["option"])}
    prompt = ("Fix the two Python conditional blocks in this input. The existing local variables, labels and "
              "translation function retain their meaning. Return a JSON object with exactly two string keys "
              "'command' and 'option', each a complete replacement of the corresponding if block.\n"
              + json.dumps(brief))
    if explicit:
        prompt += ("\nBoth blocks are currently wrong. In the command block, text may be empty. "
                   "In the option block, help may be empty or None. In those cases output only the label. "
                   "Do not return an unchanged block.")
    data = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "seed": seed_number, "max_tokens": 512, "stream": False,
            "reasoning_effort": "none", "response_format": {"type": "json_object"}}
    req = Request(endpoint + "/chat/completions", data=json.dumps(data).encode(),
                  headers={"Content-Type": "application/json"})
    started = monotonic()
    with urlopen(req, timeout=180) as response:
        body = json.load(response)
    choice = body["choices"][0]
    content = choice["message"]["content"]
    return content, {"requested_seed": seed_number, "seconds": round(monotonic() - started, 3),
                     "prompt_sha256": sha(prompt.encode()), "output_sha256": sha((content or "").encode()),
                     "finish_reason": choice["finish_reason"], "usage": body.get("usage")}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--endpoint", default="http://127.0.0.1:14687/v1")
    cli.add_argument("--diagnostic", action="store_true")
    args = cli.parse_args()
    case = next(case for case in CASES if case["id"] == "click-help")
    report = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "model": local_provider_metadata(args.endpoint),
              "source_sha256": sha(Path(__file__).read_bytes()), "attempts": []}
    assert replacement("if deprecated:\n    help = label").startswith("        if")
    try:
        replacement("if deprecated:\n    print(help)")
    except ValueError:
        pass
    else:
        raise AssertionError("The guard admitted an unrelated call")
    with tempfile.TemporaryDirectory(prefix="continuity-scoped-click-") as directory:
        root = Path(directory)
        expected, report["calibration"] = calibrate(case, root / "control")
        reference = (root / "control" / "control" / case["source"][0]).read_text()
        schedule = ((31, False), (31, True)) if args.diagnostic else ((31, False), (32, False))
        for index, (seed_number, explicit) in enumerate(schedule):
            workspace = download(case, root / str(index), reference=False)
            seed(case, workspace)
            path = workspace / case["source"][0]
            original = path.read_text()
            assert apply_blocks(original, known_good_blocks(reference)) == reference
            report["upstream_edit_guard_control"] = True
            content, trial = model_response(args.endpoint, case, seed_number, explicit=explicit)
            trial["explicit_prompt"] = explicit
            try:
                candidate = apply_blocks(original, json.loads(content))
            except (ValueError, SyntaxError, TypeError) as error:
                trial.update(applied=False, disposition=type(error).__name__, detail=str(error))
            else:
                path.write_text(candidate)
                trial.update(applied=candidate != original, disposition="validated")
            trial["grade"] = grade(case, workspace, expected)
            report["attempts"].append(trial)
            save(args.output, report)


if __name__ == "__main__":
    main()
