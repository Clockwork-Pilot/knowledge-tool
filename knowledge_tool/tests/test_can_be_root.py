#!/usr/bin/env python3
"""Tests for can_be_root() method on renderable models."""

import sys
from pathlib import Path
import pytest

# Add src to path for imports
_src_dir = Path(__file__).parent.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from models import Doc, Task, Iteration


class TestCanBeRoot:
    """Test can_be_root() method on all models."""

    def test_doc_can_be_root(self):
        """Doc model should be creatable as root document."""
        doc = Doc(id="test_doc", label="Test Doc")
        assert doc.can_be_root() is True

    def test_task_can_be_root(self):
        """Task model should be creatable as root document."""
        plan = Doc(id="plan", label="Plan")
        task = Task(id="test_task", plan=plan)
        assert task.can_be_root() is True

    def test_iteration_cannot_be_root(self):
        """Iteration model should not be creatable as root document."""
        iteration = Iteration(id="iteration_1")
        assert iteration.can_be_root() is False

    def test_all_doc_instances_can_be_root(self):
        """All Doc instances should return True for can_be_root()."""
        doc_variants = [
            Doc(id="simple", label="Simple"),
            Doc(id="with_desc", label="With Desc", description="A description"),
            Doc(id="with_metadata", label="With Meta", metadata={"key": "value"}),
            Doc(
                id="with_children",
                label="Parent",
                children={
                    "child1": Doc(id="child1", label="Child 1"),
                },
            ),
        ]
        for doc in doc_variants:
            assert doc.can_be_root() is True

    def test_all_task_instances_can_be_root(self):
        """All Task instances should return True for can_be_root()."""
        plan = Doc(id="plan", label="Plan")
        task_variants = [
            Task(id="simple", plan=plan),
            Task(
                id="with_iters",
                plan=plan,
                iterations={
                    "iteration_1": Iteration(id="iteration_1"),
                },
            ),
        ]
        for task in task_variants:
            assert task.can_be_root() is True

    def test_all_iteration_instances_cannot_be_root(self):
        """All Iteration instances should return False for can_be_root()."""
        iteration_variants = [
            Iteration(id="simple"),
            Iteration(id="with_metadata", metadata={"key": "value"}),
            Iteration(
                id="with_children",
                children={"child1": Doc(id="child1", label="Child")},
            ),
        ]
        for iteration in iteration_variants:
            assert iteration.can_be_root() is False
