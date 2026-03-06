#!/usr/bin/env python3
"""API Response model for apply_json_patch operation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApplyPatchErrorResponse(BaseModel):
    """Error response for apply_json_patch operation. Success returns None."""

    error: str = Field(..., description="Error message")
    operation: str = Field(..., description="Operation name")

    # Error context fields
    hint: Optional[str] = Field(None, description="Helpful hint for error recovery")
    example: Optional[List[Dict[str, Any]]] = Field(None, description="Example for syntax errors")
    parent_path: Optional[str] = Field(None, description="Parent path for path errors")
    existing_children: Optional[List[str]] = Field(None, description="Available children for path errors")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="Validation error details")
