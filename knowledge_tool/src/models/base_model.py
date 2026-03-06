#!/usr/bin/env python3
"""Base model for all renderable model types."""

from abc import ABC, abstractmethod
from pydantic import BaseModel


class RenderableModel(BaseModel, ABC):
    """Abstract base model for all models that can render to markdown.

    All model types (Doc, Task, etc.) must inherit from this and implement render().
    The type field (as Literal in subclasses) determines which model class to instantiate.
    """

    type: str  # Subclasses override with Literal["ModelType"]

    @abstractmethod
    def render(self) -> str:
        """Render model to markdown string.

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
