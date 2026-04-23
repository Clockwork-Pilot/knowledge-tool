#!/usr/bin/env python3
"""Document API - JSON Patch operations with validation and error handling."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from jsonpatch import JsonPatch, JsonPatchException
from pydantic import ValidationError

# Auto-setup: Add parent directory to path so "from knowledge_tool import ..." works
# when this script is run directly (not as a module import)
_pkg_dir = Path(__file__).parent
_parent_dir = _pkg_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Must run before any src imports touch config.py
if 'PROJECT_ROOT' not in os.environ and len(sys.argv) > 1:
    _doc = Path(sys.argv[1]).resolve()
    if _doc.parent.exists():
        os.environ['PROJECT_ROOT'] = str(_doc.parent)

# Now we can import from knowledge_tool package
from knowledge_tool import Doc
from common.response import ApplyPatchErrorResponse
from common.file_tools import write_protected_file
from common.render import render
from common.model_loader import get_model_registry
from knowledge_files_registry import add_knowledge_files


def apply_json_patch(
    document_path: str,
    json_patch: Optional[str] = None
) -> Optional[ApplyPatchErrorResponse]:
    """
    Apply JSON Patch to document file with validation and automatic markdown rendering.

    Automatically creates new documents if a patch is provided. If json_patch is None,
    only re-renders an existing document without patching.

    External/pluggable models are configured via knowledge_config.yaml or KNOWLEDGE_TOOL_CONFIG_ROOT
    environment variable. Built-in models are always available.

    Process:
    1. Read document from file, or start with empty dict if document doesn't exist (when patch is provided)
    2. If json_patch provided:
       a. Parse and validate JSON Patch (RFC 6902)
       b. Apply patch in memory
       c. Validate against Pydantic Doc schema
       d. Write changes with file protection
    3. Render markdown representation to .md file

    Args:
        document_path: Path to document JSON file
        json_patch: JSON Patch operations as JSON string (RFC 6902 format). If None, only re-renders existing document.

    Returns:
        None on success, ApplyPatchErrorResponse on error
    """
    operation = "apply_json_patch"
    doc_path = Path(document_path)

    # 1. Read document or initialize empty
    if not doc_path.exists():
        # If no patch provided, can't re-render a non-existent document
        if json_patch is None:
            return ApplyPatchErrorResponse(
                error=f"Document not found: {document_path}",
                operation=operation,
                hint="Provide a patch to create a new document or ensure the file exists to re-render"
            )
        # Start with empty doc dict for creation (implicit when patch is provided)
        doc_dict = {}
    else:
        try:
            doc_content = doc_path.read_text(encoding="utf-8")
            doc_dict = json.loads(doc_content)
        except (json.JSONDecodeError, IOError) as e:
            return ApplyPatchErrorResponse(
                error=f"Failed to read document: {str(e)}",
                operation=operation
            )

    # If no patch provided, skip patching and go straight to render
    if json_patch is None:
        patched_dict = doc_dict
    else:
        # 2. Parse JSON Patch
        try:
            patch_ops = json.loads(json_patch)
            if not isinstance(patch_ops, list):
                raise ValueError("JSON Patch must be an array of operations")
        except (json.JSONDecodeError, ValueError) as e:
            return _error_json_patch_syntax(str(e), operation)

        # 3. Create JsonPatch object
        try:
            patch = JsonPatch(patch_ops)
        except Exception as e:
            return _error_json_patch_syntax(str(e), operation)

        # 4. Apply patch in memory
        try:
            patched_dict = patch.apply(doc_dict)
        except Exception as e:
            return _error_path_not_found(str(e), doc_dict, operation)

    # 5. Validate against correct model type
    try:
        model_type = patched_dict.get("type", "Doc")
        model_registry = get_model_registry()
        ModelClass = model_registry.get(model_type)

        if not ModelClass:
            return ApplyPatchErrorResponse(
                error=f"Unknown model type: {model_type}",
                operation=operation
            )

        validated_model = ModelClass.model_validate(patched_dict, context={'original_doc': doc_dict})
        patched_dict = json.loads(validated_model.model_dump_json(exclude_none=True))

        # Check for tips from the model
        model_tips = validated_model.tips()
        if model_tips:
            for tip in model_tips:
                print(tip)

    except ValidationError as e:
        return _error_pydantic_validation(e, operation)
    except Exception as e:
        return ApplyPatchErrorResponse(
            error=f"Failed to validate document: {str(e)}",
            operation=operation
        )

    # 6. Write to file with protection
    try:
        write_protected_file(doc_path, json.dumps(patched_dict, indent=2))
    except Exception as e:
        return ApplyPatchErrorResponse(
            error=f"Failed to write document: {str(e)}",
            operation=operation
        )

    # 7. Render markdown representation
    try:
        render(str(doc_path))
    except Exception as e:
        # Rendering failure doesn't fail the patch operation
        # JSON was updated successfully, but warn the user
        print(f"⚠️  Warning: Failed to render markdown: {str(e)}", file=sys.stderr)

    # 8. Register JSON and MD files in knowledge files registry
    md_path = doc_path.with_suffix(".md")
    try:
        add_knowledge_files([str(doc_path), str(md_path)])
    except Exception as e:
        # Registration failure doesn't fail the patch operation
        print(f"⚠️  Warning: Failed to register knowledge files: {str(e)}", file=sys.stderr)

    return None


def _error_json_patch_syntax(error: str, operation: str) -> ApplyPatchErrorResponse:
    """Return error for JSON Patch syntax errors with example and document schema."""
    schema = Doc.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    hint = (
        "JSON Patch must be valid JSON array of RFC 6902 operations.\n\n"
        "Document schema:\n"
        f"{schema_str}"
    )

    return ApplyPatchErrorResponse(
        error=f"Invalid JSON Patch syntax: {error}",
        hint=hint,
        example=[
            {
                "op": "add",
                "path": "/children/new_id",
                "value": {
                    "id": "new_id",
                    "label": "New Node",
                    "type": "Doc",
                    "metadata": {}
                }
            },
            {
                "op": "replace",
                "path": "/label",
                "value": "Updated Label"
            },
            {
                "op": "remove",
                "path": "/children/old_id"
            }
        ],
        operation=operation
    )


def _error_path_not_found(error: str, doc_dict: Dict, operation: str) -> ApplyPatchErrorResponse:
    """Return error for path not found with parent suggestions."""
    error_str = str(error)

    # Try to extract path from error message
    parent_path = None
    existing_children = []

    if "path" in error_str.lower():
        # Try common error patterns
        if "does not exist" in error_str:
            parts = error_str.split("'")
            if len(parts) >= 2:
                failed_path = parts[1]
                # Get parent path
                if "/" in failed_path:
                    parent_path = "/".join(failed_path.split("/")[:-1])
                    # Get existing children at parent
                    try:
                        parent_obj = _get_path_value(doc_dict, parent_path)
                        if isinstance(parent_obj, dict):
                            existing_children = list(parent_obj.keys())
                    except (KeyError, ValueError):
                        pass

    return ApplyPatchErrorResponse(
        error=f"Path not found: {error}",
        hint="Check parent path and available children",
        parent_path=parent_path,
        existing_children=existing_children if existing_children else None,
        operation=operation
    )


def _error_pydantic_validation(validation_error: ValidationError, operation: str) -> ApplyPatchErrorResponse:
    """Return error for Pydantic validation with schema."""
    schema = Doc.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    hint = (
        "Expected Pydantic schema:\n"
        f"{schema_str}"
    )

    return ApplyPatchErrorResponse(
        error=f"Document validation failed: {validation_error.error_count()} error(s)",
        hint=hint,
        details=json.loads(json.dumps(validation_error.errors(), default=str)),
        operation=operation
    )


def _get_path_value(doc: Dict, path: str) -> Any:
    """Get value at JSON Pointer path."""
    if path == "" or path == "/":
        return doc

    parts = path.lstrip("/").split("/")
    current = doc

    for part in parts:
        if isinstance(current, dict):
            current = current[part]
        else:
            raise ValueError(f"Cannot traverse {part} on non-dict")

    return current


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python3 patch_knowledge_document.py [--stdin] [--schema] <document_path> [json_patch]",
            file=sys.stderr,
        )
        print("\nOptions:", file=sys.stderr)
        print("  --stdin    Read patch from stdin instead of argument", file=sys.stderr)
        print("  --schema   Print JSON schema for model type in document", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print(
            '  python3 patch_knowledge_document.py doc.k.json \'[{"op": "replace", "path": "/label", "value": "new"}]\'',
            file=sys.stderr,
        )
        print(
            '  cat patch.json | python3 patch_knowledge_document.py --stdin doc.k.json',
            file=sys.stderr,
        )
        print(
            '  python3 patch_knowledge_document.py doc.k.json --schema  # Print schema for model in doc.k.json',
            file=sys.stderr,
        )
        print(
            '  python3 patch_knowledge_document.py doc.k.json  # Re-render only',
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse arguments
    stdin_mode = False
    schemas_mode = False
    json_patch = None

    idx = 1
    # Parse flags
    while idx < len(sys.argv) and sys.argv[idx].startswith("--"):
        if sys.argv[idx] == "--stdin":
            stdin_mode = True
        elif sys.argv[idx] == "--schema":
            schemas_mode = True
        else:
            print(f"Error: Unknown flag {sys.argv[idx]}", file=sys.stderr)
            sys.exit(1)
        idx += 1

    # Get document path (always required)
    if idx >= len(sys.argv):
        print("Error: document_path is required", file=sys.stderr)
        sys.exit(1)
    document_path = sys.argv[idx]
    idx += 1

    # Check for --schema flag after document path
    if idx < len(sys.argv) and sys.argv[idx] == "--schema":
        schemas_mode = True
        idx += 1

    # Handle --schema mode: print schema for model in document
    if schemas_mode:
        try:
            doc_path = Path(document_path)
            if not doc_path.exists():
                print(f"Error: Document not found: {document_path}", file=sys.stderr)
                sys.exit(1)

            # Read document to get model type
            doc_content = doc_path.read_text(encoding="utf-8")
            doc_dict = json.loads(doc_content)
            model_type = doc_dict.get("type", "Doc")

            # Get schema for this model type
            model_registry = get_model_registry()
            ModelClass = model_registry.get(model_type)

            if not ModelClass:
                print(f"Error: Unknown model type: {model_type}", file=sys.stderr)
                sys.exit(1)

            # Print schema
            schema = ModelClass.model_json_schema()
            print(json.dumps(schema, indent=2))
            sys.exit(0)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {document_path}: {str(e)}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to load schema: {str(e)}", file=sys.stderr)
            sys.exit(1)

    # Get patch from argument or stdin
    if stdin_mode:
        # Read patch from stdin
        json_patch = sys.stdin.read().strip()
        if not json_patch:
            json_patch = None
    elif idx < len(sys.argv):
        # Patch provided as argument
        json_patch = sys.argv[idx]

    result = apply_json_patch(document_path, json_patch)

    if result:
        # Error occurred
        error_data = result.model_dump(exclude_none=True)
        print(json.dumps(error_data, indent=2))
        sys.exit(1)
    else:
        # Success
        if json_patch is not None:
            action = "Patched/Created"
        else:
            action = "Re-rendered"

        # Show what was done
        md_path = Path(document_path).with_suffix(".md")
        print(f"✓ {action} {document_path}")
        print(f"✓ Rendered {md_path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
