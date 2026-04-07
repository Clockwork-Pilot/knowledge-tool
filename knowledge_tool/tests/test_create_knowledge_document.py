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


    def test_cannot_overwrite_existing_document(self):
        """Cannot overwrite existing document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test.json"
            create_knowledge_document("Doc", str(doc_path))
            result = create_knowledge_document("Doc", str(doc_path))
            assert result == 1
