"""Check the frozen Packaging helper against fixed behavior examples."""

from itertools import product
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

    if "--expanded" in sys.argv:
        vocabulary = ("none", "abi3", "abi3t", "cp313", "cp313t", "cp316d", "cp316td", "cp316dt", "cp316", "other")
        print(json.dumps([
            _is_threaded_cpython(list(abis))
            for length in range(4) for abis in product(vocabulary, repeat=length)
        ]))
        raise SystemExit

    print(json.dumps([
        {"abis": abis, "expected": expected, "observed": _is_threaded_cpython(list(abis))}
        for abis, expected in CASES
    ]))
