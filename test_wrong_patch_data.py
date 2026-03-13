#!/usr/bin/env python3
"""Comprehensive test to verify knowledge_tool behavior with wrong patch data."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "knowledge_tool")
from patch_knowledge_document import apply_json_patch


def create_temp_doc():
    """Create a test document."""
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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        return f.name


def test_scenario(title, doc_path, patch, expected_error_contains=None):
    """Test a scenario and print results."""
    print(f"\n{'='*80}")
    print(f"TEST: {title}")
    print(f"{'='*80}")
    if patch:
        print(f"Patch input: {patch[:100]}..." if len(patch) > 100 else f"Patch input: {patch}")
    else:
        print(f"Patch input: None")

    result = apply_json_patch(doc_path, patch)

    if result is None:
        print("✓ SUCCESS - No error returned")
        if expected_error_contains:
            print(f"⚠ WARNING: Expected error containing '{expected_error_contains}' but got success")
        return True
    else:
        print(f"✗ ERROR DETECTED\n")
        error_dict = result.model_dump(exclude_none=True)

        # Print key fields
        print(f"Error: {error_dict['error']}")
        if 'hint' in error_dict:
            hint = error_dict['hint']
            # Truncate long hints
            if len(hint) > 300:
                print(f"Hint (truncated): {hint[:300]}...")
            else:
                print(f"Hint: {hint}")

        if 'example' in error_dict:
            print(f"Examples provided: {len(error_dict['example'])} operation(s)")

        if 'parent_path' in error_dict:
            print(f"Parent path: {error_dict['parent_path']}")

        if 'existing_children' in error_dict:
            print(f"Existing children: {error_dict['existing_children']}")

        if 'details' in error_dict:
            print(f"Validation details: {error_dict['details']}")

        # Check if error contains expected text
        if expected_error_contains:
            if expected_error_contains.lower() in error_dict['error'].lower():
                print(f"✓ Error contains expected: '{expected_error_contains}'")
                return True
            else:
                print(f"✗ Error missing expected: '{expected_error_contains}'")
                return False

        return True


# Create test document
doc_path = create_temp_doc()
passed = 0
failed = 0

try:
    # ==================== JSON SYNTAX ERRORS ====================
    print(f"\n\n{'#'*80}")
    print("# SECTION 1: JSON SYNTAX ERRORS")
    print(f"{'#'*80}")

    if test_scenario(
        "Completely invalid JSON string",
        doc_path,
        "this is not json at all {[ ]",
        expected_error_contains="syntax"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Valid JSON but not an array (object instead)",
        doc_path,
        '{"op": "add", "path": "/label", "value": "test"}',
        expected_error_contains="array"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Valid JSON but not an array (string instead)",
        doc_path,
        '"not an array"',
        expected_error_contains="array"
    ):
        passed += 1
    else:
        failed += 1

    # ==================== PATCH STRUCTURE ERRORS ====================
    print(f"\n\n{'#'*80}")
    print("# SECTION 2: PATCH OPERATION STRUCTURE ERRORS")
    print(f"{'#'*80}")

    if test_scenario(
        "Missing required 'op' field",
        doc_path,
        '[{"path": "/label", "value": "test"}]',
        expected_error_contains="syntax"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Missing required 'path' field",
        doc_path,
        '[{"op": "add", "value": "test"}]',
        expected_error_contains="syntax"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Invalid operation type (not standard RFC 6902)",
        doc_path,
        '[{"op": "invalid_op", "path": "/label", "value": "test"}]',
        expected_error_contains="syntax"
    ):
        passed += 1
    else:
        failed += 1

    # ==================== PATH ERRORS ====================
    print(f"\n\n{'#'*80}")
    print("# SECTION 3: PATH ERRORS")
    print(f"{'#'*80}")

    if test_scenario(
        "Path does not exist in document",
        doc_path,
        '[{"op": "replace", "path": "/nonexistent/path", "value": "test"}]',
        expected_error_contains="path"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Try to access property of non-object (children is dict, not array)",
        doc_path,
        '[{"op": "replace", "path": "/children/0", "value": "test"}]',
        expected_error_contains="path"
    ):
        passed += 1
    else:
        failed += 1

    # ==================== VALIDATION ERRORS ====================
    print(f"\n\n{'#'*80}")
    print("# SECTION 4: PYDANTIC VALIDATION ERRORS")
    print(f"{'#'*80}")

    if test_scenario(
        "Missing required 'id' field in new child",
        doc_path,
        '[{"op": "add", "path": "/children/newchild", "value": {"label": "No ID", "type": "Doc"}}]',
        expected_error_contains="validation"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Missing required 'label' field in new child",
        doc_path,
        '[{"op": "add", "path": "/children/newchild", "value": {"id": "new", "type": "Doc"}}]',
        expected_error_contains="validation"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Invalid type value (not in allowed enum)",
        doc_path,
        '[{"op": "add", "path": "/children/newchild", "value": {"id": "new", "label": "Test", "type": "InvalidType"}}]',
        expected_error_contains="validation"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Wrong data type - string instead of object (metadata)",
        doc_path,
        '[{"op": "replace", "path": "/metadata", "value": "should be object"}]',
        expected_error_contains="validation"
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Null value for required field 'id'",
        doc_path,
        '[{"op": "replace", "path": "/id", "value": null}]',
        expected_error_contains="validation"
    ):
        passed += 1
    else:
        failed += 1

    # ==================== EDGE CASES ====================
    print(f"\n\n{'#'*80}")
    print("# SECTION 5: EDGE CASES")
    print(f"{'#'*80}")

    if test_scenario(
        "Empty patch array (should succeed)",
        doc_path,
        '[]'
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Re-render only (no patch)",
        doc_path,
        None
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Valid add operation (should succeed)",
        doc_path,
        '[{"op": "add", "path": "/children/newchild", "value": {"id": "new", "label": "New Child", "type": "Doc"}}]'
    ):
        passed += 1
    else:
        failed += 1

    if test_scenario(
        "Valid replace operation (should succeed)",
        doc_path,
        '[{"op": "replace", "path": "/label", "value": "Updated Label"}]'
    ):
        passed += 1
    else:
        failed += 1

finally:
    # Cleanup
    Path(doc_path).unlink(missing_ok=True)
    Path(doc_path).with_suffix(".md").unlink(missing_ok=True)

print(f"\n\n{'='*80}")
print("TEST SUMMARY")
print(f"{'='*80}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Total:   {passed + failed}")
print(f"{'='*80}")

sys.exit(0 if failed == 0 else 1)
