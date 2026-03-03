#!/usr/bin/env python3
"""Tests for Doc model rendering functionality."""

import json
import tempfile
from pathlib import Path
import pytest

from knowledge_tool.models import Doc
from knowledge_tool.common.render import render


class TestDocRender:
    """Test Doc model render() method."""

    def test_render_document_with_structure(self):
        """Test rendering a document with metadata and nested structure."""
        doc = Doc(
            id="test",
            label="Test Document",
            metadata={
                "description": "A test document",
                "version": "1.0"
            },
            children={
                "section1": Doc(
                    id="section1",
                    label="First Section",
                    metadata={"status": "complete"}
                )
            }
        )

        result = doc.render()

        assert result is not None
        assert "# Test Document" in result
        assert "## First Section" in result
        assert "A test document" in result
        assert "1.0" in result

    def test_render_writes_md_file(self):
        """Test that render() function creates a .md file from JSON."""
        doc = Doc(
            id="test",
            label="Test Document",
            metadata={"description": "A test"}
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(doc.model_dump(), f)
            temp_path = f.name

        try:
            # Use render() function which handles file I/O
            result = render(temp_path)

            assert result is not None
            md_path = Path(temp_path).with_suffix(".md")
            assert md_path.exists()

            md_content = md_path.read_text()
            assert "# Test Document" in md_content
            assert "A test" in md_content
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
