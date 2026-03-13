#!/usr/bin/env python3
"""Base model for all renderable model types."""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class RenderableModel(BaseModel, ABC):
    """Abstract base model for all models that can render to markdown.

    All model types (Doc, Task, etc.) must inherit from this and implement render().
    The type field (as Literal in subclasses) determines which model class to instantiate.
    """

    type: str  # Subclasses override with Literal["ModelType"]
    model_version: int = Field(..., description="Model schema version for data migrations")

    @abstractmethod
    def render(self, include_toc: bool = True) -> str:
        """Render model to markdown string.

        Args:
            include_toc: Whether to include TOC in rendering (default: True).
                        Set to False when rendering as a child of another document.

        Returns:
            Formatted markdown string representation of the model.
        """
        pass

    def tips(self) -> list:
        """Return list of best practice tips/warnings for this model.

        Returns:
            List of tip strings, or empty list if no tips. Override in subclasses.
        """
        return []

    def render_toc(self) -> list:
        """Generate table of contents lines for this model's structure.

        Subclasses override to provide TOC based on their structure.
        TOC lines are markdown-formatted with proper indentation and anchors.

        Returns:
            List of TOC lines (empty list if no TOC applicable).
        """
        return []

    def is_can_be_root(self) -> bool:
        """Indicate whether this model can be created as a root document.

        Root documents can be created directly using create_knowledge_document.py.
        Non-root models can only exist as children of other documents.

        Returns:
            True if this model can be a root document, False otherwise.
        """
        return False  # Default: models must explicitly opt-in to be root
