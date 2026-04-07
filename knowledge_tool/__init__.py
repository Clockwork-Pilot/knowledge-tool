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

# Configuration - single source of truth
PROTECTED_REGISTRY_FILENAME = ".protected_files.txt"  # Customizable in this module
PROTECTED_REGISTRY_DIR = Path(
    os.getenv(
        "PROTECTED_REGISTRY_DIR",
        str(_knowledge_tool_root.parent)  # parent of knowledge_tool/
    )
)

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
    "PROTECTED_REGISTRY_DIR",
]
