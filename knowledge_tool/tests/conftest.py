"""Pytest configuration - handles knowledge_tool package imports.

This conftest sets up the knowledge_tool package for testing by:
1. Making src/ directly importable as knowledge_tool
2. Making test_models directly importable for test-only models
"""
import sys
from pathlib import Path
import importlib.util

# Add src as a top-level module named knowledge_tool
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Create a knowledge_tool module alias that points to src
spec = importlib.util.spec_from_file_location(
    "knowledge_tool",
    str(src_dir / "__init__.py"),
    submodule_search_locations=[str(src_dir)]
)
knowledge_tool_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_tool"] = knowledge_tool_module
spec.loader.exec_module(knowledge_tool_module)

# Add test_models directory to sys.path for direct imports
test_models_dir = Path(__file__).parent / "test_models"
if str(test_models_dir) not in sys.path:
    sys.path.insert(0, str(test_models_dir))
