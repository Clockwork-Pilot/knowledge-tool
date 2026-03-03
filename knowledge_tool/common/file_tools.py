#!/usr/bin/env python3
"""Common utilities for knowledge_tools file operations."""

import stat
from pathlib import Path


def write_protected_file(file_path: Path, content: str) -> None:
    """Write file with protection workflow.

    Process:
    1. Remove read-only/archive attributes if file exists
    2. Write to temp file for atomicity
    3. Atomic rename (replace)
    4. Set read-only/archive attributes

    Args:
        file_path: Path to output file
        content: Content to write
    """
    # Remove read-only/archive attributes if file exists
    if file_path.exists():
        current_mode = file_path.stat().st_mode
        file_path.chmod(current_mode | stat.S_IWUSR | stat.S_IWGRP)

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with exclusive lock semantics
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        # Write to temp file first for atomicity
        temp_path.write_text(content, encoding="utf-8")

        # Atomic rename
        temp_path.replace(file_path)
    finally:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()

    # Set read-only/archive attributes
    current_mode = file_path.stat().st_mode
    file_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
