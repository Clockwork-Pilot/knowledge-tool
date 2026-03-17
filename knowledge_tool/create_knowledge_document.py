#!/usr/bin/env python3
"""Create a new knowledge document of a specified model type.

Creates a JSON document of the given model type at the specified path.
Supports both built-in models and pluggable custom models configured in knowledge_config.yaml.
"""

import json
import sys
from pathlib import Path

# Auto-setup: Add src directory to path (handles direct execution or package import)
_pkg_dir = Path(__file__).parent
_src_dir = _pkg_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Now we can import from src modules
from common.model_loader import get_model_registry


def _is_creatable_model(model_type: str, model_class) -> bool:
    """Predicate: check if model can be created as a root document.

    Args:
        model_type: The model type name
        model_class: The model class to check

    Returns:
        True if model can be created as root document, False otherwise
    """
    try:
        instance = model_class.create_default()
        return instance.is_can_be_root()
    except Exception:
        return False


def create_knowledge_document(model_type: str, document_path: str) -> int:
    """Create a new knowledge document of the specified type.

    Args:
        model_type: Name of the model type to create
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
    if not _is_creatable_model(model_type, model_class):
        print(f"✗ Model type cannot be created as root document: {model_type}")
        return 1

    # Create document instance
    try:
        document = model_class.create_default()

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
            '  python3 create_knowledge_document.py Task task-iterations.k.json',
            file=sys.stderr,
        )
        sys.exit(1)

    model_type = sys.argv[1]
    document_path = sys.argv[2]

    exit_code = create_knowledge_document(model_type, document_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
