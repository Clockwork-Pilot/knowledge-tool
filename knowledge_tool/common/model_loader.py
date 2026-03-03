#!/usr/bin/env python3
"""Load models dynamically from external folders."""

import sys
import importlib.util
from pathlib import Path
from typing import Dict, Optional, Type
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


def get_model_registry(external_models_path: Optional[str] = None) -> Dict[str, Type[RenderableModel]]:
    """
    Get combined model registry with optional external models.

    Args:
        external_models_path: Optional path to external models folder

    Returns:
        Dictionary mapping model type names to model classes
    """
    # Start with default registry
    registry = MODEL_REGISTRY.copy()

    # Load and merge external models if path provided
    if external_models_path:
        external = load_external_models(external_models_path)
        registry.update(external)

    return registry
