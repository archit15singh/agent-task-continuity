"""Fixture worker processes for deterministic crash evaluation."""

import os
from pathlib import Path
import signal
import sys


if sys.argv[1] == "crash":
    Path("continuity-late-edit.txt").write_text("Written after checkpoint.\n")
    os.kill(os.getpid(), signal.SIGKILL)
elif sys.argv[1] == "recover":
    assert "Prior worker checkpoint notes" in os.environ["CONTINUITY_PROMPT"]
    assert not Path("continuity-late-edit.txt").exists()
    assert Path("continuity-eval-note.txt").is_file()
    os.execv(sys.executable, [sys.executable, sys.argv[2], sys.argv[3]])
else:
    sys.exit("unknown fixture action")
