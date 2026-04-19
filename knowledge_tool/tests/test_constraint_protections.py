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
    """Test Feature-level protection against updating constraint cmd when fails_count > 0.

    The lock lives in Feature.protect_proven_constraints_from_removal (feature_model.py),
    so these tests drive Feature.model_validate. Description is intentionally not locked —
    it's documentation and can be edited freely.
    """

    def test_cmd_update_allowed_with_no_failure_history(self):
        """cmd can change when constraint is unverified (fails_count=0)."""
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
                            "fails_count": 0,
                        }
                    },
                }
            },
        }

        new_feature = {
            "id": "f1",
            "description": "Test",
            "constraints": {
                "c1": {
                    "id": "c1",
                    "cmd": "echo new",
                    "description": "Test",
                }
            },
        }

        feature = Feature.model_validate(new_feature, context={"original_doc": original_doc})
        assert feature.constraints["c1"].cmd == "echo new"

    def test_cmd_update_blocked_with_failure_history(self):
        """cmd changes are blocked once constraint is verified (fails_count > 0)."""
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
                            "fails_count": 1,
                        }
                    },
                }
            },
        }

        new_feature = {
            "id": "f1",
            "description": "Test",
            "constraints": {
                "c1": {
                    "id": "c1",
                    "cmd": "echo modified",
                    "description": "Test",
                    "fails_count": 1,
                }
            },
        }

        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(new_feature, context={"original_doc": original_doc})

        error_msg = str(exc_info.value)
        assert "c1" in error_msg
        assert "cmd" in error_msg
        assert "fails_count=1" in error_msg

    def test_description_update_allowed_with_failure_history(self):
        """Description is not locked — it's documentation, safe to update even when verified."""
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
                            "fails_count": 1,
                        }
                    },
                }
            },
        }

        new_feature = {
            "id": "f1",
            "description": "Test",
            "constraints": {
                "c1": {
                    "id": "c1",
                    "cmd": "test",
                    "description": "Modified description",
                    "fails_count": 1,
                }
            },
        }

        feature = Feature.model_validate(new_feature, context={"original_doc": original_doc})
        assert feature.constraints["c1"].description == "Modified description"

    def test_other_fields_updatable_with_failure_history(self):
        """Non-cmd fields (e.g. timeout) remain editable when constraint is verified."""
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
                            "timeout": 30,
                            "fails_count": 1,
                        }
                    },
                }
            },
        }

        new_feature = {
            "id": "f1",
            "description": "Test",
            "constraints": {
                "c1": {
                    "id": "c1",
                    "cmd": "test",
                    "description": "Test",
                    "timeout": 120,
                    "fails_count": 1,
                }
            },
        }

        feature = Feature.model_validate(new_feature, context={"original_doc": original_doc})
        assert feature.constraints["c1"].timeout == 120


class TestFailsCountTamperingProtection:
    """Model-level guard: any fails_count change through the user path is rejected.

    The user path passes context={'original_doc': ...}; the admin path (the
    checker's direct write) does not pass context, so the guard returns early
    and lets the 0 → 1 transition through. Tests here exercise the user path.
    """

    def test_setting_fails_count_on_unverified_constraint_is_blocked(self):
        """0 → N smuggling on an existing constraint via the model path must raise."""
        original_doc = {
            "type": "Spec",
            "features": {
                "f1": {
                    "id": "f1",
                    "description": "Test feature",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "echo test",
                            "description": "Unverified constraint",
                            "fails_count": 0,
                        }
                    },
                }
            },
        }

        tampered = {
            "id": "f1",
            "description": "Test feature",
            "constraints": {
                "c1": {
                    "id": "c1",
                    "cmd": "echo test",
                    "description": "Unverified constraint",
                    "fails_count": 5,
                }
            },
        }

        with pytest.raises(ValueError) as exc_info:
            Feature.model_validate(tampered, context={"original_doc": original_doc})

        error_msg = str(exc_info.value)
        assert "fails_count" in error_msg
        assert "c1" in error_msg


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


class TestFeatureRemovalProtection:
    """Test protection against removing features containing verified constraints."""

    def test_feature_removal_allowed_without_constraints(self):
        """Test that feature can be removed if it has no constraints."""
        original_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Feature with no constraints"
                    # No constraints
                }
            }
        }

        new_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {}  # f1 removed
        }

        # Should succeed - feature has no constraints
        spec = Spec.model_validate(
            new_doc,
            context={"original_doc": original_doc}
        )
        assert spec.features is not None
        assert len(spec.features) == 0

    def test_feature_removal_allowed_with_unverified_constraints(self):
        """Test that feature can be removed if all constraints are unverified."""
        original_doc = {
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
                            "description": "Unverified",
                            "fails_count": 0  # Unverified
                        }
                    }
                }
            }
        }

        new_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {}  # f1 removed
        }

        # Should succeed - feature constraints are unverified
        spec = Spec.model_validate(
            new_doc,
            context={"original_doc": original_doc}
        )
        assert spec.features is not None
        assert len(spec.features) == 0

    def test_feature_removal_blocked_with_verified_constraint(self):
        """Test that feature removal is blocked if it contains verified constraints."""
        original_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "critical_feature": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "critical_feature",
                    "description": "Feature with proven constraint",
                    "constraints": {
                        "proven_constraint": {
                            "id": "proven_constraint",
                            "cmd": "test -f /tmp/critical",
                            "description": "Critical constraint",
                            "fails_count": 2  # Verified/proven
                        }
                    }
                }
            }
        }

        new_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {}  # critical_feature removed
        }

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            Spec.model_validate(
                new_doc,
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "Cannot remove feature" in error_msg
        assert "critical_feature" in error_msg
        assert "proven_constraint" in error_msg
        assert "fails_count=2" in error_msg

    def test_feature_removal_blocked_with_mixed_constraints(self):
        """Test that feature removal is blocked if it has ANY verified constraint, even with unverified ones."""
        original_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "f1": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f1",
                    "description": "Mixed constraints",
                    "constraints": {
                        "unverified_c": {
                            "id": "unverified_c",
                            "cmd": "echo new",
                            "description": "New constraint",
                            "fails_count": 0  # Unverified
                        },
                        "verified_c": {
                            "id": "verified_c",
                            "cmd": "echo old",
                            "description": "Proven constraint",
                            "fails_count": 1  # Verified - blocks removal
                        }
                    }
                }
            }
        }

        new_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {}  # f1 removed
        }

        # Should raise ValueError because of verified_c
        with pytest.raises(ValueError) as exc_info:
            Spec.model_validate(
                new_doc,
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "Cannot remove feature" in error_msg
        assert "f1" in error_msg
        assert "verified_c" in error_msg

    def test_multiple_features_removal_with_one_verified(self):
        """Test that removal is blocked when any removed feature has verified constraints."""
        original_doc = {
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
                    "constraints": {}
                },
                "f2": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "f2",
                    "description": "Feature 2",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "test",
                            "description": "Verified",
                            "fails_count": 1
                        }
                    }
                }
            }
        }

        new_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {}  # Both f1 and f2 removed
        }

        # Should raise error for f2
        with pytest.raises(ValueError) as exc_info:
            Spec.model_validate(
                new_doc,
                context={"original_doc": original_doc}
            )

        error_msg = str(exc_info.value)
        assert "f2" in error_msg

    def test_other_features_can_be_modified_when_some_protected(self):
        """Test that other features can be modified even if one has verified constraints."""
        original_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "safe_feature": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "safe_feature",
                    "description": "No verified constraints",
                    "constraints": {}
                },
                "protected_feature": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "protected_feature",
                    "description": "Has verified constraint",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "test",
                            "description": "Verified",
                            "fails_count": 1
                        }
                    }
                }
            }
        }

        new_doc = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test",
            "features": {
                "safe_feature": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "safe_feature",
                    "description": "Modified description",
                    "constraints": {}
                },
                "protected_feature": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "protected_feature",
                    "description": "Has verified constraint",
                    "constraints": {
                        "c1": {
                            "id": "c1",
                            "cmd": "test",
                            "description": "Verified",
                            "fails_count": 1
                        }
                    }
                }
            }
        }

        # Should succeed - safe_feature is modified, protected_feature is preserved
        spec = Spec.model_validate(
            new_doc,
            context={"original_doc": original_doc}
        )
        assert spec.features is not None
        assert len(spec.features) == 2
        assert spec.features["safe_feature"].description == "Modified description"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
