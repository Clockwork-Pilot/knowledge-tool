#!/usr/bin/env python3
"""Task and Iteration models for knowledge-based task management."""

import json
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

from knowledge_tool.models import RenderableModel, Doc


class CodeStats(BaseModel):
    """Statistics about code changes in an iteration."""

    added_lines: int = Field(default=0, description="Number of lines added")
    removed_lines: int = Field(default=0, description="Number of lines removed")
    files_changed: int = Field(default=0, description="Number of files changed")


class TaskTestMetrics(BaseModel):
    """Statistics about test execution in an iteration."""

    passed: int = Field(default=0, description="Number of tests passed")
    total: int = Field(default=0, description="Total number of tests")

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100.0


class Iteration(RenderableModel):
    """Represents a single iteration of a task with metrics."""

    id: str = Field(..., description="Unique iteration identifier")
    type: Literal["Iteration"] = "Iteration"
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Iteration metadata (created_at, updated_at, etc.)"
    )
    code_stats: Optional[CodeStats] = Field(None, description="Code change statistics")
    tests_stats: Optional[TaskTestMetrics] = Field(None, description="Test execution statistics")
    coverage_stats_by_tests: Optional[Dict[str, int]] = Field(
        None, description="Coverage metrics per test (test_name -> lines_covered)"
    )

    def render(self) -> str:
        """Render Iteration to markdown string.

        Returns:
            Formatted markdown string representation.
        """
        lines = []
        lines.append(f"### {self.id}")
        lines.append("")

        # Render metadata
        if self.metadata:
            lines.append("**Metadata:**")
            lines.append("")
            for key, value in self.metadata.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        # Render code stats
        if self.code_stats:
            lines.append("**Code Stats:**")
            lines.append(f"- Added lines: {self.code_stats.added_lines}")
            lines.append(f"- Removed lines: {self.code_stats.removed_lines}")
            lines.append(f"- Files changed: {self.code_stats.files_changed}")
            lines.append("")

        # Render test stats
        if self.tests_stats:
            lines.append("**Test Stats:**")
            lines.append(f"- Passed: {self.tests_stats.passed}/{self.tests_stats.total}")
            if self.tests_stats.total > 0:
                lines.append(f"- Pass rate: {self.tests_stats.pass_rate:.1f}%")
            lines.append("")

        # Render coverage stats
        if self.coverage_stats_by_tests:
            lines.append("**Coverage by Test:**")
            lines.append("")
            for test_name, coverage in self.coverage_stats_by_tests.items():
                lines.append(f"- {test_name}: {coverage} lines")
            lines.append("")

        return "\n".join(lines).strip()


class Task(RenderableModel):
    """Represents a task with plan and iterations."""

    id: str = Field(..., description="Unique task identifier")
    type: Literal["Task"] = "Task"
    project: Optional[Doc] = Field(None, description="Project description as a Doc")
    plan: Doc = Field(..., description="Task plan as a Doc with metadata (created_at, updated_at)")
    iterations: Optional[Dict[str, Iteration]] = Field(
        None, description="Iterations indexed by iteration ID"
    )

    def render(self) -> str:
        """Render Task to markdown string.

        Returns:
            Formatted markdown string representation.
        """
        lines = []
        lines.append(f"# Task: {self.id}")
        lines.append("")

        # Render project section
        if self.project:
            lines.append("## Project")
            lines.append("")
            project_markdown = self.project.render()
            lines.append(project_markdown)
            lines.append("")

        # Render plan section
        lines.append("## Plan")
        lines.append("")
        plan_markdown = self.plan.render()
        lines.append(plan_markdown)
        lines.append("")

        # Render iterations section
        if self.iterations:
            lines.append("## Iterations")
            lines.append("")
            # Sort iterations by ID (assuming they follow iteration_1, iteration_2 pattern)
            sorted_iterations = sorted(
                self.iterations.items(), key=lambda x: (len(x[0]), x[0])
            )
            for iter_id, iteration in sorted_iterations:
                lines.append(iteration.render())
                lines.append("")

        return "\n".join(lines).strip()


Task.model_rebuild()
Iteration.model_rebuild()
