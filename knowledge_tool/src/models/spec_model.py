#!/usr/bin/env python3
"""Spec model for feature specifications with versioning."""

from typing import Any, Dict, Optional, Literal
from pydantic import Field

# Support both package imports (.) and direct imports (models)
try:
    from .base_model import RenderableModel
    from .feature_model import Feature
except ImportError:
    from base_model import RenderableModel
    from feature_model import Feature


class Spec(RenderableModel):
    """Renderable specification document with features and versioning.

    Spec documents organize features with version control and detailed descriptions.
    Each spec includes a description and optional features that define the specification scope.
    """

    type: Literal["Spec"] = "Spec"
    model_version: int = 1
    version: int = 1
    description: str = Field(default="", description="Specification description")
    features: Optional[Dict[str, Feature]] = Field(
        None, description="Features indexed by feature ID"
    )

    @classmethod
    def create_default(cls) -> "Spec":
        """Create a default Spec instance."""
        return cls(description="Specification description", features=None)

    def render(self, include_toc: bool = True) -> str:
        """Render Spec to markdown string with detailed features and constraints.

        Args:
            include_toc: Whether to include TOC in rendering (default: True).

        Returns:
            Formatted markdown string representation.
        """
        lines = []

        # Render heading
        lines.append(f"# Specification")
        lines.append("")

        # Render description
        if self.description:
            lines.append("## Overview")
            lines.append("")
            lines.append(self.description)
            lines.append("")

        if include_toc:
            toc = self.render_toc()
            if toc:
                lines.append("## Table of Contents")
                lines.append("")
                lines.extend(toc)
                lines.append("")

        # Render features section with detailed content
        if self.features:
            lines.append("## Features")
            lines.append("")
            # Sort features by ID for consistent rendering
            sorted_features = sorted(self.features.items())
            for feature_id, feature in sorted_features:
                # Render feature heading at level 3 (under ## Features)
                lines.append(f"### Feature: {feature.id}")
                lines.append(f"**{feature.description}**")
                lines.append("")

                # Render goals if present
                if feature.goals:
                    lines.append("**Goals:**")
                    for goal in feature.goals:
                        lines.append(f"- {goal}")
                    lines.append("")

                # Render constraints directly at level 4, without section headers
                if feature.constraints:
                    for constraint_id, constraint in sorted(feature.constraints.items()):
                        # Render constraint heading at level 4 (under ### feature)
                        lines.append(f"#### {constraint.id}")
                        lines.append(f"**Description:** {constraint.description}")

                        # Render constraint-specific details
                        if hasattr(constraint, 'cmd'):  # ConstraintBash
                            lines.append(f"**Command:** `{constraint.cmd}`")

                        lines.append("")

                # Render metadata if present
                if feature.metadata:
                    lines.append("**Metadata:**")
                    for key, value in feature.metadata.items():
                        lines.append(f"- {key}: {value}")
                    lines.append("")

        return "\n".join(lines).strip()

    def render_toc(self) -> list:
        """Generate table of contents for spec with features and constraints.

        Returns:
            List of TOC lines with proper indentation.
        """
        toc_lines = []

        toc_lines.append("- [Overview](#overview)")

        if self.features:
            toc_lines.append("- [Features](#features)")
            for feature_id in sorted(self.features.keys()):
                feature = self.features[feature_id]
                # Feature anchor: generated from ID
                feature_anchor = feature_id.lower().replace(' ', '-')
                toc_lines.append(f"    - [Feature: {feature_id}](#{feature_anchor})")

                # Add constraints for this feature (nested deeper with 6-space indentation)
                if feature.constraints:
                    for constraint_id in sorted(feature.constraints.keys()):
                        # Constraint anchor: generated from ID only
                        constraint_anchor = constraint_id.lower().replace(' ', '-')
                        toc_lines.append(f"      - [{constraint_id}](#{constraint_anchor})")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Spec can be created as a root document.

        Returns:
            True - Spec can be a root document.
        """
        return True


Spec.model_rebuild()
