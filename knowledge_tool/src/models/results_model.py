#!/usr/bin/env python3
"""Constraint execution result models."""

from datetime import datetime
from typing import Optional, Dict, Literal
from pydantic import BaseModel, Field

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
except ImportError:
    from models import RenderableModel


class ConstraintBashResult(BaseModel):
    """Result of executing a bash constraint."""

    constraint_id: str = Field(..., description="ID of the constraint that was executed")
    verdict: bool = Field(..., description="Whether the constraint passed (True) or failed (False)")
    shrunken_output: Optional[str] = Field(None, description="Truncated stdout/stderr output")
    timestamp: Optional[datetime] = Field(None, description="When the constraint was executed")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    fails_count: int = Field(default=0, description="Number of times this constraint has failed")
    postponed: bool = Field(
        default=False, description="True if constraint check was skipped due to failing dependencies"
    )


class FeatureResult(BaseModel):
    """Constraint execution results for a feature."""

    feature_id: str = Field(..., description="ID of the feature")
    constraints_results: Dict[str, ConstraintBashResult] = Field(
        ..., description="Constraint execution results indexed by constraint ID (required)"
    )




class ChecksResults(RenderableModel):
    """Root document for constraint execution results."""

    type: Literal["ChecksResults"] = "ChecksResults"
    model_version: int = 1
    features_results: Optional[Dict[str, FeatureResult]] = Field(
        None, description="Feature results indexed by feature ID"
    )

    @classmethod
    def create_default(cls) -> "ChecksResults":
        """Create a default ChecksResults instance."""
        return cls(features_results=None)

    def render(self, include_toc: bool = True) -> str:
        """Render ChecksResults to markdown string.

        Args:
            include_toc: Whether to include TOC in rendering (default: True).

        Returns:
            Formatted markdown string representation.
        """
        lines = []

        if include_toc:
            toc = self.render_toc()
            if toc:
                lines.append("## Table of Contents")
                lines.append("")
                lines.extend(toc)
                lines.append("")

        # Organize and render results by feature
        if self.features_results:
            has_results = any(
                feature_result.constraints_results
                for feature_result in self.features_results.values()
            )

            if has_results:
                lines.append("## Constraint Results")
                lines.append("")

                # Render each feature and its constraints
                for feature_id in sorted(self.features_results.keys()):
                    feature_result = self.features_results[feature_id]

                    if feature_result.constraints_results:
                        # Feature header with explicit anchor
                        feature_anchor = feature_id.replace("_", "-").replace(" ", "-")
                        lines.append(f"<a id=\"{feature_anchor}\"></a>")
                        lines.append(f"### Feature: {feature_id}")
                        lines.append("")

                        # Feature summary
                        passed = sum(1 for r in feature_result.constraints_results.values() if r.verdict)
                        total = len(feature_result.constraints_results)
                        status = "✓" if passed == total else "⚠"
                        lines.append(f"**{status} {passed}/{total} constraints passed**")
                        lines.append("")

                        for constraint_id in sorted(feature_result.constraints_results.keys()):
                            result = feature_result.constraints_results[constraint_id]
                            namespaced_id = f"{feature_id}.{constraint_id}"
                            constraint_anchor = namespaced_id.replace("_", "-").replace(" ", "-").replace(".", "-")
                            verdict_str = "✓ PASS" if result.verdict else "✗ FAIL"

                            lines.append(f"<a id=\"{constraint_anchor}\"></a>")
                            lines.append(f"**{verdict_str}** {constraint_id}")
                            lines.append("")

                            # Indented details as list items
                            if result.timestamp:
                                lines.append(f"- Executed: {result.timestamp.isoformat()}")
                            if result.duration is not None:
                                lines.append(f"- Duration: {result.duration:.2f}s")
                            if result.shrunken_output:
                                lines.append(f"- Output: {result.shrunken_output}")

                            lines.append("")

        return "\n".join(lines).strip()

    def render_toc(self) -> list:
        """Generate table of contents for constraint results with all features and constraints.

        Returns:
            List of TOC lines with links to each feature and constraint.
        """
        toc_lines = []

        if self.features_results:
            # Add main Constraint Results header
            toc_lines.append("- [Constraint Results](#constraint-results)")

            # Add each feature and its constraints
            for feature_id in sorted(self.features_results.keys()):
                feature_result = self.features_results[feature_id]
                # Feature anchor uses feature_id with hyphens instead of underscores/spaces
                feature_anchor = feature_id.replace("_", "-").replace(" ", "-")
                toc_lines.append(f"  - [Feature: {feature_id}](#{feature_anchor})")

                # Add each constraint within the feature
                if feature_result.constraints_results:
                    for constraint_id in sorted(feature_result.constraints_results.keys()):
                        # Constraint anchor uses feature_id.constraint_id
                        constraint_anchor = f"{feature_id}.{constraint_id}".replace("_", "-").replace(" ", "-").replace(".", "-")
                        toc_lines.append(f"    - [{constraint_id}](#{constraint_anchor})")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """ChecksResults can be created as a root document.

        Returns:
            True - ChecksResults can be root documents.
        """
        return True
