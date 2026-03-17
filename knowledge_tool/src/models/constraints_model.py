#!/usr/bin/env python3
"""Feature, Constraints, and Test models for constraint validation."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal, Pattern, Union
from pydantic import BaseModel, Field, model_validator, ValidationInfo, model_serializer

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
    from .results_model import ConstraintBashResult, ChecksResults
except ImportError:
    from models import RenderableModel
    from results_model import ConstraintBashResult, ChecksResults

# define tags list
LiteralTags = Literal["structure", "API", "logic"]

class ConstraintBash(BaseModel):
    """Bash command constraint with fail tracking and cmd protection."""

    id: str = Field(..., description="Unique constraint identifier")
    cmd: str = Field(..., description="Bash command to execute")
    tags: List[LiteralTags] = Field(default=[], description="List of tags for the constraint")
    description: str = Field(..., description="Description of the constraint")
    fails_count: int = Field(default=0, description="Count of failed constraint executions; prevents cmd updates when > 0")

    def increment_fails_count(self) -> None:
        """Increment the fail count when constraint execution fails.

        After fails_count > 0, the cmd field becomes locked and cannot be changed.
        The constraint can only be deleted entirely.
        """
        self.fails_count += 1

    @model_serializer
    def serialize(self) -> dict:
        """Serialize model, omitting fails_count when it is the default value (0)."""
        d = {
            'id': self.id,
            'cmd': self.cmd,
            'tags': self.tags,
            'description': self.description,
        }
        if self.fails_count != 0:
            d['fails_count'] = self.fails_count
        return d

    @model_validator(mode='before')
    @classmethod
    def protect_cmd_when_failed(cls, data: Any, info: ValidationInfo) -> Any:
        """Document cmd protection when fails_count > 0.

        When fails_count > 0 (constraint has failed), the cmd field is locked.
        Attempts to change it will fail during patch application.
        """
        # Note: Protection is enforced at patch application level, not during model loading.
        # This allows constraints to be loaded from JSON while still preventing cmd changes
        # through explicit patch operations.
        return data

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
            ConstraintBashResult with verdict, output, and current fails_count
        """
        return ConstraintBashResult(
            constraint_id=self.id,
            verdict=verdict,
            shrunken_output=output[:100],
            timestamp=datetime.now(),
            fails_count=self.fails_count
        )
