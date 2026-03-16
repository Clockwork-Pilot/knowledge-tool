#!/usr/bin/env python3
"""Feature, Constraints, and Test models for constraint validation."""

import re
from datetime import datetime
from typing import Any, Dict, Optional, Literal, Pattern, Union
from pydantic import BaseModel, Field, model_validator

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
    from .results_model import ConstraintBashResult, ChecksResults
except ImportError:
    from models import RenderableModel
    from results_model import ConstraintBashResult, ChecksResults


class ConstraintBash(BaseModel):
    """Bash command constraint with 2-phase validation support."""

    id: str = Field(..., description="Unique constraint identifier")
    cmd: str = Field(..., description="Bash command to execute")
    description: str = Field(..., description="Description of the constraint")

    def render(self, include_toc: bool = True) -> str:
        """Render constraint to markdown string.

        Args:
            include_toc: Whether to include TOC (not used for constraints)

        Returns:
            Formatted markdown string representation.
        """
        lines = []
        lines.append(f"#### {self.id}")
        lines.append(f"**Description:** {self.description}")
        lines.append(f"**Type:** Bash")
        lines.append(f"**Command:** `{self.cmd}`")
        return "\n".join(lines)

    def render_toc(self) -> list:
        """Generate TOC entry for this constraint.

        Returns:
            List with single TOC entry for the constraint.
        """
        return [f"- [{self.id}](#{self.id.lower().replace('_', '-')})"]

    def create_result(self, verdict: bool, output: str) -> ConstraintBashResult:
        """Create result from bash execution.

        Args:
            verdict: True if command passed (exit code 0), False otherwise
            output: Command stdout/stderr output

        Returns:
            ConstraintBashResult with verdict and truncated output
        """
        return ConstraintBashResult(
            constraint_id=self.id,
            verdict=verdict,
            shrunken_output=output[:500],
            timestamp=datetime.now()
        )
