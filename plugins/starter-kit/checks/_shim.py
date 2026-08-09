"""Re-export the hook helpers so checks and hooks share one implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _shared import repo_root, run  # noqa: E402,F401
