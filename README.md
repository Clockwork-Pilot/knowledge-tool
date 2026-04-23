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

### Registry Location

The registry file (`.protected_files.txt`) is stored in the directory given by the `PROJECT_ROOT` environment variable. If `PROJECT_ROOT` is not set, the current working directory is used.

```bash
# Point registry at a specific project
export PROJECT_ROOT=/path/to/project
python /path/to/knowledge_tool/patch_knowledge_document.py doc.k.json '[...]'

# Registry file will be stored at $PROJECT_ROOT/.protected_files.txt
```

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
