"""Validate hidden probes against deliberately incomplete historical repairs."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from .paired_continuation import CASES, calibrate, native, oracle, repro, seed
from .run import download, sha


REPAIRS = {
    "click-help": (
        "src/click/core.py",
        'help = f"{help} {label}" if help is not None else label',
        'help = f"{help} {label}" if help else label',
    ),
    "packaging-quotes": (
        "src/packaging/_parser.py",
        """class Value(Node):
    __slots__ = ()

    def serialize(self) -> str:
        return f'"{self}"'
""",
        """class Value(Node):
    __slots__ = ()

    def serialize(self) -> str:
        value = str(self)
        if '"' in value:
            return f"'{value}'"
        return f'"{value}"'
""",
    ),
    "attrs-converter": (
        "src/attr/setters.py",
        """    c = attrib.converter
    if c:
        return c(new_value)
""",
        """    c = attrib.converter
    if c:
        from ._make import Converter

        if isinstance(c, Converter) and c.takes_self and c.takes_field:
            return c.converter(new_value, instance, attrib)
        return c(new_value)
""",
    ),
}


def control(case, root):
    expected, calibration = calibrate(case, root)
    partial = download(case, root / "partial", reference=False)
    seed(case, partial)
    path, old, new = REPAIRS[case["id"]]
    file = partial / path
    before = file.read_text()
    assert before.count(old) == 1
    file.write_text(before.replace(old, new, 1))
    visible = repro(partial)
    observed, exit_code = oracle(case, partial)
    assert exit_code == 0 and expected.keys() == observed.keys()
    missed = [key for key, value in expected.items() if observed[key] != value]
    tests = native(case, partial)
    assert visible["exit"] == 0 and missed, (visible, missed)
    return {"id": case["id"], "visible": visible, "native": tests, "changed_file": path,
            "changed_sha256": sha(file.read_bytes()), "hidden_count": len(expected),
            "hidden_disagreements": len(missed), "first_disagreements": missed[:8],
            "reference_hidden_sha256": calibration["reference_hidden_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-paired-control-") as directory:
        records = [control(case, Path(directory) / case["id"]) for case in CASES]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_sha256": sha(Path(__file__).read_bytes()), "cases": records,
    }, indent=2) + "\n")
