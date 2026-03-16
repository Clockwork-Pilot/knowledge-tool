# y2-knowledge-tool

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
python /path/to/knowledge_tool/patch_knowledge_document.py doc.json '[{"op": "replace", "path": "/label", "value": "Updated"}]'

# Create new document
python /path/to/knowledge_tool/patch_knowledge_document.py doc.json '[{"op": "add", "path": "/id", "value": "my_doc"}]'
```

## Installation Note

⚠️ **Do NOT install this package with `pip install`**. Use the scripts directly:
- The scripts are self-contained and work from any directory without installation
- Run `patch_knowledge_document.py` directly: `python /path/to/patch_knowledge_document.py`
- The script automatically locates its dependencies in the `src/` directory

## Development in Docker

```bash
# Run in docker with SSH agent and volume mounts
mkdir $(pwd)/.credentials -p && \
  docker run -it --rm  \
    --user 1000:1000  \
    -w /project \
    -v $HOME/.ssh/id_ed25519.pub:/home/node/.ssh/id_ed25519.pub:ro \
    -v $SSH_AUTH_SOCK:/ssh-agent \
    -e SSH_AUTH_SOCK=/ssh-agent \
    -v $(pwd)/.credentials:/home/node/:Z  \
    -v $(pwd):/project y2-coder

# Inside container: activate venv and use the tools (do NOT pip install)
cd /project && source .venv/bin/activate
python apply_json_patch.py --help
```