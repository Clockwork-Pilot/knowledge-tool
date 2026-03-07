#!/usr/bin/env python3
"""Create a new knowledge document of a specified model type.

Creates a JSON document of the given model type at the specified path.
Supports both built-in models (Doc, Task, Iteration) and pluggable custom models
configured in knowledge_config.yaml.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Auto-setup: Add src directory to path (handles direct execution or package import)
_pkg_dir = Path(__file__).parent
_src_dir = _pkg_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Now we can import from src modules
from models import Doc
from common.model_loader import get_model_registry


def _create_temp_instance(model_class, model_type: str):
    """Create a temporary instance to check model properties.

    Args:
        model_class: The model class to instantiate
        model_type: The model type name

    Returns:
        A temporary instance or None if instantiation fails
    """
    try:
        if model_type == "Task":
            from models import Task
            plan = Doc(id="test", label="Test")
            return Task(id="test", plan=plan)
        elif model_type == "Iteration":
            from models import Iteration
            return Iteration(id="test")
        elif model_type == "Doc":
            return Doc(id="test", label="Test")
        else:
            # Try with minimal fields
            return model_class(
                id="test",
                type=model_type,
            )
    except Exception:
        return None


def _get_creatable_models(registry: dict) -> list:
    """Get list of models that can be created as root documents.

    Args:
        registry: Model registry dictionary

    Returns:
        List of creatable model type names
    """
    creatable = []
    for model_type, model_class in registry.items():
        try:
            instance = _create_temp_instance(model_class, model_type)
            if instance and instance.can_be_root():
                creatable.append(model_type)
        except Exception:
            pass
    return creatable


def create_knowledge_document(model_type: str, document_path: str) -> int:
    """Create a new knowledge document of the specified type.

    Args:
        model_type: Name of the model type (e.g., 'Doc', 'Task', 'Iteration')
        document_path: Path where the document will be created

    Returns:
        0 on success, 1 on error
    """
    doc_file = Path(document_path)

    # Check if document file already exists
    if doc_file.exists():
        print(f"✗ Document already exists: {document_path}")
        return 1

    # Get model registry (uses knowledge_config.yaml or auto-discovery)
    try:
        registry = get_model_registry()
    except Exception as e:
        print(f"✗ Error loading model registry: {e}")
        return 1

    # Check if model type exists
    if model_type not in registry:
        available_models = ", ".join(sorted(registry.keys()))
        print(f"✗ Model type not found: {model_type}")
        print(f"Available models: {available_models}")
        return 1

    # Get the model class
    model_class = registry[model_type]

    # Check if model can be created as root document
    try:
        # Create a temporary instance to check can_be_root()
        # We need to instantiate with minimal required fields
        temp_instance = _create_temp_instance(model_class, model_type)
        if temp_instance and not temp_instance.can_be_root():
            creatable_models = _get_creatable_models(registry)
            print(f"✗ Model type cannot be created as root document: {model_type}")
            print(f"Creatable models: {', '.join(sorted(creatable_models))}")
            return 1
    except Exception as e:
        # If we can't instantiate to check, we'll try to create it anyway
        pass

    # Create document instance based on model type
    try:
        now = datetime.now().isoformat()

        if model_type == "Task":
            # Task requires a plan Doc
            from models import Task
            plan = Doc(
                id="plan",
                label="Task Plan",
                metadata={"created_at": now, "updated_at": now},
            )
            document = Task(
                id="task_1",
                plan=plan,
                iterations=None,
            )
        elif model_type == "Iteration":
            # Iteration is a standalone document
            from models import Iteration
            document = Iteration(
                id="iteration_1",
                metadata={"created_at": now, "updated_at": now},
            )
        elif model_type == "Doc":
            # Doc is the base model
            document = Doc(
                id="doc_1",
                label="Knowledge Document",
                metadata={"created_at": now, "updated_at": now},
            )
        else:
            # For custom models, try to instantiate with basic fields
            # Assume the model has at least 'id' and 'type' fields
            try:
                document = model_class(
                    id=f"{model_type.lower()}_1",
                    type=model_type,
                    metadata={"created_at": now, "updated_at": now},
                )
            except TypeError:
                # If that fails, try with just the required fields
                try:
                    document = model_class(
                        id=f"{model_type.lower()}_1",
                        type=model_type,
                    )
                except TypeError as e:
                    print(f"✗ Error instantiating {model_type}: {e}")
                    return 1

        # Ensure parent directory exists
        doc_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to JSON file
        with open(doc_file, "w") as f:
            json.dump(json.loads(document.model_dump_json()), f, indent=2)

        print(f"✓ Created {model_type} document: {document_path}")
        return 0

    except Exception as e:
        print(f"✗ Error creating document: {e}")
        return 1


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 3:
        print(
            "Usage: python3 create_knowledge_document.py <model_type> <document_path>",
            file=sys.stderr,
        )
        print("\nExamples:", file=sys.stderr)
        print(
            '  python3 create_knowledge_document.py Doc doc.json',
            file=sys.stderr,
        )
        print(
            '  python3 create_knowledge_document.py Task task.json',
            file=sys.stderr,
        )
        print(
            '  python3 create_knowledge_document.py Iteration iteration.json',
            file=sys.stderr,
        )
        sys.exit(1)

    model_type = sys.argv[1]
    document_path = sys.argv[2]

    exit_code = create_knowledge_document(model_type, document_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
