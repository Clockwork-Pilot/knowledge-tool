# Knowledge Tools

## Table of Contents

- [Version](#version)
- [Backend](#backend)
- [API](#api)
    - [Scripts](#scripts)
      - [apply_json_patch.py](#apply_json_patchpy)
        - [Using Stdin for Complex Patches](#using-stdin-for-complex-patches)
    - [Functions](#functions)
      - [apply_json_patch()](#apply_json_patch)
        - [Rendering Behavior](#rendering-behavior)
      - [Pluggable Models](#pluggable-models)
        - [Overview](#overview)
        - [Usage](#usage)
        - [Creating Custom Models](#creating-custom-models)
      - [Opts Configuration](#opts-configuration)
        - [render_priority Field](#render_priority-field)
    - [Configuration](#configuration)
      - [knowledge_config.yaml](#knowledge_configyaml)
      - [Environment Variables](#environment-variables)
        - [KNOWLEDGE_TOOL_CONFIG_ROOT](#knowledge_tool_config_root)
      - [Automatic Discovery](#automatic-discovery)
      - [Configuration File Format](#configuration-file-format)
        - [Built-in Models](#built-in-models)
        - [Pluggable Models Directories](#pluggable-models-directories)
        - [Model Merging Strategy](#model-merging-strategy)
- [File Modification Workflow](#file-modification-workflow)
- [Architecture](#architecture)
    - [Json Patch](#json-patch)
    - [Document Rendering](#document-rendering)
    - [Workflow](#workflow)
    - [File Protection Purpose](#file-protection-purpose)
- [Testing](#testing)
- [Installation Note](#installation-note)
- [Python API Usage](#python-api-usage)
    - [Function Signature](#function-signature)
    - [Usage Examples](#usage-examples)
      - [Hello World Example](#hello-world-example)
    - [Using from Other Projects](#using-from-other-projects)
    - [Error Handling](#error-handling)

Updated description

## Version
2.0.0

## Backend
knowledge_base_system

## API
Public interfaces for knowledge tools: command-line scripts and Python functions

### Scripts
Command-line script interfaces

#### apply_json_patch.py
Apply JSON Patch operations to knowledge documents from command line with automatic markdown rendering. Supports both command-line arguments and stdin input to avoid shell escaping issues. Works with built-in models and pluggable custom models configured in knowledge_config.yaml.

##### Expected Output
✓ Patched doc.json

##### Using Stdin for Complex Patches
For complex JSON patches with many nested quotes, pass the patch via stdin to avoid shell escaping issues.

###### Why
Shell escaping can be error-prone with deeply nested JSON. Use stdin for reliability.

### Functions
Python function interfaces for programmatic use

#### apply_json_patch()
Apply JSON Patch to document file with validation and automatic markdown rendering.

```
apply_json_patch(document_path: str, json_patch: Optional[str] = None) -> Optional[ApplyPatchErrorResponse]
```

##### Parameters
  - document_path (str): Path to JSON document file
  - json_patch (Optional[str]): RFC 6902 JSON Patch operations as JSON string. If None, only re-renders without patching (default: None)

##### Returns
None on success, ApplyPatchErrorResponse object on error with detailed context

##### Exceptions
  - JsonPatchException - Invalid patch format
  - ValidationError - Schema violation
  - FileNotFoundError - Document not found
  - IOError - File access issues

##### Behavior
All exceptions caught and returned as ApplyPatchErrorResponse with helpful hints

##### Safety
Atomic operations, in-memory validation before write, file protection workflow, read-only file management

##### Rendering
Every successful patch automatically generates markdown: document.json → document.md with identical file protection

##### Rendering Behavior
When apply_json_patch succeeds, it always attempts to regenerate the markdown file.

###### When Renders
  - After successful patch application and write
  - When called with no patch (re-render only mode)
  - In both --stdin and command-line argument modes

###### What Happens
  1. JSON is validated against Pydantic schema
  2. File is written with atomic operations
  3. Markdown (.md file) is automatically generated from the JSON
  4. Both files are set to read-only for protection

###### Rendering Failures
  - If rendering fails, operation still succeeds (JSON is safe)
  - User is warned via stderr: ⚠️ Warning: Failed to render markdown: ...
  - JSON and markdown may be out of sync
  - Patch command will exit with code 0 (success)

###### Important
Always check stderr for warnings about rendering failures

#### Pluggable Models
Extend apply_json_patch with custom model types by configuring external model definitions in knowledge_config.yaml. Models are auto-discovered by searching for knowledge_config.yaml in the project directory hierarchy.

##### Overview
Pluggable models allow you to define custom document types beyond the built-in Doc model. External models are loaded dynamically and work seamlessly with apply_json_patch validation and rendering.

###### Key Points
  - Load custom model classes from external Python files
  - All internal models (Doc, Task, etc.) continue to work normally
  - External and internal models coexist in the same registry
  - Custom models inherit from RenderableModel and implement render()
  - Validation works the same way as built-in models

###### Internal Models
  - Doc - Default document model with hierarchical children
  - Feature - Feature definition model
  - Spec - Specification model
  - ChecksResults - Test/constraint results model

##### Usage
How to use pluggable models with apply_json_patch.

###### Command Line
# Models configured in knowledge_config.yaml are auto-discovered
apply-json-patch doc.json '[{"op": "replace", "path": "/type", "value": "CustomType"}]'

###### Python Function
apply_json_patch(document_path, json_patch)

###### Folder Structure
# Configure in knowledge_config.yaml:
pluggable_models_dirs:
  - ./models
  - ./custom_models

# File structure:
custom_models/
  my_model.py      # Contains class MyModel(RenderableModel)
  other_model.py   # Contains class OtherModel(RenderableModel)

##### Creating Custom Models
How to create a pluggable model.

###### Requirements
  - Inherit from RenderableModel
  - Define type as Literal["ModelType"]
  - Implement render() method returning markdown string
  - Optionally implement tips() method
  - Use Pydantic Field for schema validation

###### Example Code
from typing import Literal
from pydantic import Field
from models import RenderableModel

class MyModel(RenderableModel):
    type: Literal["MyModel"] = "MyModel"
    id: str = Field(..., description="Unique ID")
    title: str = Field(..., description="Title")
    
    def render(self) -> str:
        return f"# {self.title}"
    
    def tips(self) -> list:
        return ["Custom model loaded successfully"]

#### Opts Configuration
Non-displayable rendering options for document nodes

##### render_priority Field
When true, renders node before siblings with render_priority=false

###### Type
bool

### Configuration
Knowledge tool models are configured via knowledge_config.yaml file. The tool automatically searches for this file in the following locations, in priority order.

#### knowledge_config.yaml
YAML configuration file that defines pluggable model directories for loading custom RenderableModel implementations.

**File Location:**
- Default: Same directory as apply_json_patch.py script
- Or: Project root when used as dependency
- Or: Use KNOWLEDGE_TOOL_CONFIG_ROOT environment variable to override

**Content:** Single key `pluggable_models_dirs` with list of relative or absolute paths to directories containing model definitions.

**Paths:** Can be relative (to config file location) or absolute paths to model directories.

##### Example
# Basic Configuration File:
# Place this at project root or where apply_json_patch is called
pluggable_models_dirs:
  - ./models
  - ./custom_models
  - /absolute/path/to/models

#### Environment Variables
Control configuration via environment variables.

##### KNOWLEDGE_TOOL_CONFIG_ROOT
Control where knowledge_config.yaml is searched for.

###### Resolution Order
  1. KNOWLEDGE_TOOL_CONFIG_ROOT - Highest priority, explicitly set config directory
  2. Upward directory search - Walks up from current working directory
  3. Script directory (knowledge_tool/) - Default fallback
  4. Empty config if not found - Only built-in models (Doc, Task, etc.)

###### Examples
  - KNOWLEDGE_TOOL_CONFIG_ROOT=/etc/knowledge_document_tools apply-json-patch doc.json '[...]'

#### Automatic Discovery
When used as a Claude plugin or in a Claude project, knowledge_config.yaml is automatically found without manual configuration by searching upward from the current working directory.

##### Plugin Usage
Tool automatically searches for knowledge_config.yaml in parent directories

##### Project Usage
Tool automatically searches for knowledge_config.yaml in parent directories

##### Manual Override
Set KNOWLEDGE_TOOL_CONFIG_ROOT to explicitly specify config location

#### Configuration File Format
The knowledge_config.yaml file configures pluggable model directories for the knowledge tool. Place this file in the same directory as apply_json_patch.py script, or set KNOWLEDGE_TOOL_CONFIG_ROOT environment variable to override the config location.

The knowledge tool always loads built-in models. External models from pluggable_models_dirs are merged with built-in models.

##### File Location
Same directory as apply_json_patch.py script

##### Env Override
KNOWLEDGE_TOOL_CONFIG_ROOT environment variable

##### Built-in Models
Built-in models are always loaded and available:
- Doc: Default document model with hierarchical children
- Feature: Feature definition model for constraints and testing
- Spec: Specification model
- ChecksResults: Test and constraint results tracking model

##### Pluggable Models Directories
List of directories containing custom/pluggable knowledge models. Paths are relative to the config file location.

###### Format
List of directory paths (relative or absolute)

###### Examples
  - ./models
  - ./custom_models
  - /absolute/path/to/models

##### Model Merging Strategy
External models from pluggable_models_dirs are merged with built-in models. If a custom model has the same name as a built-in model, the custom model takes precedence and overrides the built-in one.

## File Modification Workflow
How to properly modify knowledge documents using the tool. Models are loaded automatically from knowledge_config.yaml by searching the project directory hierarchy.

### Important
ALWAYS use apply_json_patch to modify documents. Never edit JSON files directly.

### Workflow
  1. Prepare JSON Patch operations (RFC 6902 format)
  2. Call apply_json_patch with document path and patch
  3. Tool automatically: removes read-only → writes atomically → restores read-only → renders markdown

### Why Important
  - Ensures data consistency and validation through Pydantic schema
  - Automatically regenerates markdown documentation
  - Maintains file protection (read-only flags)
  - Provides error handling and helpful hints
  - Atomic writes prevent partial/corrupted states

### Wrong Way
❌ Directly editing knowledge_tool.k.json with a text editor or file tools

### Right Way
✓ python tools/apply_json_patch.py knowledge_tool.k.json '[{"op": "replace", "path": "/label", "value": "Updated"}]'

## Architecture
API-first design with JSON Patch operations

### Json Patch
RFC 6902 JSON Patch standard for describing modifications to JSON documents.

**File:** tools/apply_json_patch.py

**Standard:** RFC 6902

**Operations:**
- add - Insert or replace value
- remove - Delete value at path
- replace - Replace value at path
- move - Move value from one path to another
- copy - Copy value from one path to another
- test - Assert value equals expected before applying

```
[{"op": "replace", "path": "/label", "value": "new_label"}, {"op": "add", "path": "/children/new_id", "value": {...}}]
```

#### Operation Structure
  - Required Fields: ['op', 'path']
  - Optional Fields: ['value', 'from']
  - Op: Operation type (add, remove, replace, move, copy, test)
  - Path: JSON Pointer to target location
  - Value: New value for add/replace/test operations
  - From: Source path for move/copy operations

### Document Rendering
Automatic markdown generation on patch application using pluggable RenderableModel classes. Handles file I/O for all model types (not a public API)

#### File
tools/common/render.py

#### Status
complete_internal_only

### Workflow
Complete knowledge tool operation workflow from API call to markdown generation.

**Main Flow:**
read JSON → validate patch → apply in memory → validate schema → write with protection → render markdown

**File Protection (within Write step):**
remove read-only → exclusive write → atomic rename → restore read-only

#### Main Steps
  1. Read Document - Load and parse JSON file
  2. Parse & Validate Patch - Validate RFC 6902 format
  3. Apply in Memory - Execute patch operations on dict
  4. Validate Schema - Check Pydantic Doc model
  5. Write with Protection - Atomic file write with read-only management
  6. Auto-Render Markdown - Generate .md from JSON

#### File Protection Phases
  - Remove read-only attribute
  - Exclusive write to temp file
  - Atomic rename to target
  - Restore read-only/archive attribute

### File Protection Purpose
Files are protected with read-only attributes after writing to prevent accidental corruption or modification. This applies to both JSON knowledge documents and their auto-rendered markdown pairs.

```
knowledge_tool.k.json
knowledge_tool.k.md
```

#### Purpose
  - Prevent accidental overwrites of validated JSON data
  - Ensure JSON and MD files always stay in sync (both locked together)
  - Protect against race conditions when multiple processes access files
  - Maintain document integrity as the source of truth for knowledge

#### File Locking Strategy
  - Both .json and .md files are set to read-only after successful write
  - Any modification requires removing read-only attribute first
  - Atomic write operations ensure files are never in partial state
  - Read-only flag restored immediately after write completes

## Testing
Comprehensive test suite with 19 tests covering all functionality.

```
pytest tools/ -v
pytest
```

## Installation Note
Do NOT install this package. Use the scripts directly without installation. The knowledge_tool is designed to work as-is without requiring package installation via pip. Simply run the scripts directly from their location with: python /path/to/knowledge_tool/apply_json_patch.py doc.json '[{"op": "replace", "path": "/label", "value": "Updated"}]'. The script automatically locates its dependencies in the src/ directory without requiring installation. This approach works from any directory, requires only Python dependencies installed via pip install -r requirements.txt, needs no package installation, and provides a cleaner project structure.

### Importance
critical

### Applies To
all scripts

## Python API Usage
The apply_json_patch function is a clean, simple callable that can be used directly from Python code without any installation. It works in any project by simply importing and calling the function.

### Stability
stable

### Breaking Changes
none

### Function Signature
apply_json_patch(document_path: str, json_patch: Optional[str] = None) -> Optional[ApplyPatchErrorResponse]

Simple two-parameter function:
- document_path: String path to JSON file (can be relative or absolute)
- json_patch: JSON Patch operations string (RFC 6902), or None to just re-render

Returns None on success, or ApplyPatchErrorResponse with error details on failure.

### Usage Examples
# Create or patch a document
from apply_json_patch import apply_json_patch

# Patch existing document
error = apply_json_patch('doc.json', '[{"op": "replace", "path": "/label", "value": "new"}]')
if error:
    print(f"Error: {error.error}")
else:
    print("Success")

# Create new document by providing patch for non-existent file
error = apply_json_patch('new_doc.json', '[{"op": "add", "path": "/id", "value": "doc1"}]')

# Re-render existing document without patching
error = apply_json_patch('doc.json', None)

#### Hello World Example
Complete JSON payload showing typical document structure with table of contents rendering enabled and 2 nested children

##### Json Payload
  - Type: Doc
  - Id: hello_world
  - Label: Hello World Guide
  - Description: A simple getting started guide with TOC rendering enabled
  - Metadata: {'version': '1.0', 'author': 'Developer'}
  - Opts: {'render_priority': False, 'render_toc': True}
  - Children: {'introduction': {'type': 'Doc', 'id': 'introduction', 'label': 'Introduction', 'description': 'Getting started with the basics', 'metadata': {'section': 'overview'}}, 'setup': {'type': 'Doc', 'id': 'setup', 'label': 'Setup Instructions', 'description': 'Step-by-step setup guide for beginners', 'metadata': {'section': 'installation', 'difficulty': 'beginner'}}}

### Using from Other Projects
To use apply_json_patch from another project:

1. Copy the apply_json_patch.py file to your project
2. Ensure jsonpatch and pydantic are installed: pip install jsonpatch pydantic
3. Import and use: from apply_json_patch import apply_json_patch

The function is self-contained and works without any installation or sys.path manipulation on the caller side. The script handles its own internal path setup automatically.

### Error Handling
The function returns None on success, or an ApplyPatchErrorResponse object on error. Check the response to get detailed error information:

if result := apply_json_patch(path, patch):
    print(result.error)
    if result.hint:
        print(result.hint)
    if result.details:
        print(result.details)
