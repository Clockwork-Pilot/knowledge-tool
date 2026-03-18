#!/usr/bin/env python3
"""Task and Iteration models for knowledge-based task management."""

import json
import re
from typing import Any, Dict, Optional, Literal, List

try:
    from .metadata_model import Metadata
except ImportError:
    from metadata_model import Metadata
from pydantic import BaseModel, Field, model_validator, model_serializer

# Support both package imports (.) and direct imports (models)
try:
    from .base_model import RenderableModel
    from .doc_model import Doc, Opts
    from .results_model import FeaturesStats, FeaturesStatsDiff
except ImportError:
    from base_model import RenderableModel
    from doc_model import Doc, Opts
    from results_model import FeaturesStats, FeaturesStatsDiff


class CodeStats(BaseModel):
    """Statistics about code changes in an iteration."""

    added_lines: int = Field(default=0, description="Number of lines added")
    removed_lines: int = Field(default=0, description="Number of lines removed")
    files_changed: int = Field(default=0, description="Number of files changed")


class TaskTestMetrics(BaseModel):
    """Statistics about test execution in an iteration."""

    passed: int = Field(default=0, description="Number of tests passed")
    total: int = Field(default=0, description="Total number of tests")
    failed_tests: Dict[str, str] = Field(
        default_factory=dict,
        description="Failed test name -> shrunk error message (max 100 chars)"
    )

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100.0


class Iteration(RenderableModel):
    """Represents a single iteration of a task with metrics."""

    type: Literal["Iteration"] = "Iteration"
    model_version: int = 2
    id: str = Field(..., description="Unique iteration identifier")
    summary: str = Field(..., description="Human-readable summary of what was done in this iteration (max 100 chars)")
    children: Optional[Dict[str, Doc]] = Field(None, description="Child documents for iteration sections")
    metadata: Optional[Metadata] = Field(None, description="Iteration metadata (created_at, updated_at, etc.)")
    code_stats: Optional[CodeStats] = Field(None, description="Code change statistics")
    tests_stats: Optional[TaskTestMetrics] = Field(None, description="Test execution statistics")
    coverage_stats_by_tests: Optional[Dict[str, int]] = Field(
        None, description="Coverage metrics per test (test_name -> lines_covered)"
    )
    features_stats: Optional[FeaturesStats] = Field(
        None, description="Feature constraint validation statistics (which features passed/failed)"
    )
    features_stats_diff: Optional[FeaturesStatsDiff] = Field(
        None, description="Changes in feature validation results compared to previous iteration"
    )

    @model_validator(mode='before')
    @classmethod
    def migrate_v1_to_v2(cls, data: Any) -> Any:
        """Migrate Iteration from model_version 1 to 2.

        v1 -> v2 changes in FeaturesStatsDiff:
          - still_failing: set[str] (stored as list) -> Dict[str, List[str]]
          - improved:      Dict[str, bool]            -> Dict[str, List[str]]
          - regressed:     Dict[str, bool]            -> Dict[str, List[str]]
        """
        if not isinstance(data, dict):
            return data
        if data.get('model_version', 1) >= 2:
            return data

        diff = data.get('features_stats_diff')
        if isinstance(diff, dict):
            # still_failing: list -> dict
            sf = diff.get('still_failing')
            if isinstance(sf, list):
                diff['still_failing'] = {fid: [] for fid in sf}

            # improved: Dict[str, bool] -> Dict[str, List[str]]
            imp = diff.get('improved')
            if isinstance(imp, dict):
                diff['improved'] = {k: [] for k, v in imp.items() if not isinstance(v, list)}
                diff['improved'].update({k: v for k, v in imp.items() if isinstance(v, list)})

            # regressed: Dict[str, bool] -> Dict[str, List[str]]
            reg = diff.get('regressed')
            if isinstance(reg, dict):
                diff['regressed'] = {k: [] for k, v in reg.items() if not isinstance(v, list)}
                diff['regressed'].update({k: v for k, v in reg.items() if isinstance(v, list)})

        data['model_version'] = 2
        return data

    @model_validator(mode='after')
    def normalize_empty_stats(self) -> 'Iteration':
        """Nullify stats fields when they carry no information."""
        if self.features_stats is not None and not self.features_stats.failed:
            self.features_stats = None
        if self.features_stats_diff is not None:
            d = self.features_stats_diff
            if not d.improved and not d.regressed and not d.still_failing:
                self.features_stats_diff = None
        return self

    @model_serializer(mode='wrap')
    def serialize(self, handler) -> dict:
        """Serialize, dropping None fields."""
        return {k: v for k, v in handler(self).items() if v is not None}

    @classmethod
    def create_default(cls) -> "Iteration":
        """Create a default Iteration instance."""
        return cls(
            id=f"{cls.__name__.lower()}_1",
            children=None,
            code_stats=None,
            tests_stats=None,
            coverage_stats_by_tests=None,
            features_stats=None,
            features_stats_diff=None,
            metadata={}
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

        # Render children documents (without their own TOC, since parent Task has comprehensive TOC)
        if self.children:
            # Sort children by render_priority (if available)
            sorted_children = sorted(
                self.children.items(),
                key=lambda x: (not x[1].opts.render_priority if x[1].opts else True)
            )
            for child_id, child_doc in sorted_children:
                child_markdown = child_doc.render(include_toc=False)
                lines.append(child_markdown)
                lines.append("")

        # Render metadata
        if self.metadata:
            lines.append("**Metadata:**")
            lines.append("")
            for key, value in self.metadata.model_dump(exclude_none=True).items():
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

        # Render features stats
        if self.features_stats:
            lines.append("**Feature Constraint Validation Stats:**")
            lines.append("")

            failing_count = len(self.features_stats.failed)
            lines.append(f"- **Failed:** {failing_count} features with constraint violations" if failing_count > 0 else "- **All features passing**")
            lines.append("")

            # Detail failed features if any
            if self.features_stats.failed:
                lines.append("**Failed Feature Details:**")
                lines.append("")
                for feature_id, feature_result in sorted(self.features_stats.failed.items()):
                    lines.append(f"**{feature_id}:**")
                    if feature_result.constraints_results:
                        for constraint_id, result in sorted(feature_result.constraints_results.items()):
                            if hasattr(result, 'verdict') and not result.verdict:
                                lines.append(f"- {constraint_id}: FAILED")
                    lines.append("")

        return "\n".join(lines).strip()

    def render_toc(self) -> list:
        """Generate TOC for Iteration's children structure.

        Returns nested TOC from each child if it has render_toc=true.

        Returns:
            List of TOC lines from children with render_toc enabled.
        """
        toc_lines = []

        if not self.children:
            return toc_lines

        # Sort children by render_priority (if available)
        sorted_children = sorted(
            self.children.items(),
            key=lambda x: (not x[1].opts.render_priority if x[1].opts else True)
        )

        for child_id, child_doc in sorted_children:
            # Only include child's TOC if it explicitly has render_toc=true
            if child_doc.opts and child_doc.opts.render_toc:
                child_toc = child_doc.render_toc()
                if child_toc:
                    toc_lines.extend(child_toc)

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Iteration cannot be created as a root document.

        Iterations only exist as children within Task documents.

        Returns:
            False - Iteration cannot be a root document.
        """
        return False


class Task(RenderableModel):
    """Represents a task with specification and iterations."""

    type: Literal["Task"] = "Task"
    model_version: int = 2
    id: str = Field(..., description="Unique task identifier")
    iterations: Optional[Dict[str, Iteration]] = Field(
        None, description="Iterations indexed by iteration ID"
    )
    opts: Optional[Opts] = Field(None, description="Task rendering options (render_toc, render_priority)")

    @classmethod
    def create_default(cls) -> "Task":
        """Create a default Task instance."""
        return cls(
            id=f"{cls.__name__.lower()}_1",
            iterations=None,
            opts=None
        )

    @model_validator(mode='after')
    def set_default_render_toc(self) -> 'Task':
        """Set render_toc=True by default if opts is not specified.

        When loading a Task from snapshot (JSON), if opts is not provided,
        create default opts with render_toc=True for better UX.
        If opts exists and render_toc is explicitly False, keep it False.
        """
        if self.opts is None:
            # opts not specified in snapshot: create new Opts with render_toc=True
            self.opts = Opts(render_toc=True, render_priority=False)
        # If opts is specified, use its render_toc value as-is
        return self

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
        # opts is guaranteed to exist after validator runs, render_toc defaults to True
        if include_toc and self.opts.render_toc:
            toc_lines = self._generate_toc()
            if toc_lines:
                lines.append("## Table of Contents")
                lines.append("")
                lines.extend(toc_lines)
                lines.append("")

        # Note: Specification and features are now in task-spec.k.json
        lines.append("## Task Overview")
        lines.append("")
        lines.append("**Specification:** See task-spec.k.json for features and constraints")
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

        return "\n".join(lines).strip()

    @staticmethod
    def _adjust_heading_levels(markdown: str, shift: int = 2) -> str:
        """Adjust all markdown heading levels by prepending # symbols.

        This shifts feature headings from # to ### while preserving relative hierarchy.
        So # becomes ###, ## becomes ####, etc.

        Args:
            markdown: Markdown text with headings
            shift: Number of levels to shift (default 2, so # becomes ###)

        Returns:
            Markdown with adjusted heading levels
        """
        lines = markdown.split('\n')
        adjusted_lines = []

        for line in lines:
            # Check if line starts with markdown heading syntax
            if line.startswith('#') and not line.startswith(' '):
                # Count existing hashes
                hash_count = len(line) - len(line.lstrip('#'))
                # Prepend shift amount of new hashes
                new_heading = '#' * shift + line
                adjusted_lines.append(new_heading)
            else:
                adjusted_lines.append(line)

        return '\n'.join(adjusted_lines)

    @staticmethod
    def _generate_anchor(text: str) -> str:
        """Generate markdown anchor from heading text.

        Converts heading text to a valid markdown anchor by:
        - Converting to lowercase
        - Replacing spaces with hyphens
        - Removing special characters except hyphens and underscores

        Args:
            text: Heading text to generate anchor for

        Returns:
            Markdown anchor string (without # prefix)
        """
        # Lowercase
        anchor = text.lower()
        # Replace spaces with hyphens (underscores preserved, matching markdown renderers)
        anchor = anchor.replace(' ', '-')
        # Remove special characters (keep only word chars and hyphens)
        anchor = re.sub(r'[^\w-]', '', anchor)
        # Remove multiple consecutive hyphens
        anchor = re.sub(r'-+', '-', anchor)
        # Strip leading/trailing hyphens
        anchor = anchor.strip('-')
        return anchor

    def _generate_toc(self) -> list:
        """Generate table of contents for the task.

        Uses 4-space indentation increments (standard for VS Code markdown preview).

        Returns:
            List of TOC lines including Specification and Iterations sections.
        """
        import re
        toc_lines = []

        # Add Task Overview section
        toc_lines.append("- [Task Overview](#task-overview)")
        # Note: Features and specifications are now in task-spec.k.json

        # Add Iterations section if there are iterations
        if self.iterations:
            toc_lines.append("- [Iterations](#iterations)")

            # Sort iterations by ID
            sorted_iterations = sorted(
                self.iterations.items(), key=lambda x: (len(x[0]), x[0])
            )

            for iter_id, iteration in sorted_iterations:
                # Use iteration's id field for heading and anchor
                iter_id_field = iteration.id
                # Generate anchor matching standard markdown: lowercase, spaces→hyphens
                anchor = iter_id_field.lower().replace(' ', '-')

                toc_lines.append(f"    - [{iter_id_field}](#{anchor})")

                # Add iteration's children TOC if available (6-space indent)
                iteration_toc = iteration.render_toc()
                if iteration_toc:
                    for toc_line in iteration_toc:
                        toc_lines.append("      " + toc_line)

        return toc_lines

    @staticmethod
    def _generate_doc_toc(doc: Doc, level: int = 1) -> list:
        """Generate table of contents from a Doc node including its label and children.

        Args:
            doc: Doc node to generate TOC for
            level: Current heading level (for indentation)

        Returns:
            List of TOC lines with doc label and its children
        """
        import re
        toc_lines = []

        # Add the doc's own label as a TOC entry
        label = doc.label
        anchor = label.lower()
        anchor = anchor.replace(' ', '-')
        anchor = re.sub(r'[^\w-]', '', anchor)
        toc_lines.append(f"- [{label}](#{anchor})")

        # Add doc's children if they exist
        children = doc.children or {}
        if children:
            # Sort children by priority (matching Doc's sorting logic)
            sorted_children = sorted(
                children.items(),
                key=lambda item: not item[1].opts.render_priority if item[1].opts else True
            )

            for child_id, child_node in sorted_children:
                child_label = child_node.label
                # Generate anchor matching standard markdown: lowercase, spaces→hyphens, remove special chars
                child_anchor = child_label.lower()
                child_anchor = child_anchor.replace(' ', '-')
                child_anchor = re.sub(r'[^\w-]', '', child_anchor)

                toc_lines.append(f"  - [{child_label}](#{child_anchor})")

                # Recursively add child's children
                child_toc = Task._generate_doc_toc(child_node, level + 1)
                for toc_line in child_toc:
                    toc_lines.append("    " + toc_line)

        return toc_lines

    def render_toc(self) -> list:
        """Generate TOC for Task structure with Specification and Iterations sections.

        Uses 4-space indentation increments (standard for VS Code markdown preview).

        Includes:
        - Specification entry with nested TOC from spec.description.render_toc() if spec.description.opts.render_toc=true
        - Iterations entry with iteration entries and their nested TOCs if iteration.opts.render_toc=true

        Returns:
            List of TOC lines with proper indentation and anchors.
        """
        toc_lines = []

        # Specification entry
        toc_lines.append("- [Specification](#specification)")

        # Features entry (if features exist)
        if self.spec.features:
            toc_lines.append("- [Features](#features)")
            for feature_id in sorted(self.spec.features.keys()):
                feature = self.spec.features[feature_id]
                # Feature anchor: generated from ID only (markdown naturally does this)
                feature_anchor = self._generate_anchor(feature_id)
                toc_lines.append(f"    - [{feature_id}](#{feature_anchor})")

                # Add constraints for this feature (nested deeper with 6-space indent)
                if feature.constraints:
                    for constraint_id in sorted(feature.constraints.keys()):
                        # Constraint anchor: generated from ID only
                        constraint_anchor = self._generate_anchor(constraint_id)
                        toc_lines.append(f"      - [{constraint_id}](#{constraint_anchor})")

        # Iterations entry (if iterations exist)
        if self.iterations:
            toc_lines.append("- [Iterations](#iterations)")

            # Sort iterations by ID
            sorted_iterations = sorted(
                self.iterations.items(), key=lambda x: (len(x[0]), x[0])
            )

            for iter_key, iteration in sorted_iterations:
                # Use iteration's id field (not dict key) for heading and anchor
                iter_id = iteration.id
                # Create anchor matching standard markdown: lowercase, spaces→hyphens only
                anchor = iter_id.lower().replace(" ", "-")
                toc_lines.append(f"    - [{iter_id}](#{anchor})")

                # Add nested TOC from iteration's children if any have render_toc=true (6-space indent)
                iteration_toc = iteration.render_toc()
                if iteration_toc:
                    for line in iteration_toc:
                        toc_lines.append("      " + line)

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Task can be created as a root document.

        Returns:
            True - Task can be a root document.
        """
        return True


Task.model_rebuild()
Iteration.model_rebuild()
