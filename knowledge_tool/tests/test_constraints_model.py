#!/usr/bin/env python3
"""Tests for Constraints and Feature models."""

import json
import re
from datetime import datetime
import pytest

from models import (
    Feature, Constraints, Task, MODEL_REGISTRY,
    ConstraintBash, ConstraintPrompt, ConstraintBashResult, ConstraintPromptResult,
    Constraint, Tests
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


class TestConstraintsModel:
    """Test Constraints model creation and rendering."""

    def test_constraints_creation(self):
        """Test creating a Constraints instance."""
        constraints = Constraints()

        assert constraints.type == "Constraints"
        assert constraints.features is None
        assert constraints.metadata == {}

    def test_constraints_with_features(self):
        """Test Constraints with features."""
        feature1 = Feature(
            id="g1",
            description="First feature",
            constraint="cmd1"
        )
        feature2 = Feature(
            id="g2",
            description="Second feature",
            constraint="cmd2"
        )

        constraints = Constraints(
            features={"g1": feature1, "g2": feature2},
            metadata={"version": "1.0"}
        )

        assert len(constraints.features) == 2
        assert constraints.features["g1"].description == "First feature"
        assert constraints.metadata["version"] == "1.0"

    def test_constraints_is_root(self):
        """Test that Constraints can be a root document."""
        constraints = Constraints()
        assert constraints.is_can_be_root() is True

    def test_constraints_render(self):
        """Test Constraints rendering to markdown."""
        bash_constraint = ConstraintBash(
            id="c1",
            cmd="grep -q 'feature_x' src/main.py",
            description="Check for feature_x"
        )
        feature = Feature(
            id="g1",
            description="Add feature X",
            constraints={"c1": bash_constraint}
        )

        constraints = Constraints(
            features={"g1": feature},
            metadata={"created": "2025-03-08"}
        )

        markdown = constraints.render()

        assert "## Features" in markdown
        assert "g1: Add feature X" in markdown
        assert "grep -q 'feature_x' src/main.py" in markdown
        assert "## Metadata" in markdown

    def test_constraints_render_toc(self):
        """Test Constraints table of contents rendering."""
        feature1 = Feature(id="g1", description="Feature 1", constraint="cmd1")
        feature2 = Feature(id="g2", description="Feature 2", constraint="cmd2")

        constraints = Constraints(features={"g1": feature1, "g2": feature2})
        toc = constraints.render_toc()

        assert len(toc) > 0
        assert any("Features" in line for line in toc)
        assert any("g1" in line for line in toc)
        assert any("g2" in line for line in toc)

    def test_constraints_default_factory(self):
        """Test Constraints.create_default()."""
        constraints = Constraints.create_default()

        assert constraints.type == "Constraints"
        assert constraints.features is None


class TestTaskWithFeatures:
    """Test Task model with features field."""

    def test_task_has_features_field(self):
        """Test that Task model includes features field."""
        task = Task.create_default()

        assert hasattr(task, "features")
        assert task.features is None

    def test_task_with_features(self):
        """Test Task with features populated."""
        from models import Doc

        feature = Feature(
            id="g1",
            description="Complete task objective",
            constraint="test command"
        )

        plan = Doc(id="plan", label="Plan")
        task = Task(
            id="task1",
            plan=plan,
            features={"g1": feature}
        )

        assert task.features is not None
        assert len(task.features) == 1
        assert task.features["g1"].description == "Complete task objective"

    def test_task_serialization_with_features(self):
        """Test Task serializes with features."""
        from models import Doc

        feature = Feature(id="g1", description="Feature", constraint="cmd")
        plan = Doc(id="plan", label="Plan")
        task = Task(id="task1", plan=plan, features={"g1": feature})

        data = task.model_dump()

        assert "features" in data
        assert data["features"]["g1"]["id"] == "g1"


class TestModelRegistry:
    """Test model registry includes new models."""

    def test_constraints_in_registry(self):
        """Test that Constraints is registered."""
        assert "Constraints" in MODEL_REGISTRY
        assert MODEL_REGISTRY["Constraints"] is Constraints

    def test_all_root_models_registered(self):
        """Test all expected models are in registry."""
        expected = ["Doc", "Constraints", "Task", "Iteration", "Tests"]
        for model_name in expected:
            assert model_name in MODEL_REGISTRY, f"{model_name} not in MODEL_REGISTRY"

    def test_tests_in_registry(self):
        """Test that Tests is registered."""
        assert "Tests" in MODEL_REGISTRY
        assert MODEL_REGISTRY["Tests"] is Tests


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
        assert bash.scope == "local"

    def test_constraint_bash_default_scope(self):
        """Test ConstraintBash default scope."""
        bash = ConstraintBash(
            id="c1",
            cmd="test",
            description="Test"
        )

        assert bash.scope == "local"


class TestConstraintPromptModel:
    """Test ConstraintPrompt model with regex validation."""

    def test_constraint_prompt_creation(self):
        """Test creating a ConstraintPrompt instance."""
        prompt = ConstraintPrompt(
            id="p1",
            prompt="Is the code correct?",
            verdict_expect_rule="(yes|true|correct)",
            description="Check code correctness",
            scope="global"
        )

        assert prompt.id == "p1"
        assert prompt.prompt == "Is the code correct?"
        assert prompt.verdict_expect_rule == "(yes|true|correct)"
        assert prompt.scope == "global"

    def test_constraint_prompt_lazy_regex_compilation(self):
        """Test regex is lazily compiled on first access."""
        prompt = ConstraintPrompt(
            id="p1",
            prompt="Test",
            verdict_expect_rule="test_.*",
            description="Test prompt"
        )

        # Regex should not be compiled yet
        assert prompt._compiled_regex is None

        # Access compiled regex
        compiled = prompt.get_compiled_regex()
        assert compiled is not None
        assert isinstance(compiled, type(re.compile("")))

        # Second access returns cached version
        compiled2 = prompt.get_compiled_regex()
        assert compiled is compiled2  # Same object

    def test_constraint_prompt_regex_validation(self):
        """Test invalid regex is rejected."""
        with pytest.raises(ValueError, match="Invalid regex"):
            ConstraintPrompt(
                id="p1",
                prompt="Test",
                verdict_expect_rule="[invalid(regex",  # Invalid regex
                description="Test"
            )

    def test_constraint_prompt_regex_matching(self):
        """Test compiled regex matching."""
        prompt = ConstraintPrompt(
            id="p1",
            prompt="What is status?",
            verdict_expect_rule="(pass|success|ok)",
            description="Check status"
        )

        regex = prompt.get_compiled_regex()
        assert regex.search("pass") is not None
        assert regex.search("success") is not None
        assert regex.search("fail") is None


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


class TestConstraintPromptResultModel:
    """Test ConstraintPromptResult model."""

    def test_prompt_result_creation(self):
        """Test creating ConstraintPromptResult."""
        result = ConstraintPromptResult(
            constraint_id="p1",
            verdict="pass",
            short_answer="Yes, it's correct."
        )

        assert result.constraint_id == "p1"
        assert result.verdict == "pass"
        assert result.short_answer == "Yes, it's correct."

    def test_prompt_result_with_timestamp(self):
        """Test ConstraintPromptResult with timestamp."""
        now = datetime.now()
        result = ConstraintPromptResult(
            constraint_id="p1",
            verdict="success",
            short_answer="Test passed",
            timestamp=now
        )

        assert result.timestamp == now


class TestConstraintModel:
    """Test Constraint wrapper model."""

    def test_constraint_with_bash(self):
        """Test Constraint with bash constraint."""
        bash = ConstraintBash(
            id="c1",
            cmd="test -f file.txt",
            description="File exists"
        )

        constraint = Constraint(
            id="const1",
            scope="local",
            constraint_bash=bash
        )

        assert constraint.constraint_bash is not None
        assert constraint.constraint_prompt is None

    def test_constraint_with_prompt(self):
        """Test Constraint with prompt constraint."""
        prompt = ConstraintPrompt(
            id="p1",
            prompt="Is valid?",
            verdict_expect_rule="yes|true",
            description="Validation"
        )

        constraint = Constraint(
            id="const1",
            scope="local",
            constraint_prompt=prompt
        )

        assert constraint.constraint_bash is None
        assert constraint.constraint_prompt is not None

    def test_constraint_rejects_both_set(self):
        """Test Constraint rejects both bash and prompt."""
        bash = ConstraintBash(id="c1", cmd="test", description="test")
        prompt = ConstraintPrompt(
            id="p1", prompt="test", verdict_expect_rule="t.*", description="test"
        )

        with pytest.raises(ValueError, match="Exactly one"):
            Constraint(
                id="const1",
                scope="local",
                constraint_bash=bash,
                constraint_prompt=prompt
            )

    def test_constraint_rejects_neither_set(self):
        """Test Constraint rejects neither bash nor prompt."""
        with pytest.raises(ValueError, match="Exactly one"):
            Constraint(id="const1", scope="local")


class TestTestsModel:
    """Test Tests root document model."""

    def test_tests_creation(self):
        """Test creating Tests instance."""
        tests = Tests()

        assert tests.type == "Tests"
        assert tests.constraints_results is None

    def test_tests_with_bash_tests(self):
        """Test Tests with bash constraint results."""
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

        tests = Tests(
            constraints_results={"c1": result1, "c2": result2}
        )

        assert len(tests.constraints_results) == 2
        assert tests.constraints_results["c1"].verdict is True

    def test_tests_with_prompt_tests(self):
        """Test Tests with prompt constraint results."""
        result = ConstraintPromptResult(
            constraint_id="p1",
            verdict="success",
            short_answer="Passed"
        )

        tests = Tests(
            constraints_results={"p1": result}
        )

        assert tests.constraints_results["p1"].verdict == "success"

    def test_tests_is_root(self):
        """Test Tests can be a root document."""
        tests = Tests()
        assert tests.is_can_be_root() is True

    def test_tests_create_default(self):
        """Test Tests.create_default()."""
        tests = Tests.create_default()
        assert tests.type == "Tests"
        assert tests.constraints_results is None

    def test_tests_render(self):
        """Test Tests markdown rendering."""
        result1 = ConstraintBashResult(constraint_id="c1", verdict=True, shrunken_output="ok")
        result2 = ConstraintPromptResult(constraint_id="p1", verdict="pass", short_answer="Yes")

        tests = Tests(
            constraints_results={"c1": result1, "p1": result2}
        )

        markdown = tests.render()

        assert "## Constraint Results" in markdown
        assert "### Bash Constraints" in markdown
        assert "### Prompt Constraints" in markdown
        assert "✓ PASS" in markdown
        assert "c1" in markdown
        assert "p1" in markdown

    def test_tests_render_toc(self):
        """Test Tests table of contents rendering."""
        result = ConstraintBashResult(constraint_id="c1", verdict=True, shrunken_output="ok")

        tests = Tests(
            constraints_results={"c1": result}
        )

        toc = tests.render_toc()

        assert len(toc) > 0
        assert any("Constraint Results" in line for line in toc)
        assert any("Bash Constraints" in line for line in toc)
