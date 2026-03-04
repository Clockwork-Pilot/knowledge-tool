#!/usr/bin/env python3
"""Tests for external/pluggable model support in apply_json_patch."""

import json
import tempfile
from pathlib import Path
import pytest

from knowledge_tool.apply_json_patch import apply_json_patch


@pytest.fixture
def external_models_path():
    """Path to external models folder."""
    return str(Path(__file__).parent / "test_models")


@pytest.fixture
def temp_custom_doc():
    """Create temporary test document for testing."""
    doc = {
        "type": "TestModel",
        "id": "test1",
        "title": "Test Document",
        "description": "A test document",
        "metadata": {"key": "value"}
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(doc, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


class TestExternalModels:
    """Test external model support."""

    def test_load_custom_model(self, temp_custom_doc, external_models_path):
        """Test patching a document with custom model type."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/title",
                "value": "Updated Custom Title"
            }
        ])

        error = apply_json_patch(temp_custom_doc, patch, external_models_path=external_models_path)

        assert error is None, f"Expected success but got error: {error}"

        # Verify document was updated
        doc_content = json.loads(Path(temp_custom_doc).read_text())
        assert doc_content["title"] == "Updated Custom Title"

    def test_custom_model_metadata(self, temp_custom_doc, external_models_path):
        """Test updating metadata in custom model."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/metadata/key",
                "value": "updated_value"
            }
        ])

        error = apply_json_patch(temp_custom_doc, patch, external_models_path=external_models_path)

        assert error is None

        doc_content = json.loads(Path(temp_custom_doc).read_text())
        assert doc_content["metadata"]["key"] == "updated_value"

    def test_unknown_model_type_with_external_models(self, temp_custom_doc, external_models_path):
        """Test error when using unknown model type even with external models."""
        doc = {
            "type": "UnknownType",
            "id": "test1",
            "name": "Test"
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(doc, f)
            temp_path = f.name

        try:
            patch = json.dumps([{"op": "replace", "path": "/name", "value": "Updated"}])
            error = apply_json_patch(temp_path, patch, external_models_path=external_models_path)

            assert error is not None
            assert "Unknown model type" in error.error
        finally:
            Path(temp_path).unlink()

    def test_invalid_external_models_path(self, temp_custom_doc):
        """Test error when external models path doesn't exist."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/title",
                "value": "Updated"
            }
        ])

        error = apply_json_patch(
            temp_custom_doc,
            patch,
            external_models_path="/nonexistent/path"
        )

        assert error is not None
        assert "not found" in error.error.lower()

    def test_default_models_still_work(self, external_models_path):
        """Test that default Doc model still works with external models path."""
        doc = {
            "id": "root",
            "label": "Root",
            "type": "Doc",
            "metadata": {},
            "children": {}
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(doc, f)
            temp_path = f.name

        try:
            patch = json.dumps([
                {
                    "op": "replace",
                    "path": "/label",
                    "value": "Updated Root"
                }
            ])

            error = apply_json_patch(temp_path, patch, external_models_path=external_models_path)

            assert error is None
            doc_content = json.loads(Path(temp_path).read_text())
            assert doc_content["label"] == "Updated Root"
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
