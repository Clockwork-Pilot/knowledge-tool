#!/usr/bin/env python3
"""Constraint execution result models."""

from datetime import datetime
from typing import Optional, Dict, List, Union, Literal
from pydantic import BaseModel, Field, model_validator, model_serializer

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
    fails_count: int = Field(default=0, description="Number of times this constraint has failed")


class FeatureResult(BaseModel):
    """Constraint execution results for a feature."""

    feature_id: str = Field(..., description="ID of the feature")
    constraints_results: Dict[str, ConstraintBashResult] = Field(
        ..., description="Constraint execution results indexed by constraint ID (required)"
    )


class FeaturesStats(BaseModel):
    """Statistics tracking feature constraint validation results for an iteration."""

    failed: Dict[str, FeatureResult] = Field(
        default_factory=dict,
        description="Failed features with their FeatureResult details. Passing features are absent."
    )

    def diff(self, previous: Optional["FeaturesStats"]) -> "FeaturesStatsDiff":
        """Calculate difference between this and previous features stats.

        Uses only the failed dict keys — a feature absent from failed is passing.

        Args:
            previous: Previous iteration's FeaturesStats (None if first iteration)

        Returns:
            FeaturesStatsDiff with improved, regressed, and still_failing features
        """
        if previous is None:
            return FeaturesStatsDiff(
                improved={},
                regressed={},
                still_failing={
                    fid: list(fr.constraints_results.keys())
                    for fid, fr in self.failed.items()
                }
            )

        improved = {}
        regressed = {}

        # Improved: was failing, now passing (absent from current failed)
        for feature_id, feature_result in previous.failed.items():
            if feature_id not in self.failed:
                improved[feature_id] = list(feature_result.constraints_results.keys())

        # Regressed: was passing (absent from previous failed), now failing
        for feature_id, feature_result in self.failed.items():
            if feature_id not in previous.failed:
                regressed[feature_id] = list(feature_result.constraints_results.keys())

        still_failing = {
            fid: list(self.failed[fid].constraints_results.keys())
            for fid in set(self.failed.keys()).intersection(previous.failed.keys())
        }

        return FeaturesStatsDiff(
            improved=improved,
            regressed=regressed,
            still_failing=still_failing
        )


class FeaturesStatsDiff(BaseModel):
    """Tracks changes in feature constraint validation between iterations."""

    improved: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Features that improved (fail->pass): feature_id -> list of constraint IDs"
    )
    regressed: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Features that regressed (pass->fail): feature_id -> list of constraint IDs"
    )
    still_failing: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Features still failing: feature_id -> list of constraint IDs"
    )

    @model_serializer
    def serialize(self) -> dict:
        """Omit empty sub-dicts."""
        d = {}
        if self.improved:
            d['improved'] = self.improved
        if self.regressed:
            d['regressed'] = self.regressed
        if self.still_failing:
            d['still_failing'] = self.still_failing
        return d


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

                        for constraint_id in sorted(feature_result.constraints_results.keys()):
                            result = feature_result.constraints_results[constraint_id]
                            namespaced_id = f"{feature_id}.{constraint_id}"
                            constraint_anchor = namespaced_id.replace("_", "-").replace(" ", "-").replace(".", "-")
                            verdict_str = "✓ PASS" if result.verdict else "✗ FAIL"
                            lines.append(f"<a id=\"{constraint_anchor}\"></a>")
                            lines.append(f"#### {namespaced_id}")
                            lines.append(f"**Verdict:** {verdict_str}")
                            if result.timestamp:
                                lines.append(f"**Timestamp:** {result.timestamp.isoformat()}")
                            if result.shrunken_output:
                                lines.append(f"**Output:** `{result.shrunken_output}`")
                            lines.append("")

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
