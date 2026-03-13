#!/usr/bin/env python3
"""Spec model for feature specifications with versioning."""

from typing import Any, Dict, Optional, Literal
from pydantic import Field

# Support both package imports (.) and direct imports (models)
try:
    from .base_model import RenderableModel
    from .doc_model import Doc
    from .feature_model import Feature
except ImportError:
    from base_model import RenderableModel
    from doc_model import Doc
    from feature_model import Feature


class Spec(RenderableModel):
    """Renderable specification document with features and versioning.

    Spec documents organize features with version control and detailed descriptions.
    Each spec includes a description and optional features that define the specification scope.
    """

    type: Literal["Spec"] = "Spec"
    model_version: int = 1
    version: int = Field(..., description="Specification version number")
    description: Doc = Field(..., description="Detailed specification description as a Doc")
    features: Optional[Dict[str, Feature]] = Field(
        None, description="Features indexed by feature ID"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata (created_at, updated_at, etc.)"
    )

    @classmethod
    def create_default(cls) -> "Spec":
        """Create a default Spec instance."""
        description = Doc(id="description", label="Specification Description", metadata={})
        return cls(version=1, description=description, features=None)

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

        # Spec header with version
        lines.append(f"# Specification (v{self.version})")
        lines.append("")

        # Render description Doc
        lines.append("## Description")
        lines.append("")
        description_markdown = self.description.render(include_toc=False)
        lines.append(description_markdown)
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

        # Render metadata
        if self.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in self.metadata.items():
                lines.append(f"- {key}: {value}")
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

        if self.metadata:
            toc_lines.append("- [Metadata](#metadata)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Spec can be created as a root document.

        Returns:
            True - Spec can be a root document.
        """
        return True


Spec.model_rebuild()
