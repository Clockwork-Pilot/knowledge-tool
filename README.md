# y2-knowledge_tool

A reusable knowledge base system with JSON Patch operations, validation, and automatic markdown rendering.

## Important: Read-Only Files

❌ DO NOT Edit Read-only `.k.json` or `.k.md` Files Directly.

All modifications must go through `patch_knowledge_document`

If you encounter "Permission denied" when trying to edit, this is by design—use `patch_knowledge_document` instead.

## Documentation

**Knowledge Tool documentation is maintained in `knowledge_tool.k.json`** which renders to `knowledge_tool.k.md`. This is the single source of truth for:
- API reference (Scripts and Functions)
- Architecture and workflow
- Examples and usage patterns
- Configuration options

To view the documentation: See `knowledge_tool.k.md` (auto-generated from JSON)

## Quick Start

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies only (do NOT install the package itself)
pip install -r requirements.txt

# Apply JSON Patch to a document
python /path/to/knowledge_tool/patch_knowledge_document.py doc.k.json '[{"op": "replace", "path": "/label", "value": "Updated"}]'

# Create new document
python /path/to/knowledge_tool/patch_knowledge_document.py doc.k.json '[{"op": "add", "path": "/id", "value": "my_doc"}]'
```

## Configuration

All configuration is centralized in `knowledge_tool/__init__.py` (single source of truth):

- **`PROTECTED_REGISTRY_FILENAME`**: Name of the registry file (default: `.protected_files.txt`)
- **`PROTECTED_REGISTRY_DIR`**: Directory where registry files are stored (configurable via environment variable)

### Customize Registry Location

Set the `PROTECTED_REGISTRY_DIR` environment variable:

```bash
# Use custom registry directory
export PROTECTED_REGISTRY_DIR=/path/to/custom/directory
python /path/to/knowledge_tool/patch_knowledge_document.py doc.k.json '[...]'

# Registry files will be stored in /path/to/custom/directory/.protected_files.txt
```

Default: Registry files are stored in the project root (parent of `knowledge_tool/` directory)

### Using the Public API

```python
# Core models and registry
from knowledge_tool import Doc, RenderableModel, MODEL_REGISTRY

# JSON Patch operations
from knowledge_tool.patch_knowledge_document import apply_json_patch

# Knowledge files tracking (optional)
from knowledge_files_registry import add_knowledge_files
```

## Installation Note

⚠️ **Do NOT install this package with `pip install`**. Use the scripts directly:
- The scripts are self-contained and work from any directory without installation
- Run `patch_knowledge_document.py` directly: `python /path/to/patch_knowledge_document.py`
- The script automatically locates its dependencies in the `src/` directory
