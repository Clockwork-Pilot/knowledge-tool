#!/usr/bin/env python3
"""Test-only models for knowledge_tool testing.

This module contains custom model implementations used only for testing
the pluggable model system. These models should NOT be mixed with the
main knowledge_tool models (Doc, Task, etc.) in production.

The models here are registered via conftest.py for test purposes only.
"""

from typing import Literal, Optional, Dict, Any
from pydantic import Field
from knowledge_tool.models import RenderableModel


class TestModel(RenderableModel):
    """Test model for external/pluggable models."""

    __test__ = False  # Prevent pytest from trying to collect this as a test class

    type: Literal["TestModel"] = "TestModel"
    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Title")
    description: Optional[str] = Field(None, description="Description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")

    def render(self) -> str:
        """Render the test model to markdown."""
        lines = []
        lines.append(f"# {self.title}")

        if self.description:
            lines.append("")
            lines.append(self.description)

        if self.metadata:
            lines.append("")
            lines.append("## Metadata")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}**: {value}")

        return "\n".join(lines)

    def tips(self) -> list:
        """Return tips for using Test model."""
        return [
            "✓ Test: Pluggable model loaded successfully"
        ]
