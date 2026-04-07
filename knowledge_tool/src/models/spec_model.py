#!/usr/bin/env python3
"""Spec model for feature specifications with versioning."""

import re
from typing import Any, Dict, Optional, Literal
from pydantic import Field, model_validator, ValidationInfo

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
    contains_unverified_constraints: bool = False
    features: Optional[Dict[str, Feature]] = Field(
        None, description="Features indexed by feature ID"
    )

    @model_validator(mode='before')
    @classmethod
    def protect_features_with_verified_constraints_from_removal(cls, data: Any, info: ValidationInfo) -> Any:
        """Raise an error if any feature with verified constraints is being removed.

        A feature with verified constraints (at least one constraint with fails_count > 0)
        cannot be removed, as it would lose proven constraint failure history.

        Uses original_doc from validation context to detect removed features.
        """
        context = getattr(info, 'context', None) if info else None
        if not context or not isinstance(data, dict):
            return data

        original_doc = context.get('original_doc', {})
        if not original_doc or original_doc.get('type') != 'Spec':
            return data

        original_features = original_doc.get('features') or {}
        new_features = data.get('features') or {}

        for feature_id, original_feature_data in original_features.items():
            if feature_id not in new_features:
                # Feature is being removed. Check if it has verified constraints.
                constraints = (original_feature_data or {}).get('constraints') or {}
                for cid, constraint_data in constraints.items():
                    fails_count = constraint_data.get('fails_count', 0)
                    if fails_count > 0:
                        # Found a verified constraint in the removed feature
                        raise ValueError(
                            f"Cannot remove feature '{feature_id}': contains verified constraint '{cid}' "
                            f"with fails_count={fails_count} > 0. "
                            f"Fix the constraint to pass first."
                        )

        return data

    @model_validator(mode='before')
    @classmethod
    def compute_unverified_constraints_flag(cls, data: Any, info: ValidationInfo) -> Any:
        """Automatically compute contains_unverified_constraints flag.

        Scans all constraints in all features and sets the flag to:
        - True if ANY constraint has fails_count < 1 (unproven constraint)
        - False if ALL constraints have fails_count >= 1 (all proven) or no constraints exist
        """
        if not isinstance(data, dict):
            return data

        features = data.get('features') or {}
        has_unverified = False

        # Check all constraints in all features
        for feature in features.values():
            if isinstance(feature, dict):
                constraints = feature.get('constraints') or {}
                for constraint in constraints.values():
                    if isinstance(constraint, dict):
                        fails_count = constraint.get('fails_count', 0)
                        if fails_count < 1:
                            has_unverified = True
                            break
            if has_unverified:
                break

        data['contains_unverified_constraints'] = has_unverified
        return data

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
                        lines.append("")

                # Render metadata if present
                if feature.metadata:
                    lines.append("**Metadata:**")
                    for key, value in feature.metadata.model_dump(exclude_none=True).items():
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
                # Feature anchor: generated from "Feature: {id}" heading text using markdown rules
                heading_text = f"Feature: {feature_id}"
                feature_anchor = heading_text.lower().replace(' ', '-')
                feature_anchor = re.sub(r'[^\w-]', '', feature_anchor)
                feature_anchor = re.sub(r'-+', '-', feature_anchor).strip('-')
                toc_lines.append(f"    - [Feature: {feature_id}](#{feature_anchor})")

                # Add constraints for this feature (nested deeper with 6-space indentation)
                if feature.constraints:
                    for constraint_id in sorted(feature.constraints.keys()):
                        # Constraint anchor: generated from ID heading text
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
