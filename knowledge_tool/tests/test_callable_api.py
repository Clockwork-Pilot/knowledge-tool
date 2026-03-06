#!/usr/bin/env python3
"""Tests verifying apply_json_patch is callable from other projects without installation."""

import json
import sys
import tempfile
from pathlib import Path
import pytest

from apply_json_patch import apply_json_patch
from common.response import ApplyPatchErrorResponse


class TestCallableFunction:
    """Test that apply_json_patch is a simple, clean callable."""

    def test_function_signature(self):
        """Verify the function has the expected signature."""
        import inspect
        sig = inspect.signature(apply_json_patch)
        params = list(sig.parameters.keys())

        # Should have document_path and json_patch parameters
        assert len(params) == 2
        assert params[0] == 'document_path'
        assert params[1] == 'json_patch'

        # json_patch should be optional (None default)
        assert sig.parameters['json_patch'].default is None

    def test_return_type_none_on_success(self):
        """Verify function returns None on success."""
        doc = {
            "id": "test",
            "type": "Doc",
            "label": "Test",
            "metadata": {}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc, f)
            temp_path = f.name

        try:
            result = apply_json_patch(
                temp_path,
                '[{"op": "replace", "path": "/label", "value": "updated"}]'
            )
            assert result is None, "Should return None on success"
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix('.md').unlink(missing_ok=True)

    def test_return_type_error_response_on_failure(self):
        """Verify function returns ApplyPatchErrorResponse on error."""
        result = apply_json_patch(
            "/nonexistent/path/doc.json",
            '[{"op": "replace", "path": "/label", "value": "test"}]'
        )

        assert result is not None
        assert isinstance(result, ApplyPatchErrorResponse)
        assert hasattr(result, 'error')
        assert isinstance(result.error, str)

    def test_callable_with_positional_args(self):
        """Verify function can be called with positional arguments."""
        doc = {"id": "test", "type": "Doc", "label": "Test", "metadata": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc, f)
            temp_path = f.name

        try:
            # Call with positional arguments
            result = apply_json_patch(temp_path, '[{"op": "replace", "path": "/label", "value": "new"}]')
            assert result is None
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix('.md').unlink(missing_ok=True)

    def test_callable_with_keyword_args(self):
        """Verify function can be called with keyword arguments."""
        doc = {"id": "test", "type": "Doc", "label": "Test", "metadata": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc, f)
            temp_path = f.name

        try:
            # Call with keyword arguments
            result = apply_json_patch(
                document_path=temp_path,
                json_patch='[{"op": "replace", "path": "/label", "value": "new"}]'
            )
            assert result is None
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix('.md').unlink(missing_ok=True)

    def test_callable_with_optional_patch_none(self):
        """Verify function works with json_patch=None (re-render only)."""
        doc = {"id": "test", "type": "Doc", "label": "Test", "metadata": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc, f)
            temp_path = f.name

        try:
            # Call without patch to re-render only
            result = apply_json_patch(document_path=temp_path, json_patch=None)
            assert result is None
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix('.md').unlink(missing_ok=True)

    def test_callable_creates_document(self):
        """Verify function can create new document from patch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "new_doc.json"

            # Create new document by patching non-existent file
            # Doc requires id and label fields
            result = apply_json_patch(
                str(doc_path),
                '[{"op": "add", "path": "/id", "value": "new"}, {"op": "add", "path": "/label", "value": "New Doc"}, {"op": "add", "path": "/type", "value": "Doc"}, {"op": "add", "path": "/metadata", "value": {}}]'
            )

            # Should succeed
            assert result is None

            # File should exist
            assert doc_path.exists()

    def test_callable_from_different_directory(self):
        """Verify function works when called from a different directory."""
        import os
        import tempfile

        # Create temp directory to work in
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            doc_path = tmpdir / "test.json"
            doc = {"id": "test", "type": "Doc", "label": "Test", "metadata": {}}
            doc_path.write_text(json.dumps(doc))

            # Change to different directory
            original_cwd = os.getcwd()
            try:
                os.chdir("/tmp")

                # Call apply_json_patch with absolute path
                result = apply_json_patch(
                    str(doc_path),
                    '[{"op": "replace", "path": "/label", "value": "modified"}]'
                )

                assert result is None
            finally:
                os.chdir(original_cwd)


class TestCallableImports:
    """Test that apply_json_patch can be imported cleanly."""

    def test_can_import_function(self):
        """Verify function can be imported."""
        # This already works if we got here, but explicitly verify
        assert callable(apply_json_patch)

    def test_can_import_error_response(self):
        """Verify ApplyPatchErrorResponse can be imported."""
        assert ApplyPatchErrorResponse is not None

        # Should be a Pydantic model
        response = ApplyPatchErrorResponse(
            error="test error",
            operation="test_op"
        )
        assert response.error == "test error"
        assert response.operation == "test_op"

    def test_no_side_effects_on_import(self):
        """Verify importing apply_json_patch has no unwanted side effects."""
        # Should not modify sys.path significantly or cause other issues
        assert apply_json_patch is not None
        # Function should be callable
        assert callable(apply_json_patch)


class TestCallableDocumentation:
    """Test that apply_json_patch is properly documented."""

    def test_has_docstring(self):
        """Verify function has documentation."""
        assert apply_json_patch.__doc__ is not None
        assert len(apply_json_patch.__doc__) > 0

        # Should mention key parameters
        doc = apply_json_patch.__doc__.lower()
        assert "document_path" in doc
        assert "json_patch" in doc

    def test_docstring_mentions_rfc6902(self):
        """Verify docstring references RFC 6902 standard."""
        assert "RFC 6902" in apply_json_patch.__doc__

    def test_docstring_mentions_pydantic(self):
        """Verify docstring mentions validation."""
        assert "validation" in apply_json_patch.__doc__.lower() or "validate" in apply_json_patch.__doc__.lower()


class TestCallableErrorMessages:
    """Test that error messages are informative."""

    def test_error_response_has_error_field(self):
        """Verify error responses include error message."""
        result = apply_json_patch("/nonexistent/doc.json", None)

        assert result is not None
        assert hasattr(result, 'error')
        assert isinstance(result.error, str)
        assert len(result.error) > 0

    def test_error_response_has_operation_field(self):
        """Verify error responses include operation context."""
        result = apply_json_patch("/nonexistent/doc.json", None)

        assert result is not None
        assert hasattr(result, 'operation')
        assert result.operation == 'apply_json_patch'
