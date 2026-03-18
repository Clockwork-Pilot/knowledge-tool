"""Tests verifying knowledge_tool behavior with invalid patch data."""

import json
import pytest

from patch_knowledge_document import apply_json_patch


@pytest.fixture
def doc_path(tmp_path):
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
    p = tmp_path / "test_doc.json"
    p.write_text(json.dumps(doc))
    return str(p)


def assert_error(result, expected_fragment):
    assert result is not None
    assert expected_fragment.lower() in result.error.lower()


class TestJsonSyntaxErrors:
    @pytest.mark.parametrize("patch", [
        "this is not json at all {[ ]",
    ])
    def test_invalid_json_string(self, doc_path, patch):
        assert_error(apply_json_patch(doc_path, patch), "syntax")

    @pytest.mark.parametrize("patch", [
        '{"op": "add", "path": "/label", "value": "test"}',
        '"not an array"',
    ])
    def test_non_array_json(self, doc_path, patch):
        assert_error(apply_json_patch(doc_path, patch), "array")


class TestPatchStructureErrors:
    @pytest.mark.parametrize("patch", [
        '[{"path": "/label", "value": "test"}]',
        '[{"op": "add", "value": "test"}]',
        '[{"op": "invalid_op", "path": "/label", "value": "test"}]',
    ])
    def test_malformed_operation(self, doc_path, patch):
        assert_error(apply_json_patch(doc_path, patch), "syntax")


class TestPathErrors:
    @pytest.mark.parametrize("patch", [
        '[{"op": "replace", "path": "/nonexistent/path", "value": "test"}]',
        '[{"op": "replace", "path": "/children/0", "value": "test"}]',
    ])
    def test_invalid_path(self, doc_path, patch):
        assert_error(apply_json_patch(doc_path, patch), "path")


class TestValidationErrors:
    @pytest.mark.parametrize("patch", [
        '[{"op": "add", "path": "/children/newchild", "value": {"label": "No ID", "type": "Doc"}}]',
        '[{"op": "add", "path": "/children/newchild", "value": {"id": "new", "type": "Doc"}}]',
        '[{"op": "add", "path": "/children/newchild", "value": {"id": "new", "label": "Test", "type": "InvalidType"}}]',
        '[{"op": "replace", "path": "/metadata", "value": "should be object"}]',
        '[{"op": "replace", "path": "/id", "value": null}]',
    ])
    def test_invalid_document_data(self, doc_path, patch):
        assert_error(apply_json_patch(doc_path, patch), "validation")


class TestEdgeCases:
    def test_empty_patch_array(self, doc_path):
        assert apply_json_patch(doc_path, '[]') is None

    def test_re_render_only(self, doc_path):
        assert apply_json_patch(doc_path, None) is None

    def test_valid_add_operation(self, doc_path):
        patch = '[{"op": "add", "path": "/children/newchild", "value": {"id": "new", "label": "New Child", "type": "Doc"}}]'
        assert apply_json_patch(doc_path, patch) is None

    def test_valid_replace_operation(self, doc_path):
        patch = '[{"op": "replace", "path": "/label", "value": "Updated Label"}]'
        assert apply_json_patch(doc_path, patch) is None
