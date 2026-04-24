#!/usr/bin/env python3
"""Project model - top-level index of specs spread across a project."""

from typing import Dict, Literal
from pydantic import BaseModel, Field

try:
    from .base_model import RenderableModel
except ImportError:
    from base_model import RenderableModel


class EnvVar(BaseModel):
    """One environment variable entry in a SpecRef's envs dict.

    `value` is the string assigned to the env var at check time. `info` is
    a human-readable note documenting what the env is for and why it is set
    — it has no runtime effect but is rendered into the project markdown.
    """

    value: str = Field(description="Environment variable value")
    info: str = Field(
        default="",
        description="Human-readable note about what this env is for",
    )


class SpecRef(BaseModel):
    """Reference to one spec inside a Project.

    Only used as the value type of `Project.specs`; not a standalone document.

    `spec_dir` is the directory that holds the spec file. It may be relative
    to the project file (typical) or absolute. An empty string or "." means
    the project file's own directory — i.e. the current PROJECT_ROOT.

    The envs dict declares environment variables applied to this spec's
    constraint commands at check time. Each entry is an `EnvVar` carrying
    both the `value` applied at check time and a human-readable `info`
    note. They layer on top of the defaults, so they can override
    PROJECT_ROOT if an explicit value is desired.
    """

    spec_dir: str = Field(
        default="",
        description='Directory containing the spec (relative to project file, or absolute). '
                    'Empty or "." means the project file\'s directory.',
    )
    envs: Dict[str, EnvVar] = Field(
        default_factory=dict,
        description="Environment variables set for this spec's constraint commands",
    )


class Project(RenderableModel):
    """Top-level project document aggregating specs across a repository.

    Each entry in `specs` is keyed by a spec id (e.g. 'claude-plugin') and
    points at a spec file with its envs. The envs are metadata at this layer:
    downstream tools (e.g. the constraints checker) apply them when running
    each spec's constraints.
    """

    type: Literal["Project"] = "Project"
    model_version: int = 1
    name: str = Field(default="", description="Project name")
    description: str = Field(default="", description="Project description")
    specs: Dict[str, SpecRef] = Field(
        default_factory=dict,
        description="Spec id -> SpecRef (path + envs)",
    )

    @classmethod
    def create_default(cls) -> "Project":
        """Create a default Project instance."""
        return cls(name="Project", description="Project description", specs={})

    def render(self, include_toc: bool = True) -> str:
        """Render Project to markdown with a list of specs and their envs.

        The include_toc argument is accepted for interface compatibility but
        Project does not emit a TOC.
        """
        lines = [f"# {self.name or 'Project'}", ""]

        if self.description:
            lines.append("## Overview")
            lines.append("")
            lines.append(self.description)
            lines.append("")

        if self.specs:
            lines.append("## Specs")
            lines.append("")
            for spec_id, ref in sorted(self.specs.items()):
                lines.append(f"### {spec_id}")
                lines.append(f"**Spec dir:** `{ref.spec_dir or '.'}`")
                lines.append("")
                if ref.envs:
                    lines.append("**Envs:**")
                    for key, entry in sorted(ref.envs.items()):
                        suffix = f" — {entry.info}" if entry.info else ""
                        lines.append(f"- `{key}`: `{entry.value}`{suffix}")
                    lines.append("")

        return "\n".join(lines).strip()

    def is_can_be_root(self) -> bool:
        """Project can be created as a root document."""
        return True


Project.model_rebuild()
