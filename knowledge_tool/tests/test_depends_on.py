#!/usr/bin/env python3
"""Tests for Feature depends_on field validation."""

import pytest
from models import Feature, Spec


class TestDependsOnValidation:
    """Test depends_on field validation."""

    def test_depends_on_with_valid_references(self):
        """Test that depends_on accepts valid feature references."""
        original_doc = {
            "type": "Spec",
            "features": {
                "feature_a": {
                    "id": "feature_a",
                    "description": "Feature A"
                },
                "feature_b": {
                    "id": "feature_b",
                    "description": "Feature B",
                    "depends_on": ["feature_a"]
                },
                "feature_c": {
                    "id": "feature_c",
                    "description": "Feature C",
                    "depends_on": ["feature_a", "feature_b"]
                }
            }
        }

        # Should not raise - all references are valid
        feature_b = Feature.model_validate(
            original_doc["features"]["feature_b"],
            context={"original_doc": original_doc}
        )
        assert feature_b.depends_on == ["feature_a"]

        feature_c = Feature.model_validate(
            original_doc["features"]["feature_c"],
            context={"original_doc": original_doc}
        )
        assert feature_c.depends_on == ["feature_a", "feature_b"]

    def test_depends_on_with_invalid_reference(self):
        """Test that depends_on rejects invalid feature references."""
        original_doc = {
            "type": "Spec",
            "features": {
                "feature_a": {
                    "id": "feature_a",
                    "description": "Feature A"
                },
                "feature_b": {
                    "id": "feature_b",
                    "description": "Feature B",
                    "depends_on": ["nonexistent_feature"]
                }
            }
        }

        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(
                original_doc["features"]["feature_b"],
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "depends on 'nonexistent_feature'" in error_msg
        assert "does not exist" in error_msg

    def test_depends_on_empty_list(self):
        """Test that empty depends_on list is valid."""
        feature_data = {
            "id": "feature_a",
            "description": "Feature A",
            "depends_on": []
        }

        feature = Feature.model_validate(feature_data)
        assert feature.depends_on == []

    def test_depends_on_none(self):
        """Test that depends_on can be None (optional field)."""
        feature_data = {
            "id": "feature_a",
            "description": "Feature A"
        }

        feature = Feature.model_validate(feature_data)
        assert feature.depends_on is None

    def test_depends_on_with_non_list_raises_error(self):
        """Test that depends_on must be a list."""
        feature_data = {
            "id": "feature_a",
            "description": "Feature A",
            "depends_on": "feature_b"  # String instead of list
        }

        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(feature_data)

        assert "depends_on must be a list" in str(exc_info.value)

    def test_depends_on_with_non_string_elements_raises_error(self):
        """Test that depends_on must contain only strings."""
        feature_data = {
            "id": "feature_a",
            "description": "Feature A",
            "depends_on": ["feature_b", 123]  # Number instead of string
        }

        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(feature_data)

        assert "Feature IDs in depends_on must be strings" in str(exc_info.value)

    def test_depends_on_with_empty_string_raises_error(self):
        """Test that depends_on cannot contain empty strings."""
        feature_data = {
            "id": "feature_a",
            "description": "Feature A",
            "depends_on": ["feature_b", ""]  # Empty string
        }

        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(feature_data)

        assert "cannot be empty strings" in str(exc_info.value)

    def test_depends_on_without_context(self):
        """Test that depends_on is still validated (basic checks) without context."""
        # Basic validation should work without context
        feature_data = {
            "id": "feature_a",
            "description": "Feature A",
            "depends_on": ["feature_b"]
        }

        # Should not raise - basic validation passes
        feature = Feature.model_validate(feature_data)
        assert feature.depends_on == ["feature_b"]
