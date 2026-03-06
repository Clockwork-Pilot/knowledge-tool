"""Knowledge Tool - JSON Patch operations and pluggable model rendering."""

import sys
from pathlib import Path

from .models import (
    RenderableModel,
    Doc,
    Opts,
    MODEL_REGISTRY,
)

# Import apply_json_patch from parent directory
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
from apply_json_patch import apply_json_patch

from .knowledge_files_registry import add_knowledge_files

__all__ = [
    "apply_json_patch",
    "add_knowledge_files",
    "RenderableModel",
    "Doc",
    "Opts",
    "MODEL_REGISTRY",
]
