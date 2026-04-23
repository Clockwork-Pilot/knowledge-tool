"""Knowledge Tool - JSON Patch operations and pluggable model rendering."""

import os
import sys
from pathlib import Path

# Setup paths for all imports
_knowledge_tool_root = Path(__file__).parent  # knowledge_tool/ directory

_src_dir = _knowledge_tool_root / "src"

# Add src directory to path so src modules are importable
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Add knowledge_tool root to path for patch_knowledge_document and other scripts
if str(_knowledge_tool_root) not in sys.path:
    sys.path.insert(0, str(_knowledge_tool_root))

# Protected files (knowledge_tool uses this to track protected files)
PROTECTED_REGISTRY_FILENAME = ".protected_files.txt"
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", os.getcwd())).resolve()

# Import models for compatibility with tests
from models import (
    RenderableModel,
    Doc,
    Opts,
    MODEL_REGISTRY,
)

__all__ = [
    "RenderableModel",
    "Doc",
    "Opts",
    "MODEL_REGISTRY",
    "PROTECTED_REGISTRY_FILENAME",
    "PROJECT_ROOT",
]
