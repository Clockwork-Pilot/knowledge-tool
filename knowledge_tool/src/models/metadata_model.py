#!/usr/bin/env python3
"""Unified Metadata model for all Pydantic models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


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

    created_at: Optional[str] = Field(None, description="ISO8601 timestamp when model was created")
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

    model_config = ConfigDict(extra='allow', validate_default=True)

    @classmethod
    def now(cls, **kwargs) -> "Metadata":
        """Create Metadata with created_at set to the current ISO timestamp."""
        return cls(created_at=datetime.now().isoformat(), **kwargs)
