#!/usr/bin/env python3
"""Tests for knowledge_tools API - apply_json_patch function."""

import json
import sys
import tempfile
from pathlib import Path
import pytest

from patch_knowledge_document import apply_json_patch
from common.response import ApplyPatchErrorResponse


@pytest.fixture
def temp_doc():
    """Create temporary document for testing."""
    doc = {
        "id": "root",
        "label": "Root",
        "type": "Doc",
        "metadata": {},
        "children": {
            "child1": {
                "id": "child1",
                "label": "Child 1",
                "type": "Doc",
                "metadata": {}
            }
        }
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(doc, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


class TestSuccess:
    """Test successful patch operations."""

    def test_add_node(self, temp_doc):
        """Test adding a new node to children."""
        patch = json.dumps([
            {
                "op": "add",
                "path": "/children/child2",
                "value": {
                    "id": "child2",
                    "label": "Child 2",
                    "type": "Doc"
                }
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is None, f"Expected success but got error: {error}"

        # Verify document was updated
        doc_content = json.loads(Path(temp_doc).read_text())
        assert "child2" in doc_content["children"]
        assert doc_content["children"]["child2"]["label"] == "Child 2"

    def test_update_label(self, temp_doc):
        """Test updating an existing field."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/label",
                "value": "Updated Root"
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is None

        doc_content = json.loads(Path(temp_doc).read_text())
        assert doc_content["label"] == "Updated Root"

    def test_remove_node(self, temp_doc):
        """Test removing a node."""
        patch = json.dumps([
            {
                "op": "remove",
                "path": "/children/child1"
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is None

        doc_content = json.loads(Path(temp_doc).read_text())
        assert "child1" not in doc_content["children"]

    def test_multiple_operations(self, temp_doc):
        """Test multiple patch operations in one call."""
        patch = json.dumps([
            {
                "op": "add",
                "path": "/children/child2",
                "value": {"id": "child2", "label": "Child 2", "type": "Doc"}
            },
            {
                "op": "replace",
                "path": "/label",
                "value": "Multi Op Root"
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is None

        doc_content = json.loads(Path(temp_doc).read_text())
        assert "child2" in doc_content["children"]
        assert doc_content["label"] == "Multi Op Root"


class TestJsonPatchSyntaxError:
    """Test JSON Patch syntax error handling."""

    def test_invalid_json(self, temp_doc):
        """Test invalid JSON in patch string."""
        patch = "not valid json"

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert isinstance(error, ApplyPatchErrorResponse)
        assert "syntax" in error.error.lower()
        assert error.hint is not None
        assert error.example is not None
        assert len(error.example) > 0

    def test_invalid_json_includes_schema(self, temp_doc):
        """Test that invalid JSON error includes document schema in hint."""
        patch = "not valid json"

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert error.hint is not None
        # Schema should be included in hint
        assert "properties" in error.hint
        assert "id" in error.hint  # Required field in Doc schema
        assert "label" in error.hint  # Required field in Doc schema
        assert "type" in error.hint  # Type field in Doc schema
        assert "children" in error.hint  # Children field in Doc schema

    def test_not_array(self, temp_doc):
        """Test patch that's not an array."""
        patch = json.dumps({"op": "add", "path": "/label", "value": "test"})

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert "array" in error.error.lower()
        assert error.example is not None

    def test_missing_required_field(self, temp_doc):
        """Test patch operation missing required field."""
        patch = json.dumps([
            {
                "op": "add",
                "value": {"id": "test", "label": "Test", "type": "Doc"}
                # missing "path"
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert error.example is not None


class TestPathNotFoundError:
    """Test path not found error handling."""

    def test_path_not_found(self, temp_doc):
        """Test operation on non-existent path."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/nonexistent/path",
                "value": "test"
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert "path" in error.error.lower() and "not found" in error.error.lower()
        assert error.hint is not None

    def test_child_not_found_suggests_parent(self, temp_doc):
        """Test that missing child suggests parent and existing children."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/children/nonexistent/label",
                "value": "test"
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert error.hint is not None
        # Should suggest parent path or existing children if determinable
        if error.existing_children:
            assert "child1" in error.existing_children


class TestPydanticValidationError:
    """Test Pydantic validation error handling."""

    def test_missing_required_field_id(self, temp_doc):
        """Test validation error when required field is missing."""
        patch = json.dumps([
            {
                "op": "add",
                "path": "/children/invalid",
                "value": {
                    "label": "No ID",
                    "type": "Doc"
                    # missing required "id"
                }
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert "validation" in error.error.lower()
        assert error.hint is not None
        assert "schema" in error.hint.lower()
        assert error.details is not None

    def test_invalid_type_value(self, temp_doc):
        """Test validation error with invalid type value."""
        patch = json.dumps([
            {
                "op": "add",
                "path": "/children/invalid",
                "value": {
                    "id": "invalid",
                    "label": "Wrong Type",
                    "type": "InvalidType"
                }
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert "validation" in error.error.lower()
        assert error.hint is not None
        assert "schema" in error.hint.lower()

    def test_schema_returned(self, temp_doc):
        """Test that schema is included in validation error hint."""
        patch = json.dumps([
            {
                "op": "replace",
                "path": "/label",
                "value": 123
            }
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert "properties" in error.hint


class TestDocumentNotFound:
    """Test handling of non-existent documents."""

    def test_document_not_found(self):
        """Test re-render operation on non-existent file."""
        # Re-render without patch should fail with "not found" error
        error = apply_json_patch("/nonexistent/path/document.json", None)

        assert error is not None
        assert "not found" in error.error.lower()


class TestFileProtection:
    """Test file protection and write modes."""

    def test_file_is_readable_after_write(self, temp_doc):
        """Test that file is readable after successful write."""
        patch = json.dumps([
            {"op": "replace", "path": "/label", "value": "New Label"}
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is None

        # File should be readable and contain updated content
        content = json.loads(Path(temp_doc).read_text())
        assert content["label"] == "New Label"

    def test_file_unchanged_on_error(self, temp_doc):
        """Test that file is unchanged if patch fails."""
        original_content = json.loads(Path(temp_doc).read_text())

        # Try invalid patch
        patch = json.dumps([
            {"op": "replace", "path": "/nonexistent", "value": "test"}
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is not None

        # File should be unchanged
        current_content = json.loads(Path(temp_doc).read_text())
        assert current_content == original_content


class TestErrorResponseStructure:
    """Test ApplyPatchErrorResponse structure."""

    def test_error_response_required_fields(self, temp_doc):
        """Test that error response has required fields."""
        patch = "invalid json"

        error = apply_json_patch(temp_doc, patch)

        assert error is not None
        assert hasattr(error, "error")
        assert hasattr(error, "operation")
        assert error.operation == "apply_json_patch"

    def test_success_returns_none(self, temp_doc):
        """Test that successful operation returns None, not response."""
        patch = json.dumps([
            {"op": "replace", "path": "/label", "value": "Success"}
        ])

        error = apply_json_patch(temp_doc, patch)

        assert error is None


@pytest.fixture
def temp_spec_doc():
    """Spec document with one unverified constraint (fails_count unset)."""
    doc = {
        "type": "Spec",
        "model_version": 1,
        "version": 1,
        "description": "Test spec",
        "features": {
            "f1": {
                "type": "Feature",
                "model_version": 1,
                "id": "f1",
                "description": "Test feature",
                "constraints": {
                    "c1": {
                        "id": "c1",
                        "cmd": "echo test",
                        "description": "Unverified constraint"
                    }
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".k.json", delete=False
    ) as f:
        json.dump(doc, f)
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink()
    md_path = Path(temp_path).with_suffix(".md")
    if md_path.exists():
        md_path.unlink()


class TestFailsCountElevationBlocked:
    """User-driven patches must not elevate fails_count on an existing constraint
    nor fabricate a new "verified" constraint. Only check_spec_constraints.py's
    admin-path writer may set fails_count.
    """

    def test_patch_replace_fails_count_on_existing_unverified_constraint_is_blocked(self, temp_spec_doc):
        """Elevating fails_count 0 → N on an existing constraint through the
        user-facing patch API must error. This is the "smuggling" attack."""
        original = json.loads(Path(temp_spec_doc).read_text())

        patch = json.dumps([
            {
                "op": "add",
                "path": "/features/f1/constraints/c1/fails_count",
                "value": 1
            }
        ])

        error = apply_json_patch(temp_spec_doc, patch)

        assert error is not None, "Expected error when user elevates fails_count, got success"
        assert isinstance(error, ApplyPatchErrorResponse)
        assert json.loads(Path(temp_spec_doc).read_text()) == original

    def test_patch_add_new_constraint_with_fails_count_is_blocked(self, temp_spec_doc):
        """Creating a brand-new constraint with fails_count > 0 must error.

        Attack vector: a user fabricates a "verified" constraint (fails_count=1)
        in one patch call, skipping the check_spec_constraints.py flow that is
        the only legitimate writer of fails_count.
        """
        original = json.loads(Path(temp_spec_doc).read_text())

        patch = json.dumps([
            {
                "op": "add",
                "path": "/features/f1/constraints/c_new",
                "value": {
                    "id": "c_new",
                    "cmd": "echo new",
                    "description": "Smuggled constraint",
                    "fails_count": 1
                }
            }
        ])

        error = apply_json_patch(temp_spec_doc, patch)

        persisted = json.loads(Path(temp_spec_doc).read_text())
        smuggled = persisted.get("features", {}).get("f1", {}).get("constraints", {}).get("c_new")
        assert error is not None, (
            "Expected error when user creates constraint with fails_count>0, "
            f"but apply_json_patch returned success and persisted: {smuggled}"
        )
        assert isinstance(error, ApplyPatchErrorResponse)

        # File must be untouched.
        assert persisted == original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
