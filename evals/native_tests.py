"""Run an upstream test module against source in the evaluated checkout."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))

import pytest  # noqa: E402

sys.exit(pytest.main(["-q", "-o", "addopts=", sys.argv[1]]))
