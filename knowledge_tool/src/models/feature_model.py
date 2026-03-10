#!/usr/bin/env python3
"""Feature model - renderable feature with embedded constraints."""

from typing import Any, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
    from .constraints_model import ConstraintBash, ConstraintPrompt
except ImportError:
    from models import RenderableModel
    from constraints_model import ConstraintBash, ConstraintPrompt


class Feature(RenderableModel):
    """Renderable feature with embedded bash and/or prompt constraints.

    Features are self-contained, documentable units with multiple validation checks.
    Each constraint (bash or prompt) validates the feature's requirements.
    """

    type: Literal["Feature"] = "Feature"
    id: str = Field(..., description="Unique feature identifier")
    description: str = Field(..., description="Feature description")
    constraints: Optional[Dict[str, Union[ConstraintBash, ConstraintPrompt]]] = Field(
        None, description="Embedded constraints (bash commands or LLM prompts)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata (created_at, updated_at, etc.)"
    )

    @classmethod
    def create_default(cls) -> "Feature":
        """Create a default Feature instance."""
        return cls(id="feature_1", description="New feature")

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

        # Feature header
        lines.append(f"# {self.id}: {self.description}")
        lines.append("")

        # Render embedded constraints
        if self.constraints:
            bash_constraints = {}
            prompt_constraints = {}

            for c_id, c in self.constraints.items():
                if isinstance(c, ConstraintBash):
                    bash_constraints[c_id] = c
                elif isinstance(c, ConstraintPrompt):
                    prompt_constraints[c_id] = c

            if bash_constraints or prompt_constraints:
                lines.append("## Validation Constraints")
                lines.append("")

            if bash_constraints:
                lines.append("### Bash Constraints")
                lines.append("")
                for c_id, bash_c in bash_constraints.items():
                    lines.append(f"#### {c_id}: {bash_c.description}")
                    lines.append(f"**Command:** `{bash_c.cmd}`")
                    lines.append("")

            if prompt_constraints:
                lines.append("### Prompt Constraints")
                lines.append("")
                for c_id, prompt_c in prompt_constraints.items():
                    lines.append(f"#### {c_id}: {prompt_c.description}")
                    lines.append(f"**Prompt:** {prompt_c.prompt}")
                    lines.append(f"**Expected Verdict:** `{prompt_c.verdict_expect_rule}`")
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

        Returns:
            List of TOC lines.
        """
        toc_lines = []

        if self.constraints:
            bash_count = sum(1 for c in self.constraints.values() if isinstance(c, ConstraintBash))
            prompt_count = sum(1 for c in self.constraints.values() if isinstance(c, ConstraintPrompt))

            if bash_count or prompt_count:
                toc_lines.append("- [Validation Constraints](#validation-constraints)")
                if bash_count:
                    toc_lines.append("  - [Bash Constraints](#bash-constraints)")
                if prompt_count:
                    toc_lines.append("  - [Prompt Constraints](#prompt-constraints)")

        if self.metadata:
            toc_lines.append("- [Metadata](#metadata)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Feature can be created as a root document.

        Returns:
            True - Feature can be root documents.
        """
        return True
