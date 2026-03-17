#!/usr/bin/env python3
"""Tests for create_knowledge_document script."""

import json
import sys
import tempfile
from pathlib import Path
import pytest

# Add parent dir to path for imports
_script_dir = Path(__file__).parent.parent
_src_dir = _script_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from create_knowledge_document import create_knowledge_document


class TestCreateKnowledgeDocument:
    """Test create_knowledge_document functionality."""

    def test_create_doc_document(self):
        """Creating Doc document succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test_doc.json"
            result = create_knowledge_document("Doc", str(doc_path))
            assert result == 0
            assert doc_path.exists()

    def test_create_task_document(self):
        """Creating Task document without spec succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "test_task.json"
            result = create_knowledge_document("Task", str(task_path))
            assert result == 0
            with open(task_path) as f:
                data = json.load(f)
            assert data["type"] == "Task"
            assert "spec" not in data or data.get("spec") is None

    def test_cannot_create_iteration_as_root(self):
        """Iteration cannot be created as root document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iter_path = Path(tmpdir) / "iteration.json"
            result = create_knowledge_document("Iteration", str(iter_path))
            assert result == 1
            assert not iter_path.exists()

    def test_cannot_overwrite_existing_document(self):
        """Cannot overwrite existing document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test.json"
            create_knowledge_document("Doc", str(doc_path))
            result = create_knowledge_document("Doc", str(doc_path))
            assert result == 1
