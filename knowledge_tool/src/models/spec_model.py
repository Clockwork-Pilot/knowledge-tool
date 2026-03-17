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
        """Render Spec to markdown string.

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

        # Render features section
        if self.features:
            lines.append("## Features")
            lines.append("")
            for feature_id, feature in sorted(self.features.items()):
                lines.append(f"### {feature.id}: {feature.description}")
                lines.append("")
                if feature.constraints:
                    lines.append("**Constraints:**")
                    lines.append("")
                    for c_id, constraint in feature.constraints.items():
                        lines.append(f"- {c_id}: {constraint.description if hasattr(constraint, 'description') else 'N/A'}")
                    lines.append("")
                lines.append("")

        return "\n".join(lines).strip()

    def render_toc(self) -> list:
        """Generate table of contents for spec.

        Returns:
            List of TOC lines.
        """
        toc_lines = []

        toc_lines.append("- [Description](#description)")

        if self.features:
            toc_lines.append("- [Features](#features)")
            for feature_id in sorted(self.features.keys()):
                toc_lines.append(f"  - [{feature_id}](#{feature_id})")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Spec can be created as a root document.

        Returns:
            True - Spec can be a root document.
        """
        return True


Spec.model_rebuild()
