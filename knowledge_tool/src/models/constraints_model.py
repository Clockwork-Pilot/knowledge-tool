#!/usr/bin/env python3
"""Feature, Constraints, and Test models for constraint validation."""

import re
from datetime import datetime
from typing import Any, Dict, Optional, Literal, Pattern, Union
from pydantic import BaseModel, Field, model_validator

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
    from .results_model import ConstraintBashResult, ConstraintPromptResult, ChecksResults
except ImportError:
    from models import RenderableModel
    from results_model import ConstraintBashResult, ConstraintPromptResult, ChecksResults


class ConstraintBash(BaseModel):
    """Bash command constraint."""

    id: str = Field(..., description="Unique constraint identifier")
    cmd: str = Field(..., description="Bash command to execute")
    description: str = Field(..., description="Description of the constraint")
    scope: str = Field(default="local", description="Scope of the constraint (local, global, etc.)")

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
        lines.append(f"**Scope:** {self.scope}")
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


class ConstraintPrompt(BaseModel):
    """LLM prompt constraint with verdict validation."""

    id: str = Field(..., description="Unique constraint identifier")
    prompt: str = Field(..., description="Prompt to send to LLM")
    verdict_expect_rule: str = Field(..., description="Regex pattern to validate verdict against")
    description: str = Field(..., description="Description of the constraint")
    scope: str = Field(default="local", description="Scope of the constraint (local, global, etc.)")

    # Private field for cached compiled regex (not in JSON)
    _compiled_regex: Optional[Pattern] = None

    @model_validator(mode="after")
    def validate_regex(self) -> "ConstraintPrompt":
        """Validate that verdict_expect_rule is a valid regex."""
        try:
            re.compile(self.verdict_expect_rule)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern in verdict_expect_rule: {e}")
        return self

    def get_compiled_regex(self) -> Pattern:
        """Lazy-compile and cache the regex pattern.

        Returns:
            Compiled regex pattern.
        """
        if self._compiled_regex is None:
            self._compiled_regex = re.compile(self.verdict_expect_rule)
        return self._compiled_regex

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
        lines.append(f"**Type:** Prompt")
        lines.append(f"**Prompt:** {self.prompt}")
        lines.append(f"**Expected Verdict Pattern:** `{self.verdict_expect_rule}`")
        lines.append(f"**Scope:** {self.scope}")
        return "\n".join(lines)

    def render_toc(self) -> list:
        """Generate TOC entry for this constraint.

        Returns:
            List with single TOC entry for the constraint.
        """
        return [f"- [{self.id}](#{self.id.lower().replace('_', '-')})"]

    def create_result(self) -> ConstraintPromptResult:
        """Create empty result for prompt constraint.

        No LLM execution happens in the model layer. Returns placeholder
        ConstraintPromptResult with empty verdict and short_answer fields.

        Actual prompt evaluation happens at higher levels if needed.

        Returns:
            ConstraintPromptResult with constraint_id set, empty verdict/answer
        """
        return ConstraintPromptResult(
            constraint_id=self.id,
            verdict="",
            short_answer="",
            timestamp=datetime.now()
        )


class Constraint(BaseModel):
    """Wrapper for bash or prompt constraint (exactly one must be set)."""

    id: str = Field(..., description="Unique constraint identifier")
    scope: str = Field(default="local", description="Scope of the constraint")
    constraint_bash: Optional[ConstraintBash] = Field(None, description="Bash constraint (if type is bash)")
    constraint_prompt: Optional[ConstraintPrompt] = Field(None, description="Prompt constraint (if type is prompt)")

    @model_validator(mode="after")
    def validate_exactly_one_constraint(self) -> "Constraint":
        """Ensure exactly one of constraint_bash or constraint_prompt is set."""
        count = sum([
            self.constraint_bash is not None,
            self.constraint_prompt is not None
        ])
        if count != 1:
            raise ValueError("Exactly one of constraint_bash or constraint_prompt must be set")
        return self


class FeaturesScope(RenderableModel):
    """Root document for project-level features with a defined scope."""

    type: Literal["FeaturesScope"] = "FeaturesScope"
    model_version: int = 1
    scope: str = Field(..., description="Scope of this features collection (e.g., 'local', 'global', 'integration')")
    features: Optional[Dict[str, "Feature"]] = Field(None, description="Features indexed by feature ID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata (created_at, updated_at, etc.)"
    )

    @classmethod
    def create_default(cls) -> "FeaturesScope":
        """Create a default FeaturesScope instance."""
        return cls(scope="local", features=None)

    def render(self, include_toc: bool = True) -> str:
        """Render FeaturesScope to markdown string.

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

        # Render features
        if self.features:
            has_new_constraints = any(feature.constraints for feature in self.features.values())
            section_title = "## Features" if not has_new_constraints else "## Features (with Constraints)"
            lines.append(section_title)
            lines.append("")

            for feature_id, feature in self.features.items():
                lines.append(f"### {feature_id}: {feature.description}")
                lines.append("")

                # Render embedded constraints
                if feature.constraints:
                    lines.append("**Embedded Constraints:**")
                    lines.append("")

                    bash_constraints = {}
                    prompt_constraints = {}

                    for c_id, c in feature.constraints.items():
                        if isinstance(c, ConstraintBash):
                            bash_constraints[c_id] = c
                        elif isinstance(c, ConstraintPrompt):
                            prompt_constraints[c_id] = c

                    if bash_constraints:
                        lines.append("*Bash Constraints:*")
                        for c_id, bash_c in bash_constraints.items():
                            lines.append(f"  - {c_id}: `{bash_c.cmd}` ({bash_c.description})")
                        lines.append("")

                    if prompt_constraints:
                        lines.append("*Prompt Constraints:*")
                        for c_id, prompt_c in prompt_constraints.items():
                            lines.append(f"  - {c_id}: {prompt_c.description}")
                            lines.append(f"    Pattern: `{prompt_c.verdict_expect_rule}`")
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
        """Generate table of contents for FeaturesScope document.

        Returns:
            List of TOC lines with feature links.
        """
        toc_lines = []

        if self.features:
            toc_lines.append("- [Features](#features)")
            for feature_id in self.features.keys():
                toc_lines.append(f"  - [{feature_id}](#{feature_id})")

        if self.metadata:
            toc_lines.append("- [Metadata](#metadata)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """FeaturesScope can be created as a root document.

        Returns:
            True - FeaturesScope can be root documents.
        """
        return True
