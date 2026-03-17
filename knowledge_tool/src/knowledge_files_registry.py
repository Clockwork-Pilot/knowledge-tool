#!/usr/bin/env python3
"""Utility module for managing knowledge files registry."""

import sys
from pathlib import Path
from typing import Set

try:
    from config import KNOWN_KNOWLEDGE_FILES_PATH
except ImportError:
    # When called from outside the project root, resolve config.py relative to this file:
    # knowledge_tool/knowledge_tool/src/ -> up 4 levels -> project root
    _project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(_project_root))
    from config import KNOWN_KNOWLEDGE_FILES_PATH


def _is_restricted_path(file_path: str) -> bool:
    """Check if a file path is in a restricted directory (e.g., /tmp, /var/tmp).

    Args:
        file_path: Path to check

    Returns:
        True if the path is in a restricted directory, False otherwise.
    """
    try:
        resolved_path = Path(file_path).resolve()
        restricted_dirs = [Path("/tmp"), Path("/var/tmp")]

        for restricted_dir in restricted_dirs:
            try:
                resolved_path.relative_to(restricted_dir)
                return True  # Path is in a restricted directory
            except ValueError:
                # Path is not in this restricted directory
                continue
        return False
    except Exception:
        # If we can't resolve the path, allow it (fail open)
        return False


def get_registry_path() -> Path:
    """Get the path to the knowledge files registry.

    Returns:
        Path object pointing to protected_files.txt in plugin root.
    """
    return KNOWN_KNOWLEDGE_FILES_PATH


def load_knowledge_files() -> Set[str]:
    """Load all registered knowledge files from registry file.

    Returns:
        Set of absolute file paths that are registered as knowledge files.
    """
    registry_path = get_registry_path()
    if not registry_path.exists():
        return set()

    try:
        content = registry_path.read_text().strip()
        if not content:
            return set()
        return set(line.strip() for line in content.split('\n') if line.strip())
    except Exception:
        return set()


def add_knowledge_file(file_path: str) -> None:
    """Add a file to the knowledge files registry.

    Args:
        file_path: Absolute path to the file to register.
    """
    # Filter out restricted paths (e.g., /tmp)
    if _is_restricted_path(file_path):
        return

    # Convert to absolute path
    abs_path = str(Path(file_path).resolve())

    # Load existing files
    known_files = load_knowledge_files()

    # Add the new file if not already present
    if abs_path not in known_files:
        known_files.add(abs_path)
        # Write updated registry
        registry_path = get_registry_path()
        registry_path.write_text('\n'.join(sorted(known_files)) + '\n')


def add_knowledge_files(file_paths: list) -> None:
    """Add multiple files to the knowledge files registry.

    Args:
        file_paths: List of absolute paths to register.
    """
    known_files = load_knowledge_files()

    for file_path in file_paths:
        # Filter out restricted paths (e.g., /tmp)
        if _is_restricted_path(file_path):
            continue

        abs_path = str(Path(file_path).resolve())
        known_files.add(abs_path)

    if file_paths:
        registry_path = get_registry_path()
        registry_path.write_text('\n'.join(sorted(known_files)) + '\n')


def is_knowledge_file(file_path: str) -> bool:
    """Check if a file is registered as a knowledge file.

    Args:
        file_path: Path to check (can be relative or absolute).

    Returns:
        True if the file is a registered knowledge file, False otherwise.
    """
    # Convert to absolute path
    abs_path = str(Path(file_path).resolve())

    known_files = load_knowledge_files()
    return abs_path in known_files


def get_knowledge_files() -> Set[str]:
    """Get all registered knowledge files.

    Returns:
        Set of all registered knowledge file paths.
    """
    return load_knowledge_files()
