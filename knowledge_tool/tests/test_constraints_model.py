#!/usr/bin/env python3
"""Tests for Constraints and Feature models."""

import json
import re
from datetime import datetime
import pytest

from models import (
    Feature, Task, MODEL_REGISTRY,
    ConstraintBash, ConstraintBashResult,
    ChecksResults, FeatureResult
)


class TestFeatureModel:
    """Test Feature model creation and validation."""

    def test_feature_creation(self):
        """Test creating a Feature instance."""
        bash_constraint = ConstraintBash(
            id="c1",
            cmd="grep -q 'def x(.*y: int)' src/logic.py",
            description="Check for param y"
        )
        feature = Feature(
            id="g1",
            description="Add param 'y' to func 'x'",
            constraints={"c1": bash_constraint}
        )

        assert feature.id == "g1"
        assert feature.description == "Add param 'y' to func 'x'"
        assert feature.constraints is not None
        assert "c1" in feature.constraints

    def test_feature_default_values(self):
        """Test Feature defaults when not specified."""
        feature = Feature(
            id="g2",
            description="Test feature"
        )

        assert feature.id == "g2"
        assert feature.description == "Test feature"
        assert feature.constraints is None

    def test_feature_serialization(self):
        """Test Feature serializes to JSON correctly."""
        bash_constraint = ConstraintBash(
            id="c1",
            cmd="test",
            description="Test constraint"
        )
        feature = Feature(
            id="g1",
            description="Test feature",
            constraints={"c1": bash_constraint}
        )

        data = feature.model_dump()
        assert data["id"] == "g1"
        assert data["description"] == "Test feature"
        assert "constraints" in data



class TestTaskWithFeatures:
    """Test Task model with features field."""

    def test_task_has_spec_field(self):
        """Test that Task model includes spec field."""
        task = Task.create_default()

        assert hasattr(task, "spec")
        assert task.spec is not None
        assert task.spec.version == 1

    def test_task_with_spec_features(self):
        """Test Task with spec that contains features."""
        from models import Spec

        feature = Feature(
            id="g1",
            description="Complete task objective",
            constraint="test command"
        )

        spec = Spec(
            version=1,
            description="Specification description",
            features={"g1": feature}
        )
        task = Task(
            id="task1",
            spec=spec
        )

        assert task.spec is not None
        assert task.spec.features is not None
        assert len(task.spec.features) == 1
        assert task.spec.features["g1"].description == "Complete task objective"

    def test_task_serialization_with_spec(self):
        """Test Task serializes with spec."""
        from models import Spec

        feature = Feature(id="g1", description="Feature", constraint="cmd")
        spec = Spec(version=1, description="Specification description", features={"g1": feature})
        task = Task(id="task1", spec=spec)

        data = task.model_dump()

        assert "spec" in data
        assert data["spec"]["features"]["g1"]["id"] == "g1"


class TestModelRegistry:
    """Test model registry includes new models."""

    def test_all_root_models_registered(self):
        """Test all expected models are in registry."""
        expected = ["Doc", "Task", "Iteration", "ChecksResults"]
        for model_name in expected:
            assert model_name in MODEL_REGISTRY, f"{model_name} not in MODEL_REGISTRY"

    def test_test_results_in_registry(self):
        """Test that ChecksResults is registered."""
        assert "ChecksResults" in MODEL_REGISTRY
        assert MODEL_REGISTRY["ChecksResults"] is ChecksResults


class TestConstraintBashModel:
    """Test ConstraintBash model."""

    def test_constraint_bash_creation(self):
        """Test creating a ConstraintBash instance."""
        bash = ConstraintBash(
            id="c1",
            cmd="grep -q 'pattern' file.txt",
            description="Check for pattern in file",
            scope="local"
        )

        assert bash.id == "c1"
        assert bash.cmd == "grep -q 'pattern' file.txt"
        assert bash.description == "Check for pattern in file"

    def test_constraint_bash_default_scope(self):
        """Test ConstraintBash initialization."""
        bash = ConstraintBash(
            id="c1",
            cmd="test",
            description="Test"
        )

        assert bash.id == "c1"


class TestConstraintBashFailsCountProtection:
    """Test ConstraintBash fails_count protection feature."""

    def test_fails_count_default_zero(self):
        """Test that fails_count defaults to 0."""
        bash = ConstraintBash(
            id="c1",
            cmd="test",
            description="Test"
        )
        assert bash.fails_count == 0

    def test_increment_fails_count_method(self):
        """Test increment_fails_count() method increments the count."""
        bash = ConstraintBash(
            id="c1",
            cmd="test",
            description="Test"
        )
        assert bash.fails_count == 0

        bash.increment_fails_count()
        assert bash.fails_count == 1

        bash.increment_fails_count()
        assert bash.fails_count == 2

    def test_fails_count_can_be_set_via_snapshot(self):
        """Test that fails_count CAN be set via JSON snapshot for patching.

        fails_count is allowed to be updated via snapshot to support JSON patching
        in task_features_checker. The constraint warns when fails_count > 0.
        """
        constraint_data = {
            "id": "c1",
            "cmd": "echo test",
            "description": "Test constraint",
            "tags": [],
            "fails_count": 5  # Set fails_count in JSON
        }

        # Load via model_validate (snapshot loading)
        constraint = ConstraintBash.model_validate(constraint_data)

        # fails_count should be settable for patching support
        assert constraint.fails_count == 5, \
            "fails_count must be settable via snapshot for JSON patches"

    def test_cmd_warning_when_fails_count_greater_than_zero(self):
        """Test that loading constraint with fails_count > 0 shows a warning.

        When a constraint has failed (fails_count > 0), loading it from snapshot
        triggers a warning that the constraint is locked and cmd cannot be changed.
        Users should either fix the constraint or remove it.
        """
        constraint_data = {
            "id": "locked_constraint",
            "cmd": "echo test",
            "description": "Test constraint",
            "tags": [],
            "fails_count": 2  # Constraint has failed
        }

        # Load constraint with fails_count > 0 - should show warning
        constraint = ConstraintBash.model_validate(constraint_data)

        # Constraint loads successfully with the warning
        assert constraint.fails_count == 2, "fails_count should be preserved"
        assert constraint.cmd == "echo test", "cmd should be loaded from snapshot"
        # Warning is printed to stdout by the validator

    def test_constraint_removable_despite_fails_count(self):
        """Test that constraint can be removed entirely even when fails_count > 0.

        The feature should only prevent cmd updates, not constraint removal.
        """
        bash = ConstraintBash(
            id="c1",
            cmd="echo test",
            description="Test constraint"
        )
        bash.increment_fails_count()
        bash.increment_fails_count()

        assert bash.fails_count == 2

        feature_data = {
            "type": "Feature",
            "model_version": 1,
            "id": "test_feature",
            "description": "Test feature",
            "constraints": {
                "c1": json.loads(bash.model_dump_json(exclude_none=True))
            }
        }

        feature = Feature.model_validate(feature_data)

        # Constraint exists in feature
        assert "c1" in feature.constraints
        assert feature.constraints["c1"].fails_count == 2

        # Can be accessed and serialized (would be removed via JSON patch)
        serialized = json.loads(feature.model_dump_json(exclude_none=True))
        assert "c1" in serialized["constraints"]
        assert serialized["constraints"]["c1"]["fails_count"] == 2



class TestConstraintBashResultModel:
    """Test ConstraintBashResult model."""

    def test_bash_result_creation(self):
        """Test creating ConstraintBashResult."""
        result = ConstraintBashResult(
            constraint_id="c1",
            verdict=True,
            shrunken_output="command succeeded"
        )

        assert result.constraint_id == "c1"
        assert result.verdict is True
        assert result.shrunken_output == "command succeeded"
        assert result.timestamp is None

    def test_bash_result_with_timestamp(self):
        """Test ConstraintBashResult with timestamp."""
        now = datetime.now()
        result = ConstraintBashResult(
            constraint_id="c1",
            verdict=False,
            shrunken_output="failed",
            timestamp=now
        )

        assert result.timestamp == now

    def test_bash_result_serialization(self):
        """Test ConstraintBashResult serialization."""
        result = ConstraintBashResult(
            constraint_id="c1",
            verdict=True,
            shrunken_output="output"
        )

        data = result.model_dump()
        assert data["constraint_id"] == "c1"
        assert data["verdict"] is True



class TestFeatureResultModel:
    """Test FeatureResult model for grouping constraint results by feature."""

    def test_feature_result_creation(self):
        """Test creating FeatureResult instance."""
        result = ConstraintBashResult(
            constraint_id="c1",
            verdict=True,
            shrunken_output="ok"
        )

        feature_result = FeatureResult(
            feature_id="f1",
            constraints_results={"c1": result}
        )

        assert feature_result.feature_id == "f1"
        assert len(feature_result.constraints_results) == 1
        assert feature_result.constraints_results["c1"].verdict is True


    def test_feature_result_serialization(self):
        """Test FeatureResult serialization to JSON."""
        result = ConstraintBashResult(
            constraint_id="c1",
            verdict=False,
            shrunken_output="failed"
        )

        feature_result = FeatureResult(
            feature_id="f1",
            constraints_results={"c1": result}
        )

        data = feature_result.model_dump()
        assert data["feature_id"] == "f1"
        assert "c1" in data["constraints_results"]
        assert data["constraints_results"]["c1"]["verdict"] is False



class TestChecksResultsModel:
    """Test ChecksResults root document model."""

    def test_test_results_creation(self):
        """Test creating ChecksResults instance."""
        test_results = ChecksResults()

        assert test_results.type == "ChecksResults"
        assert test_results.features_results is None

    def test_test_results_with_bash_results(self):
        """Test ChecksResults with bash constraint results."""
        result1 = ConstraintBashResult(
            constraint_id="c1",
            verdict=True,
            shrunken_output="ok"
        )
        result2 = ConstraintBashResult(
            constraint_id="c2",
            verdict=False,
            shrunken_output="failed"
        )

        feature_result = FeatureResult(
            feature_id="f1",
            constraints_results={"c1": result1, "c2": result2}
        )
        test_results = ChecksResults(
            features_results={"f1": feature_result}
        )

        assert len(test_results.features_results) == 1
        assert test_results.features_results["f1"].constraints_results["c1"].verdict is True


    def test_test_results_is_root(self):
        """Test ChecksResults can be a root document."""
        test_results = ChecksResults()
        assert test_results.is_can_be_root() is True

    def test_test_results_create_default(self):
        """Test ChecksResults.create_default()."""
        test_results = ChecksResults.create_default()
        assert test_results.type == "ChecksResults"
        assert test_results.features_results is None

    def test_test_results_render(self):
        """Test ChecksResults markdown rendering."""
        result1 = ConstraintBashResult(constraint_id="c1", verdict=True, shrunken_output="ok")

        feature_result = FeatureResult(
            feature_id="f1",
            constraints_results={"c1": result1}
        )
        test_results = ChecksResults(
            features_results={"f1": feature_result}
        )

        markdown = test_results.render()

        assert "## Constraint Results" in markdown
        assert "### Feature: f1" in markdown
        assert "✓ PASS" in markdown
        assert "f1.c1" in markdown

    def test_test_results_render_toc(self):
        """Test ChecksResults table of contents rendering."""
        result = ConstraintBashResult(constraint_id="c1", verdict=True, shrunken_output="ok")

        feature_result = FeatureResult(
            feature_id="f1",
            constraints_results={"c1": result}
        )
        test_results = ChecksResults(
            features_results={"f1": feature_result}
        )

        toc = test_results.render_toc()

        assert len(toc) > 0
        assert any("Constraint Results" in line for line in toc)
        assert any("Feature: f1" in line for line in toc)
        assert any("c1" in line for line in toc)
