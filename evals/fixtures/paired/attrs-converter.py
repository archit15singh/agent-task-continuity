from pathlib import Path
import sys

sys.path.insert(0, str(Path("src").resolve()))
import attrs


@attrs.define
class Counter:
    count = attrs.field(converter=[int])


counter = Counter("1")
try:
    counter.count = "4"
except (AttributeError, TypeError) as error:
    raise AssertionError("A list converter should also run on assignment") from error
assert counter.count == 4
