from pathlib import Path
import sys

sys.path.insert(0, str(Path("src").resolve()))
from packaging.markers import InvalidMarker, Marker

original = Marker("""platform_release == 'version "preview"'""")
try:
    actual = Marker(str(original))
except InvalidMarker as error:
    raise AssertionError("Serialized marker could not be parsed") from error
assert actual == original
