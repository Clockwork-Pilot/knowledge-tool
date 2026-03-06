#!/usr/bin/env python3
"""Tests for knowledge files registry functionality."""

import tempfile
from pathlib import Path
import pytest

from knowledge_tool.knowledge_files_registry import (
    add_knowledge_file,
    add_knowledge_files,
    is_knowledge_file,
    get_knowledge_files,
)


@pytest.fixture
def temp_registry(monkeypatch):
    """Create a temporary registry file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    monkeypatch.setattr(
        "knowledge_tool.knowledge_files_registry.get_registry_path",
        lambda: Path(temp_path),
    )

    yield temp_path
    Path(temp_path).unlink(missing_ok=True)


def test_add_and_check_knowledge_files(temp_registry):
    """Test adding files and checking if they are registered."""
    add_knowledge_files(["/path/file1.json", "/path/file1.md"])

    assert is_knowledge_file("/path/file1.json") is True
    assert is_knowledge_file("/path/file1.md") is True
    assert is_knowledge_file("/path/other.json") is False

    files = get_knowledge_files()
    assert len(files) == 2
