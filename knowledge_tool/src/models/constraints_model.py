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

class ConstraintBash(BaseModel):
    """Bash command constraint with fail tracking and cmd protection."""

    id: str = Field(..., description="Unique constraint identifier")
    cmd: str = Field(..., description="Bash command to execute")
    description: str = Field(..., description="Description of the constraint")
    fails_count: int = Field(default=0, description="Count of failed constraint executions; prevents cmd updates when > 0")

    @classmethod
    def validate_removal(cls, data: dict) -> None:
        """Raise ValueError if this constraint cannot be removed.

        A constraint with fails_count > 0 has proven failure history and must
        be fixed to pass before it can be removed.

        Args:
            data: Raw constraint dict (from the document before patch)

        Raises:
            ValueError: If removal is forbidden due to fails_count > 0
        """
        fails_count = data.get("fails_count", 0)
        if fails_count > 0:
            cid = data.get("id", "unknown")
            raise ValueError(
                f"Cannot remove constraint '{cid}': fails_count={fails_count} > 0. "
                f"Fix the constraint to pass first."
            )

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
            'description': self.description,
        }
        if self.fails_count != 0:
            d['fails_count'] = self.fails_count
        return d

    @model_validator(mode='before')
    @classmethod
    def protect_cmd_when_failed(cls, data: Any, info: ValidationInfo) -> Any:
        """Protect constraint cmd and fails_count when fails_count > 0.

        Protection is enforced at the Feature level (feature_model.py) where the
        original constraints are scoped to the specific feature. This validator is
        a no-op kept for structural clarity.
        """
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

    def create_result(self, verdict: bool, output: str, duration: Optional[float] = None) -> ConstraintBashResult:
        """Create result from bash execution.

        Args:
            verdict: True if command passed (exit code 0), False otherwise
            output: Command stdout/stderr output
            duration: Execution duration in seconds

        Returns:
            ConstraintBashResult with verdict, output, duration, and current fails_count
        """
        return ConstraintBashResult(
            constraint_id=self.id,
            verdict=verdict,
            shrunken_output=output[:100],
            timestamp=datetime.now(),
            duration=duration,
            fails_count=self.fails_count
        )
