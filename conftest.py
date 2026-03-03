"""Pytest configuration - ensures project root is in sys.path and centralizes __pycache__."""

import sys
import os
from pathlib import Path

# Set PYTHONPYCACHEPREFIX BEFORE any imports (except sys, os, pathlib)
project_root = Path(__file__).parent
cache_prefix = str(project_root / ".cache" / "pycache")
os.environ["PYTHONPYCACHEPREFIX"] = cache_prefix

# Ensure .cache directory exists
(project_root / ".cache").mkdir(exist_ok=True)

# Add project root to path so imports work correctly
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
