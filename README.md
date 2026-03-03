# y2-knowledge-tool

A reusable knowledge base system with JSON Patch operations, validation, and automatic markdown rendering.

## Important: Read-Only Files

❌ DO NOT Edit Read-only `.json` or `.md` Files Directly. 

All modifications must go through `apply_json_patch` 

If you encounter "Permission denied" when trying to edit, this is by design—use `apply_json_patch` instead.

## Documentation

**All documentation is maintained in `knowledge_tool.json`** which renders to `knowledge_tool.md`. This is the single source of truth for:
- API reference (Scripts and Functions)
- Architecture and workflow
- Examples and usage patterns
- Configuration options

To view the documentation: See `knowledge_tool.md` (auto-generated from JSON)

## Quick Start

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Apply JSON Patch to a document
python -m tools.apply_json_patch doc.json '[{"op": "replace", "path": "/label", "value": "Updated"}]'

# Create new document
python -m tools.apply_json_patch --create doc.json '[{"op": "add", "path": "/id", "value": "my_doc"}]'
```

## Configuration

### Centralized Python Cache
All `__pycache__` directories are configured to be created in `.cache/pycache/` via the `PYTHONPYCACHEPREFIX` environment variable. This keeps the project directory clean. The configuration is automatically applied when running tests via `conftest.py`.

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

# Inside container: activate venv and use the tools
cd /project && source .venv/bin/activate
python tools/apply_json_patch.py --help
```