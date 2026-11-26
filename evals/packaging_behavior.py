"""Check the frozen Packaging helper against fixed behavior examples."""

import json
from pathlib import Path
import sys

CASES = (
    (("none", "cp316t"), True),
    (("abi3t",), True),
    (("cp316", "cp316t"), False),
    (("abi3t", "cp316"), True),
    (("none", "abi3"), False),
    ((), False),
)

if __name__ == "__main__":
    sys.path.insert(0, str(Path.cwd() / "src"))
    from packaging.tags import _is_threaded_cpython

    print(json.dumps([
        {"abis": abis, "expected": expected, "observed": _is_threaded_cpython(list(abis))}
        for abis, expected in CASES
    ]))
