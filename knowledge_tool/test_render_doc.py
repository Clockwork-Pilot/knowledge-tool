#!/usr/bin/env python3
"""Tests for Doc model rendering functionality and external model support."""

import json
import tempfile
from pathlib import Path
import pytest

from knowledge_tool.models import Doc
from knowledge_tool.common.render import render
from knowledge_tool.test_models.models import TestModel


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


class TestRenderWithExternalModels:
    """Test rendering with pluggable external models."""

    @pytest.fixture
    def test_models_path(self):
        """Path to test models for testing external/pluggable models."""
        # Get path to test_models directory
        return str(Path(__file__).parent / "test_models")

    def test_render_with_external_models(self, test_models_path):
        """Test rendering a custom Test model using external models."""
        test_model = TestModel(
            id="test_1",
            title="Test Document",
            description="A test document",
            metadata={"status": "active"}
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(test_model.model_dump(), f)
            temp_path = f.name

        try:
            # Render with external models
            result = render(temp_path, external_models_path=test_models_path)

            assert result is not None
            assert "# Test Document" in result
            assert "A test document" in result

            # Verify markdown file was created
            md_path = Path(temp_path).with_suffix(".md")
            assert md_path.exists()

            md_content = md_path.read_text()
            assert "# Test Document" in md_content
            assert "## Metadata" in md_content
            assert "status" in md_content
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)

    def test_render_without_external_models_fails_for_unknown_type(self):
        """Test that rendering unknown model type without external models fails."""
        test_model = TestModel(
            id="test_1",
            title="Test Document"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(test_model.model_dump(), f)
            temp_path = f.name

        try:
            # Render without external models should fail (return None)
            result = render(temp_path, external_models_path=None)
            assert result is None

            # Markdown file should not be created
            md_path = Path(temp_path).with_suffix(".md")
            assert not md_path.exists()
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
