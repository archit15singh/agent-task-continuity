"""Check that frozen probes accept alternate implementations of the reference behavior."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from .paired_continuation import CASES, calibrate, native, oracle, packet_digest, repro
from .run import sha

ALTERNATES = {
    "click-help": (0,
        '            text = f"{_(text)} {label}" if text else label\n',
        '            if text:\n                text = " ".join((_(text), label))\n'
        '            else:\n                text = label\n',
    ),
    "packaging-quotes": (0,
        '''        if '"' not in value:
            return f'"{value}"'
        if "'" not in value:
            return f"'{value}'"
        raise ValueError(
            "Cannot serialize marker value containing both quote characters"
        )
''',
        '''        delimiter = '"'
        if delimiter in value:
            delimiter = "'"
            if delimiter in value:
                raise ValueError(
                    "Cannot serialize marker value containing both quote characters"
                )
        return delimiter + value + delimiter
''',
    ),
    "attrs-converter": (0,
        '''        self.__call__ = {
            (False, False): self._takes_only_value,
            (True, False): self._takes_instance,
            (False, True): self._takes_field,
            (True, True): self._takes_both,
        }[self.takes_self, self.takes_field]
''',
        '''        if self.takes_self and self.takes_field:
            self.__call__ = self._takes_both
        elif self.takes_self:
            self.__call__ = self._takes_instance
        elif self.takes_field:
            self.__call__ = self._takes_field
        else:
            self.__call__ = self._takes_only_value
''',
    ),
}


def control(case, root):
    expected, calibration = calibrate(case, root)
    workspace = root / "control"
    index, original, alternate = ALTERNATES[case["id"]]
    path = case["source"][index]
    source = workspace / path
    contents = source.read_text()
    assert contents.count(original) == 1
    source.write_text(contents.replace(original, alternate, 1))
    observed, exit_code = oracle(case, workspace)
    reproduction, tests = repro(workspace), native(case, workspace)
    assert exit_code == 0 and observed == expected
    assert reproduction["exit"] == 0 and all(row["exit"] == 0 for row in tests.values())
    return {"id": case["id"], "modified_file": path, "modified_sha256": sha(source.read_bytes()),
            "hidden_count": len(expected), "reproduction": reproduction, "native": tests,
            "reference_hidden_sha256": calibration["reference_hidden_sha256"],
            "alternate_hidden_sha256": packet_digest(observed)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-paired-alternate-") as directory:
        root = Path(directory)
        cases = [control(case, root / case["id"]) for case in CASES]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_sha256": sha(Path(__file__).read_bytes()), "cases": cases,
    }, indent=2) + "\n")
