"""Pytest configuration shared across the migration test-suite.

Adds the ``backend`` directory to ``sys.path`` so tests can import the agent
runtime packages with ``import src.agent...`` exactly as ``backend/main.py`` does
(it runs with ``backend`` as the working directory).
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
