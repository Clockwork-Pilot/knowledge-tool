#!/usr/bin/env python3
"""Load models dynamically from external folders based on configuration."""

import sys
import os
import yaml
import importlib.util
from pathlib import Path
from typing import Dict, Optional, Type, List
from knowledge_tool.models import MODEL_REGISTRY, RenderableModel


def load_external_models(external_models_path: str) -> Dict[str, Type[RenderableModel]]:
    """
    Load model classes from external models folder.

    The folder should contain Python files with classes that inherit from RenderableModel.
    Each file should define one model class with a matching class name.

    Args:
        external_models_path: Path to folder containing external model definitions

    Returns:
        Dictionary mapping model type names to model classes

    Raises:
        ValueError: If path doesn't exist or contains invalid models
    """
    models_path = Path(external_models_path)

    if not models_path.exists():
        raise ValueError(f"External models path not found: {external_models_path}")

    if not models_path.is_dir():
        raise ValueError(f"External models path is not a directory: {external_models_path}")

    # Ensure project root is in sys.path so external models can import from models
    project_root = models_path.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    external_models = {}

    # Load all .py files except __init__.py and __pycache__
    for py_file in sorted(models_path.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        try:
            # Load module dynamically with a namespaced name to avoid conflicts
            module_name = f"_external_model_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Find RenderableModel subclasses in the module
                for name in dir(module):
                    obj = getattr(module, name)
                    # Check if it's a class, not the base class, and is a RenderableModel
                    if (isinstance(obj, type) and
                        issubclass(obj, RenderableModel) and
                        obj is not RenderableModel):
                        # Use the model's type field as the registry key
                        # Try to instantiate a dummy instance to get the type
                        try:
                            # Get type from model definition (typically a Literal)
                            if hasattr(obj, "model_fields") and "type" in obj.model_fields:
                                # For Pydantic models with Literal type
                                type_field = obj.model_fields["type"]
                                if hasattr(type_field, "annotation"):
                                    # Extract the literal value if it's a Literal type
                                    import typing
                                    if hasattr(typing, "get_args"):
                                        args = typing.get_args(type_field.annotation)
                                        if args:
                                            model_type = args[0]
                                        else:
                                            model_type = name
                                    else:
                                        model_type = name
                                else:
                                    model_type = name
                            else:
                                model_type = name

                            external_models[model_type] = obj
                        except Exception:
                            # Fallback: use class name as type
                            external_models[name] = obj

        except Exception as e:
            raise ValueError(f"Failed to load model from {py_file}: {str(e)}")

    if not external_models:
        raise ValueError(f"No valid models found in {external_models_path}")

    return external_models


def load_config() -> tuple[Dict, Path]:
    """
    Load knowledge tool configuration from knowledge_config.yaml.

    Resolution order:
    1. KNOWLEDGE_TOOL_CONFIG_ROOT environment variable (if set)
    2. CLAUDE_PLUGIN_ROOT environment variable (if set)
    3. CLAUDE_PROJECT_ROOT environment variable (if set)
    4. Same directory as apply_json_patch.py script
    5. Default empty config if file not found (no extra models)

    Returns:
        Tuple of (config dict, config file path)
    """
    config_filename = "knowledge_config.yaml"
    config_path = None

    # 1. Check KNOWLEDGE_TOOL_CONFIG_ROOT override
    if config_root := os.getenv('KNOWLEDGE_TOOL_CONFIG_ROOT'):
        config_path = Path(config_root) / config_filename
    # 2. Check CLAUDE_PLUGIN_ROOT (when used as plugin)
    elif claude_plugin_root := os.getenv('CLAUDE_PLUGIN_ROOT'):
        config_path = Path(claude_plugin_root) / config_filename
    # 3. Check CLAUDE_PROJECT_ROOT (when used in project)
    elif claude_project_root := os.getenv('CLAUDE_PROJECT_ROOT'):
        config_path = Path(claude_project_root) / config_filename
    else:
        # 4. Look in same directory as this module (apply_json_patch location)
        script_dir = Path(__file__).parent.parent
        config_path = script_dir / config_filename

    # Load config if exists
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
                return config, config_path
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}", file=sys.stderr)
            return {}, config_path

    # No config found - return empty config (will use only built-in models)
    return {}, config_path if config_path else Path("knowledge_config.yaml")


def resolve_pluggable_models_dirs(external_models_path: Optional[str] = None) -> List[Path]:
    """
    Resolve pluggable model directories from config and environment.

    Paths in knowledge_config.yaml are resolved relative to the config file location.

    Priority:
    1. pluggable_models_dirs from knowledge_config.yaml
    2. Empty list (only built-in models)

    Args:
        external_models_path: Deprecated. Use knowledge_config.yaml instead.

    Returns:
        List of Path objects to search for models
    """
    if external_models_path:
        # Explicit path takes priority (for backwards compatibility)
        return [Path(external_models_path)]

    # Load from config and get config file location
    config, config_path = load_config()
    dirs = config.get('pluggable_models_dirs', []) or []

    # Resolve relative paths from config file location
    config_root = config_path.parent
    resolved_dirs = []

    for dir_path in dirs:
        path = Path(dir_path)
        # Make absolute if relative (relative to config file location)
        if not path.is_absolute():
            path = config_root / path
        resolved_dirs.append(path)

    return resolved_dirs


def get_model_registry(external_models_path: Optional[str] = None) -> Dict[str, Type[RenderableModel]]:
    """
    Get combined model registry with built-in and pluggable models.

    Built-in models are always included. External models are loaded from:
    - pluggable_models_dirs specified in knowledge_config.yaml

    Args:
        external_models_path: Optional explicit path to external models folder

    Returns:
        Dictionary mapping model type names to model classes
    """
    # Start with default registry (built-in models always included)
    registry = MODEL_REGISTRY.copy()

    # Resolve pluggable model directories
    model_dirs = resolve_pluggable_models_dirs(external_models_path)

    # Load and merge external models from all configured directories
    for dir_path in model_dirs:
        if dir_path.exists():
            try:
                external = load_external_models(str(dir_path))
                registry.update(external)
            except ValueError as e:
                # Directory exists but has no valid models, skip it
                pass
        else:
            print(f"Warning: Pluggable models directory not found: {dir_path}", file=sys.stderr)

    return registry
