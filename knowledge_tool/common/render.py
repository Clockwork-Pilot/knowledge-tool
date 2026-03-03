#!/usr/bin/env python3
"""Generic render entry point for all model types.

Works with any model type (Doc, Task, etc.) by reading the JSON file,
determining the model type, and delegating rendering to the model's render() method.
Handles file I/O separately from model logic.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from .file_tools import write_protected_file


def render(document_path: str) -> Optional[str]:
    """Render any model type to markdown and save to .md file.

    Supports Doc, Task, and any future RenderableModel type.

    Args:
        document_path: Path to document JSON file

    Returns:
        Markdown string on success, None on error
    """
    from knowledge_tool.models import MODEL_REGISTRY

    doc_path = Path(document_path)

    if not doc_path.exists():
        print(f"Error: Document not found: {document_path}", file=sys.stderr)
        return None

    try:
        doc_content = doc_path.read_text(encoding="utf-8")
        doc_dict = json.loads(doc_content)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading document: {str(e)}", file=sys.stderr)
        return None

    # Get model type and instantiate correct class
    model_type = doc_dict.get("type", "Doc")
    ModelClass = MODEL_REGISTRY.get(model_type)

    if not ModelClass:
        print(f"Error: Unknown model type: {model_type}", file=sys.stderr)
        return None

    try:
        # Instantiate model - Pydantic validates against its schema
        model_instance = ModelClass(**doc_dict)
    except Exception as e:
        print(f"Error validating {model_type}: {str(e)}", file=sys.stderr)
        return None

    # Render to markdown and save to .md file
    try:
        markdown = model_instance.render()
        md_path = doc_path.with_suffix(".md")
        write_protected_file(md_path, markdown)
        return markdown
    except Exception as e:
        print(f"Error rendering document: {str(e)}", file=sys.stderr)
        return None
