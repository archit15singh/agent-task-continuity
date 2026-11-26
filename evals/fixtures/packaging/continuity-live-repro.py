from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from packaging.tags import Tag, cpython_tags

for abis in (["none", "cp316t"], ["abi3t"]):
    assert Tag("cp315", "abi3t", "platform") in set(
        cpython_tags((3, 16), abis, ["platform"])
    ), abis
