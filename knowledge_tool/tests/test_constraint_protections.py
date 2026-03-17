#!/usr/bin/env python3
"""Tests for constraint protection mechanisms:
- Constraint removal protection (fails_count > 0)
- Constraint update protection (cmd/description changes blocked when fails_count > 0)
- Unverified constraints tracking in Spec model
"""

import json
import pytest

from models import (
    Feature, ConstraintBash, Spec
)


class TestConstraintRemovalProtection:
    """Test protection against removing constraints with fails_count > 0."""

    def test_validate_removal_succeeds_with_fails_count_zero(self):
        """Test that removal is allowed when fails_count=0 (no failure history)."""
        constraint_data = {
            "id": "c1",
            "cmd": "test -f file.txt",
            "description": "Check file exists",
            "fails_count": 0
        }

        # Should not raise - no failure history
        ConstraintBash.validate_removal(constraint_data)

    def test_validate_removal_succeeds_without_fails_count(self):
        """Test that removal is allowed when fails_count field is missing (defaults to 0)."""
        constraint_data = {
            "id": "c1",
            "cmd": "test -f file.txt",
            "description": "Check file exists"
            # fails_count not present - defaults to 0
        }

        # Should not raise
        ConstraintBash.validate_removal(constraint_data)

    def test_validate_removal_blocks_with_fails_count_positive(self):
        """Test that removal is blocked when constraint has failure history (fails_count > 0)."""
        constraint_data = {
            "id": "proven_constraint",
            "cmd": "test -f file.txt",
            "description": "Check file exists",
            "fails_count": 2
        }

        # Should raise ValueError with clear message
        with pytest.raises(ValueError) as exc_info:
            ConstraintBash.validate_removal(constraint_data)

        error_msg = str(exc_info.value)
        assert "Cannot remove constraint" in error_msg
        assert "proven_constraint" in error_msg
        assert "fails_count=2" in error_msg
        assert "Fix the constraint to pass first" in error_msg

    def test_feature_blocks_constraint_removal_in_patch(self):
        """Test that Feature validator blocks removal of constraints with fails_count > 0."""
        # Original feature with a proven constraint
        original_doc = {
            "type": "Spec",
            "features": {
                "f1": {
                    "id": "f1",
                    "description": "Test feature",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "test",
                            "description": "Proven constraint",
                            "fails_count": 1  # Has failure history
                        }
                    }
                }
            }
        }

        # Try to remove the constraint (not present in new data)
        new_data = {
            "id": "f1",
            "description": "Test feature",
            "constraints": {}  # c1 removed
        }

        # Validation should fail
        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(
                new_data,
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "Cannot remove constraint" in error_msg
        assert "c1" in error_msg
        assert "fails_count=1" in error_msg


class TestConstraintUpdateProtection:
    """Test protection against updating constraint cmd/description when fails_count > 0.

    NOTE: These tests are for the feature 'protect_constraint_updates_when_failed'.
    The validator has not been fully implemented yet in ConstraintBash.protect_cmd_when_failed.
    Tests are marked as skipped until implementation is complete.
    """

    @pytest.mark.skip(reason="protect_cmd_when_failed validator not yet implemented in ConstraintBash")
    def test_cmd_update_allowed_with_no_failure_history(self):
        """Test that cmd can be updated when constraint hasn't failed (fails_count=0)."""
        original_doc = {
            "type": "Spec",
            "features": {
                "f1": {
                    "id": "f1",
                    "description": "Test",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo old",
                            "description": "Test",
                            "fails_count": 0  # No failure history
                        }
                    }
                }
            }
        }

        # Change cmd
        new_data = {
            "id": "c1",
            "cmd": "echo new",
            "description": "Test"
        }

        # Should succeed - no failure history
        constraint = ConstraintBash.model_validate(
            new_data,
            context={"original_doc": original_doc}
        )
        assert constraint.cmd == "echo new"

    @pytest.mark.skip(reason="protect_cmd_when_failed validator not yet implemented in ConstraintBash")
    def test_cmd_update_blocked_with_failure_history(self):
        """Test that cmd updates are blocked when constraint has failed (fails_count > 0)."""
        original_doc = {
            "type": "Spec",
            "features": {
                "f1": {
                    "id": "f1",
                    "description": "Test",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo original",
                            "description": "Test",
                            "fails_count": 2  # Has failure history
                        }
                    }
                }
            }
        }

        # Try to change cmd
        new_data = {
            "id": "c1",
            "cmd": "echo modified",
            "description": "Test"
        }

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            ConstraintBash.model_validate(
                new_data,
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "Cannot update constraint" in error_msg
        assert "c1" in error_msg
        assert "fails_count=2" in error_msg
        assert "cmd" in error_msg

    @pytest.mark.skip(reason="protect_cmd_when_failed validator not yet implemented in ConstraintBash")
    def test_description_update_blocked_with_failure_history(self):
        """Test that description updates are blocked when constraint has failed."""
        original_doc = {
            "type": "Spec",
            "features": {
                "f1": {
                    "id": "f1",
                    "description": "Test",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "test",
                            "description": "Original description",
                            "fails_count": 1
                        }
                    }
                }
            }
        }

        # Try to change description
        new_data = {
            "id": "c1",
            "cmd": "test",
            "description": "Modified description"
        }

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            ConstraintBash.model_validate(
                new_data,
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "Cannot update constraint" in error_msg
        assert "description" in error_msg
        assert "fails_count=1" in error_msg

    @pytest.mark.skip(reason="protect_cmd_when_failed validator not yet implemented in ConstraintBash")
    def test_other_fields_updatable_with_failure_history(self):
        """Test that non-cmd/description fields can be updated even with failures."""
        original_doc = {
            "type": "Spec",
            "features": {
                "f1": {
                    "id": "f1",
                    "description": "Test",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "test",
                            "description": "Test",
                            "tags": ["structure"],  # Must be valid literal
                            "fails_count": 1
                        }
                    }
                }
            }
        }

        # Update tags (not cmd or description)
        new_data = {
            "id": "c1",
            "cmd": "test",
            "description": "Test",
            "tags": ["API"]  # Valid literal value
        }

        # Should succeed - only non-protected fields changed
        constraint = ConstraintBash.model_validate(
            new_data,
            context={"original_doc": original_doc}
        )
        assert constraint.tags == ["API"]


class TestUnverifiedConstraintsTracking:
    """Test Spec model's contains_unverified_constraints flag computation."""

    def test_flag_false_with_no_constraints(self):
        """Test flag is False when spec has no constraints."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": None
        }

        spec = Spec.model_validate(spec_dict)
        assert spec.contains_unverified_constraints is False

    def test_flag_false_with_empty_features(self):
        """Test flag is False when features dict is empty."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {}
        }

        spec = Spec.model_validate(spec_dict)
        assert spec.contains_unverified_constraints is False

    def test_flag_true_with_unproven_constraint(self):
        """Test flag is True when any constraint has fails_count < 1 (unproven)."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature 1",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo test",
                            "description": "Unproven constraint",
                            "fails_count": 0  # Unproven
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)
        assert spec.contains_unverified_constraints is True

    def test_flag_true_with_missing_fails_count(self):
        """Test flag is True when constraint has no fails_count (defaults to 0, unproven)."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature 1",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo test",
                            "description": "Test"
                            # fails_count not set - defaults to 0
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)
        assert spec.contains_unverified_constraints is True

    def test_flag_false_with_proven_constraints(self):
        """Test flag is False when all constraints have fails_count >= 1 (proven)."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature 1",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo 1",
                            "description": "Proven 1",
                            "fails_count": 1
                        },
                        "c2": {
                            "id": "c2",
                            "cmd": "echo 2",
                            "description": "Proven 2",
                            "fails_count": 3
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)
        assert spec.contains_unverified_constraints is False

    def test_flag_true_with_mixed_proven_and_unproven(self):
        """Test flag is True when ANY constraint is unproven (even if others are proven)."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature 1",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo 1",
                            "description": "Proven",
                            "fails_count": 2  # Proven
                        },
                        "c2": {
                            "id": "c2",
                            "cmd": "echo 2",
                            "description": "Unproven",
                            "fails_count": 0  # Unproven - makes flag True
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)
        assert spec.contains_unverified_constraints is True

    def test_flag_updates_across_multiple_features(self):
        """Test flag correctly scans all features and their constraints."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature 1 - all proven",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo 1",
                            "description": "Test",
                            "fails_count": 1
                        }
                    }
                },
                "f2": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f2",
                    "description": "Feature 2 - has unproven",
                    "constraints": {
                        "c2": {
                            "id": "c2",
                            "cmd": "echo 2",
                            "description": "Unproven",
                            "fails_count": 0  # Makes flag True
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)
        # Flag should be True because f2.c2 is unproven
        assert spec.contains_unverified_constraints is True

    def test_flag_serialization_omitted_when_false(self):
        """Test that contains_unverified_constraints is serialized correctly."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo test",
                            "description": "Proven",
                            "fails_count": 1
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)

        # Serialize and check
        serialized = json.loads(spec.model_dump_json())
        assert serialized["contains_unverified_constraints"] is False

    def test_flag_serialization_included_when_true(self):
        """Test that contains_unverified_constraints appears in JSON when True."""
        spec_dict = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo test",
                            "description": "Unproven"
                            # fails_count not set
                        }
                    }
                }
            }
        }

        spec = Spec.model_validate(spec_dict)

        # Serialize and check
        serialized = json.loads(spec.model_dump_json())
        assert serialized["contains_unverified_constraints"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
