#!/usr/bin/env python3
"""Feature, Constraints, and Test models for constraint validation and result tracking."""

import re
from datetime import datetime
from typing import Any, Dict, Optional, Literal, Pattern, Union
from pydantic import BaseModel, Field, model_validator

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
except ImportError:
    from models import RenderableModel


class ConstraintBash(BaseModel):
    """Bash command constraint."""

    id: str = Field(..., description="Unique constraint identifier")
    cmd: str = Field(..., description="Bash command to execute")
    description: str = Field(..., description="Description of the constraint")
    scope: str = Field(default="local", description="Scope of the constraint (local, global, etc.)")

    def create_result(self, verdict: bool, output: str) -> "ConstraintBashResult":
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

    def create_result(self) -> "ConstraintPromptResult":
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


class ConstraintBashResult(BaseModel):
    """Result of executing a bash constraint."""

    constraint_id: str = Field(..., description="ID of the constraint that was executed")
    verdict: bool = Field(..., description="Whether the constraint passed (True) or failed (False)")
    shrunken_output: str = Field(..., description="Truncated stdout/stderr output")
    timestamp: Optional[datetime] = Field(None, description="When the constraint was executed")


class ConstraintPromptResult(BaseModel):
    """Result of executing a prompt constraint."""

    constraint_id: str = Field(..., description="ID of the constraint that was executed")
    verdict: str = Field(..., description="LLM's verdict (to be matched against verdict_expect_rule)")
    short_answer: str = Field(..., description="LLM's short answer/reasoning")
    timestamp: Optional[datetime] = Field(None, description="When the constraint was executed")


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


class Constraints(RenderableModel):
    """Root document for project-level features and constraints."""

    type: Literal["Constraints"] = "Constraints"
    features: Optional[Dict[str, "Feature"]] = Field(None, description="Features indexed by feature ID")
    constraints: Optional[Dict[str, Constraint]] = Field(None, description="Constraints indexed by constraint ID (bash or prompt)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata (created_at, updated_at, etc.)"
    )

    @classmethod
    def create_default(cls) -> "Constraints":
        """Create a default Constraints instance."""
        return cls()

    def render(self, include_toc: bool = True) -> str:
        """Render Constraints to markdown string.

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

        # Render constraints (standalone, not embedded in features)
        if self.constraints:
            lines.append("## Standalone Constraints")
            lines.append("")

            bash_constraints = {}
            prompt_constraints = {}

            for constraint_id, constraint in self.constraints.items():
                if constraint.constraint_bash:
                    bash_constraints[constraint_id] = constraint
                elif constraint.constraint_prompt:
                    prompt_constraints[constraint_id] = constraint

            if bash_constraints:
                lines.append("### Bash Constraints")
                lines.append("")
                for constraint_id, constraint in bash_constraints.items():
                    bash = constraint.constraint_bash
                    lines.append(f"#### {constraint_id}: {bash.description}")
                    lines.append(f"**Scope:** {bash.scope}")
                    lines.append(f"**Command:** `{bash.cmd}`")
                    lines.append("")

            if prompt_constraints:
                lines.append("### Prompt Constraints")
                lines.append("")
                for constraint_id, constraint in prompt_constraints.items():
                    prompt = constraint.constraint_prompt
                    lines.append(f"#### {constraint_id}: {prompt.description}")
                    lines.append(f"**Scope:** {prompt.scope}")
                    lines.append(f"**Prompt:** {prompt.prompt}")
                    lines.append(f"**Expected Verdict Pattern:** `{prompt.verdict_expect_rule}`")
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
        """Generate table of contents for constraints document.

        Returns:
            List of TOC lines with feature and constraint links.
        """
        toc_lines = []

        if self.features:
            toc_lines.append("- [Features](#features)")
            for feature_id in self.features.keys():
                toc_lines.append(f"  - [{feature_id}](#{feature_id})")

        if self.constraints:
            toc_lines.append("- [Standalone Constraints](#standalone-constraints)")

        if self.metadata:
            toc_lines.append("- [Metadata](#metadata)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Constraints can be created as a root document.

        Returns:
            True - Constraints can be root documents.
        """
        return True


class Tests(RenderableModel):
    """Root document for constraint execution results."""

    type: Literal["Tests"] = "Tests"
    constraints_results: Optional[Dict[str, Union[ConstraintBashResult, ConstraintPromptResult]]] = Field(
        None, description="Constraint execution results indexed by constraint ID"
    )

    @classmethod
    def create_default(cls) -> "Tests":
        """Create a default Tests instance."""
        return cls()

    def render(self, include_toc: bool = True) -> str:
        """Render Tests to markdown string.

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

        # Organize results by type
        if self.constraints_results:
            bash_results = {}
            prompt_results = {}

            for constraint_id, result in self.constraints_results.items():
                if isinstance(result, ConstraintBashResult):
                    bash_results[constraint_id] = result
                elif isinstance(result, ConstraintPromptResult):
                    prompt_results[constraint_id] = result

            if bash_results or prompt_results:
                lines.append("## Constraint Results")
                lines.append("")

            if bash_results:
                lines.append("### Bash Constraints")
                lines.append("")
                for constraint_id, result in bash_results.items():
                    verdict_str = "✓ PASS" if result.verdict else "✗ FAIL"
                    lines.append(f"#### {constraint_id}")
                    lines.append(f"**Verdict:** {verdict_str}")
                    if result.timestamp:
                        lines.append(f"**Timestamp:** {result.timestamp.isoformat()}")
                    if result.shrunken_output:
                        lines.append(f"**Output:** `{result.shrunken_output}`")
                    lines.append("")

            if prompt_results:
                lines.append("### Prompt Constraints")
                lines.append("")
                for constraint_id, result in prompt_results.items():
                    lines.append(f"#### {constraint_id}")
                    lines.append(f"**Verdict:** {result.verdict or '(empty)'}")
                    if result.short_answer:
                        lines.append(f"**Answer:** {result.short_answer}")
                    if result.timestamp:
                        lines.append(f"**Timestamp:** {result.timestamp.isoformat()}")
                    lines.append("")

        return "\n".join(lines).strip()

    def render_toc(self) -> list:
        """Generate table of contents for constraint results.

        Returns:
            List of TOC lines with result links.
        """
        toc_lines = []

        if self.constraints_results:
            bash_results = sum(1 for r in self.constraints_results.values() if isinstance(r, ConstraintBashResult))
            prompt_results = sum(1 for r in self.constraints_results.values() if isinstance(r, ConstraintPromptResult))

            if bash_results or prompt_results:
                toc_lines.append("- [Constraint Results](#constraint-results)")
                if bash_results:
                    toc_lines.append("  - [Bash Constraints](#bash-constraints)")
                if prompt_results:
                    toc_lines.append("  - [Prompt Constraints](#prompt-constraints)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Tests can be created as a root document.

        Returns:
            True - Tests can be root documents.
        """
        return True
