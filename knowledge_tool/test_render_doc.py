#!/usr/bin/env python3
"""Tests for Doc model rendering functionality and external model support."""

import json
import tempfile
from pathlib import Path
import pytest

from knowledge_tool.models import Doc
from knowledge_tool.common.render import render
from knowledge_tool.common.model_loader import get_model_registry


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
    def task_lifecycle_models_path(self):
        """Path to task lifecycle models for testing."""
        # Get the project root by going up from knowledge_tool
        kt_root = Path(__file__).parent.parent.parent
        return str(kt_root / "tasks_lifecycle" / "knowledge_models")

    def test_render_task_with_external_models(self, task_lifecycle_models_path):
        """Test rendering a Task document using external models."""
        task_data = {
            "id": "task_1",
            "type": "Task",
            "plan": {
                "id": "plan",
                "label": "Test Task Plan",
                "type": "Doc",
                "metadata": {"created_at": "2026-03-03T00:00:00"}
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(task_data, f)
            temp_path = f.name

        try:
            # Render with external models
            result = render(temp_path, external_models_path=task_lifecycle_models_path)

            assert result is not None
            assert "Task: task_1" in result
            assert "Test Task Plan" in result

            # Verify markdown file was created
            md_path = Path(temp_path).with_suffix(".md")
            assert md_path.exists()

            md_content = md_path.read_text()
            assert "# Task: task_1" in md_content
            assert "## Plan" in md_content
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)

    def test_render_without_external_models_fails_for_task(self, task_lifecycle_models_path):
        """Test that rendering Task without external models fails."""
        task_data = {
            "id": "task_1",
            "type": "Task",
            "plan": {
                "id": "plan",
                "label": "Test Task Plan",
                "type": "Doc",
                "metadata": {"created_at": "2026-03-03T00:00:00"}
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(task_data, f)
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
