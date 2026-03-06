#!/usr/bin/env python3
"""Task and Iteration models for knowledge-based task management."""

import json
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel, Doc, Opts
except ImportError:
    from models import RenderableModel, Doc, Opts


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
    summary: Optional[Doc] = Field(None, description="Summary of the iteration")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Iteration metadata (created_at, updated_at, etc.)"
    )
    code_stats: Optional[CodeStats] = Field(None, description="Code change statistics")
    tests_stats: Optional[TaskTestMetrics] = Field(None, description="Test execution statistics")
    coverage_stats_by_tests: Optional[Dict[str, int]] = Field(
        None, description="Coverage metrics per test (test_name -> lines_covered)"
    )

    def render(self, include_toc: bool = True) -> str:
        """Render Iteration to markdown string.

        Args:
            include_toc: Whether to include TOC in rendering (default: True).
                        Set to False when rendering as a child of another document.

        Returns:
            Formatted markdown string representation.
        """
        lines = []
        lines.append(f"### {self.id}")
        lines.append("")

        # Render summary (without its own TOC, since parent Task has comprehensive TOC)
        if self.summary:
            summary_markdown = self.summary.render(include_toc=False)
            lines.append(summary_markdown)
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

    def render_toc(self) -> list:
        """Generate TOC for Iteration's summary structure.

        Returns nested TOC from summary.render_toc() if summary Doc has render_toc=true.

        Returns:
            List of TOC lines from summary (empty if no summary or render_toc not enabled).
        """
        if not self.summary:
            return []

        # Only include summary's TOC if it explicitly has render_toc=true
        if self.summary.opts and self.summary.opts.render_toc:
            return self.summary.render_toc()

        return []


class Task(RenderableModel):
    """Represents a task with plan and iterations."""

    id: str = Field(..., description="Unique task identifier")
    type: Literal["Task"] = "Task"
    plan: Doc = Field(..., description="Task plan as a Doc with metadata (created_at, updated_at)")
    iterations: Optional[Dict[str, Iteration]] = Field(
        None, description="Iterations indexed by iteration ID"
    )
    opts: Optional[Opts] = Field(None, description="Task rendering options (render_toc, render_priority)")

    def render(self, include_toc: bool = True) -> str:
        """Render Task to markdown string.

        Args:
            include_toc: Whether to include TOC in rendering (default: True).
                        Set to False when rendering as a child of another document.

        Returns:
            Formatted markdown string representation.
        """
        lines = []
        lines.append(f"# Task: {self.id}")
        lines.append("")

        # Insert TOC if applicable
        if include_toc:
            toc_lines = self.render_toc()
            if toc_lines:
                lines.append("## Table of Contents")
                lines.append("")
                lines.extend(toc_lines)
                lines.append("")

        # Render plan section (without its own TOC, since Task has comprehensive TOC)
        lines.append("## Plan")
        lines.append("")
        plan_markdown = self.plan.render(include_toc=False)
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
                lines.append(iteration.render(include_toc=False))
                lines.append("")

        markdown_content = "\n".join(lines).strip()

        # Insert TOC if enabled
        if render_toc:
            toc_lines = self._generate_toc()
            if toc_lines:
                # Find where to insert TOC (after heading and any description)
                lines_list = markdown_content.split("\n")
                toc_insert_pos = 1
                for i, line in enumerate(lines_list[1:], 1):
                    if line.startswith("#") or line == "":
                        continue
                    toc_insert_pos = i
                    break

                lines_list.insert(toc_insert_pos, "")
                lines_list.insert(toc_insert_pos + 1, "## Table of Contents")
                lines_list.insert(toc_insert_pos + 2, "")
                lines_list[toc_insert_pos + 3:toc_insert_pos + 3] = toc_lines
                lines_list.insert(toc_insert_pos + 3 + len(toc_lines), "")

                markdown_content = "\n".join(lines_list)

        return markdown_content.strip()

    def _generate_toc(self) -> list:
        """Generate table of contents for the task.

        Returns:
            List of TOC lines including Plan and Iterations sections.
        """
        import re
        toc_lines = []

        # Add Plan section
        toc_lines.append("- [Plan](#plan)")

        # Generate TOC for Plan if the Doc has render_toc enabled
        if self.plan.opts and self.plan.opts.render_toc:
            plan_toc = self._generate_doc_toc(self.plan)
            # Indent plan's TOC under Plan
            for toc_line in plan_toc:
                toc_lines.append("  " + toc_line)

        # Add Iterations section if there are iterations
        if self.iterations:
            toc_lines.append("- [Iterations](#iterations)")

            # Sort iterations by ID
            sorted_iterations = sorted(
                self.iterations.items(), key=lambda x: (len(x[0]), x[0])
            )

            for iter_id, iteration in sorted_iterations:
                # Generate anchor for iteration ID
                anchor = iter_id.lower()
                anchor = anchor.replace(' ', '-')
                anchor = re.sub(r'[^\w-]', '', anchor)

                toc_lines.append(f"  - [{iter_id}](#{anchor})")

                # Add summary TOC if summary exists and has render_toc enabled
                if iteration.summary and iteration.summary.opts and iteration.summary.opts.render_toc:
                    summary_toc = self._generate_doc_toc(iteration.summary)
                    # Indent summary's TOC under the iteration
                    for toc_line in summary_toc:
                        toc_lines.append("    " + toc_line)

        return toc_lines

    @staticmethod
    def _generate_doc_toc(doc: Doc, level: int = 1) -> list:
        """Generate table of contents from a Doc node and its children.

        Args:
            doc: Doc node to generate TOC for
            level: Current heading level (for indentation)

        Returns:
            List of TOC lines
        """
        import re
        toc_lines = []

        children = doc.children or {}
        if children:
            # Sort children by priority (matching Doc's sorting logic)
            sorted_children = sorted(
                children.items(),
                key=lambda item: not item[1].opts.render_priority if item[1].opts else True
            )

            for child_id, child_node in sorted_children:
                label = child_node.label
                # Generate anchor matching standard markdown: lowercase, spaces→hyphens, remove special chars
                anchor = label.lower()
                anchor = anchor.replace(' ', '-')
                anchor = re.sub(r'[^\w-]', '', anchor)

                toc_lines.append(f"- [{label}](#{anchor})")

                # Recursively add child's children
                child_toc = Task._generate_doc_toc(child_node, level + 1)
                for toc_line in child_toc:
                    toc_lines.append("  " + toc_line)

        return toc_lines

    def render_toc(self) -> list:
        """Generate TOC for Task structure with Plan and Iterations sections.

        Includes:
        - Plan entry with nested TOC from plan.render_toc() if plan.opts.render_toc=true
        - Iterations entry with iteration entries and their nested TOCs if summary.opts.render_toc=true

        Returns:
            List of TOC lines with proper indentation and anchors.
        """
        toc_lines = []

        # Plan entry
        toc_lines.append("- [Plan](#plan)")
        if self.plan and self.plan.opts and self.plan.opts.render_toc:
            plan_toc = self.plan.render_toc()
            if plan_toc:
                # Indent plan's TOC entries
                for line in plan_toc:
                    toc_lines.append("  " + line)

        # Iterations entry (if iterations exist)
        if self.iterations:
            toc_lines.append("- [Iterations](#iterations)")

            # Sort iterations by ID
            sorted_iterations = sorted(
                self.iterations.items(), key=lambda x: (len(x[0]), x[0])
            )

            for iter_id, iteration in sorted_iterations:
                # Create anchor for iteration (lowercase, spaces/underscores to hyphens)
                anchor = iter_id.lower().replace("_", "-")
                toc_lines.append(f"  - [{iter_id}](#{anchor})")

                # Add nested TOC from iteration's summary only if summary has render_toc=true
                if iteration.summary and iteration.summary.opts and iteration.summary.opts.render_toc:
                    iteration_toc = iteration.render_toc()
                    if iteration_toc:
                        for line in iteration_toc:
                            toc_lines.append("    " + line)

        return toc_lines


Task.model_rebuild()
Iteration.model_rebuild()
