#!/usr/bin/env python3
"""Feature model - renderable feature with embedded constraints."""

from typing import Any, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
    from .constraints_model import ConstraintBash
except ImportError:
    from models import RenderableModel
    from constraints_model import ConstraintBash


class Feature(RenderableModel):
    """Renderable feature with embedded bash and/or prompt constraints.

    Features are self-contained, documentable units with multiple validation checks.
    Each constraint (bash or prompt) validates the feature's requirements.
    """

    type: Literal["Feature"] = "Feature"
    model_version: int = 1
    id: str = Field(..., description="Unique feature identifier")
    description: str = Field(..., description="Feature description")
    goals: Optional[list[str]] = Field(
        None, description="List of goals/objectives for this feature"
    )
    constraints: Optional[Dict[str, ConstraintBash]] = Field(
        None, description="Embedded constraints (bash commands)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata (created_at, updated_at, etc.)"
    )

    @classmethod
    def create_default(cls) -> "Feature":
        """Create a default Feature instance."""
        return cls(id="feature_1", description="New feature", constraints=None)

    def render(self, include_toc: bool = True) -> str:
        """Render Feature to markdown string.

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

        # Feature header - use just ID for clean anchor generation
        lines.append(f"# Feature: {self.id}")
        lines.append(f"**{self.description}**")
        lines.append("")

        # Render goals if present
        if self.goals:
            lines.append("## Goals")
            lines.append("")
            for goal in self.goals:
                lines.append(f"- {goal}")
            lines.append("")

        # Render embedded constraints
        if self.constraints:
            lines.append("## Validation Constraints")
            lines.append("")
            for c_id, bash_c in self.constraints.items():
                lines.append(f"#### {c_id}")
                lines.append(f"**Description:** {bash_c.description}")
                lines.append(f"**Command:** `{bash_c.cmd}`")
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
        """Generate table of contents for feature.

        Includes sections for goals, validation constraints, and metadata.
        For constraints, uses their individual render_toc() methods to generate
        TOC entries.

        Returns:
            List of TOC lines.
        """
        toc_lines = []

        if self.goals:
            toc_lines.append("- [Goals](#goals)")

        if self.constraints:
            toc_lines.append("- [Validation Constraints](#validation-constraints)")
            for c_id, constraint in sorted(self.constraints.items()):
                for toc_line in constraint.render_toc():
                    toc_lines.append("  " + toc_line)

        if self.metadata:
            toc_lines.append("- [Metadata](#metadata)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Feature can be created as a root document.

        Returns:
            True - Feature can be root documents.
        """
        return True
