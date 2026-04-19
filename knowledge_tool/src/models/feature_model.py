#!/usr/bin/env python3
"""Feature model - renderable feature with embedded constraints."""

from typing import Any, Dict, Optional, Literal, Union, List
from pydantic import BaseModel, Field, model_validator, ValidationInfo

# Support both package imports (.) and direct imports (models)
try:
    from . import RenderableModel
    from .constraints_model import ConstraintBash
    from .metadata_model import Metadata
except ImportError:
    from models import RenderableModel
    from constraints_model import ConstraintBash
    from metadata_model import Metadata


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
    depends_on: Optional[List[str]] = Field(
        None, description="List of feature IDs this feature depends on"
    )
    constraints: Optional[Dict[str, ConstraintBash]] = Field(
        None, description="Embedded constraints (bash commands)"
    )
    metadata: Optional[Metadata] = Field(None, description="Metadata (created_at, updated_at, etc.)")

    @model_validator(mode='before')
    @classmethod
    def protect_proven_constraints_from_removal(cls, data: Any, info: ValidationInfo) -> Any:
        """Raise an error if any proven-failed constraint is being removed.

        Uses original_doc from validation context to detect removed constraints,
        then delegates the error to ConstraintBash.validate_removal.
        Supports both Spec (features at root) and Task (features in spec) documents.
        """
        context = getattr(info, 'context', None) if info else None
        if not context or not isinstance(data, dict):
            return data

        original_doc = context.get('original_doc', {})
        feature_id = data.get('id')
        if not feature_id or not original_doc:
            return data

        # Handle both document types:
        # - Spec type: features at root level (original_doc.features)
        # - Task type: features nested under spec (original_doc.spec.features)
        doc_type = original_doc.get('type')
        if doc_type == 'Spec':
            original_features = original_doc.get('features') or {}
        else:
            original_features = (original_doc.get('spec') or {}).get('features') or {}

        original_constraints = (original_features.get(feature_id) or {}).get('constraints') or {}
        new_constraints = data.get('constraints') or {}

        for cid, constraint_data in original_constraints.items():
            if cid not in new_constraints:
                ConstraintBash.validate_removal(constraint_data)  # raises ValueError if fails_count > 0
            else:
                # PROTECTION GUARD — DO NOT REMOVE OR WEAKEN THIS BLOCK.
                #
                # fails_count: LOCKED unconditionally via the model path. The only legitimate
                #              way to change fails_count is through check_spec_constraints.py's
                #              special flow, which writes JSON directly (bypassing model
                #              validation). Any model-mediated change — including 0 → N on an
                #              unverified constraint — is tampering.
                # cmd:         LOCKED once the constraint is verified (fails_count > 0). Changing
                #              cmd would silently invalidate the proof that it was ever red.
                fails_count = constraint_data.get('fails_count', 0)
                new_c = new_constraints[cid]
                new_cmd = new_c.get('cmd') if isinstance(new_c, dict) else None
                original_cmd = constraint_data.get('cmd')
                new_fails_count = new_c.get('fails_count', 0) if isinstance(new_c, dict) else 0

                if fails_count != new_fails_count:
                    raise ValueError(
                        f"Cannot modify fails_count for constraint '{cid}' "
                        f"({fails_count} -> {new_fails_count}): fails_count is only writable "
                        f"by check_spec_constraints.py."
                    )

                if fails_count > 0 and original_cmd and new_cmd and original_cmd != new_cmd:
                    raise ValueError(
                        f"Cannot update constraint '{cid}' cmd: fails_count={fails_count} > 0. "
                        f"Fix the constraint to pass first."
                    )

        # Reject brand-new constraints that arrive with fails_count > 0.
        # Only check_spec_constraints.py may write fails_count; smuggling a
        # pre-verified constraint through the patch flow is tampering.
        for cid, new_c in new_constraints.items():
            if cid in original_constraints or not isinstance(new_c, dict):
                continue
            new_fails_count = new_c.get('fails_count', 0) or 0
            if new_fails_count:
                raise ValueError(
                    f"Cannot create constraint '{cid}' with fails_count={new_fails_count}: "
                    f"fails_count is only writable by check_spec_constraints.py."
                )

        return data

    @model_validator(mode='before')
    @classmethod
    def validate_depends_on_references(cls, data: Any, info: ValidationInfo) -> Any:
        """Validate that all features in depends_on exist.

        Checks that each feature ID listed in depends_on is available in the document's
        features collection.
        """
        if not isinstance(data, dict):
            return data

        depends_on = data.get('depends_on')
        if not depends_on:
            return data

        # Validate it's a list of strings
        if not isinstance(depends_on, list):
            raise ValueError(f"depends_on must be a list, got {type(depends_on).__name__}")

        for feature_id in depends_on:
            if not isinstance(feature_id, str):
                raise ValueError(f"Feature IDs in depends_on must be strings, got {type(feature_id).__name__}")
            if not feature_id.strip():
                raise ValueError("Feature IDs in depends_on cannot be empty strings")

        # Try to get the full features list from context
        context = getattr(info, 'context', None) if info else None
        if not context:
            return data

        original_doc = context.get('original_doc', {})
        if not original_doc:
            return data

        # Handle both Spec (features at root) and Task (features in spec)
        doc_type = original_doc.get('type')
        if doc_type == 'Spec':
            available_features = (original_doc.get('features') or {}).keys()
        else:
            available_features = ((original_doc.get('spec') or {}).get('features') or {}).keys()

        # Validate each depends_on reference exists
        current_feature_id = data.get('id')
        for feature_id in depends_on:
            if feature_id not in available_features:
                raise ValueError(
                    f"Feature '{current_feature_id}' depends on '{feature_id}', "
                    f"but '{feature_id}' does not exist in the document"
                )

        return data

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
            for c_id, constraint in sorted(self.constraints.items()):
                lines.append(f"### {constraint.id}")
                lines.append(f"**Description:** {constraint.description}")

                # Render constraint-specific details
                if hasattr(constraint, 'cmd'):  # ConstraintBash
                    lines.append(f"**Command:** `{constraint.cmd}`")

                    # Show fails_count if present
                    if hasattr(constraint, 'fails_count') and constraint.fails_count:
                        lines.append(f"**Proven Failures:** {constraint.fails_count}")

                if hasattr(constraint, 'prompt'):  # ConstraintPrompt
                    lines.append(f"**Prompt:** {constraint.prompt[:100]}...")
                    if hasattr(constraint, 'verdict_expect_rule'):
                        lines.append(f"**Expected Verdict Pattern:** `{constraint.verdict_expect_rule}`")

                lines.append("")

        # Render metadata
        if self.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in self.metadata.model_dump(exclude_none=True).items():
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
                # Add constraint ID as anchor
                constraint_anchor = constraint.id.lower().replace(' ', '-')
                toc_lines.append(f"  - [{constraint.id}](#{constraint_anchor})")

        if self.metadata:
            toc_lines.append("- [Metadata](#metadata)")

        return toc_lines

    def is_can_be_root(self) -> bool:
        """Feature can be created as a root document.

        Returns:
            True - Feature can be root documents.
        """
        return True
