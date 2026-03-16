#!/usr/bin/env python3
"""Unified Metadata model for all Pydantic models."""

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """Unified metadata for all models with version and update tracking.

    Fields:
    - created_at: Timestamp when model was created (immutable, set at creation)
    - ver: Version number, incremented on parent object changes (immutable in snapshots)
    - updated_at: Timestamp of last update (immutable in snapshots)

    The ver and updated_at fields are marked with exclude=True to prevent
    modification through snapshot/patch operations. These are set programmatically
    during postprocessing to ensure consistency.
    """

    created_at: str = Field(..., description="ISO8601 timestamp when model was created")
    ver: int = Field(
        default=0,
        exclude=True,
        description="Version number (incremented on parent changes, cannot be modified via snapshot)"
    )
    updated_at: str = Field(
        default="",
        exclude=True,
        description="ISO8601 timestamp of last update (set on parent changes, cannot be modified via snapshot)"
    )

    class Config:
        """Pydantic config for Metadata model."""
        # Allow excluding fields even though they have defaults
        validate_default = True
