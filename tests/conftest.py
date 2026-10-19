"""Pytest path setup: allow `from models... import ...` imports."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
