#!/usr/bin/env python3
"""Document model with pure rendering logic."""

import json
import re
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel

from .base_model import RenderableModel


class Opts(BaseModel):
    """Non-displayable options for document rendering behavior."""

    render_priority: bool = False
    render_toc: bool = False


class Doc(RenderableModel):
    """Document node with type-based extensibility and optional children."""

    id: str
    label: str
    type: Literal["Doc"] = "Doc"
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    opts: Optional[Opts] = None
    children: Optional[Dict[str, "Doc"]] = None

    def render(self, include_toc: bool = True) -> str:
        """Render Doc to markdown string.

        Args:
            include_toc: Whether to include TOC in rendering (default: True).
                        Set to False when rendering as a child of another document.

        Returns:
            Formatted markdown string representation.
        """
        doc_dict = json.loads(self.model_dump_json(exclude_none=True))
        lines = []
        self._render_node(doc_dict, lines, level=1)

        # Insert TOC if enabled in opts and include_toc is True
        opts = doc_dict.get("opts", {})
        if include_toc and opts.get("render_toc", False):
            toc_lines = self.render_toc()
            if toc_lines:
                # Find where to insert TOC (after heading and description)
                toc_insert_pos = 1
                # Skip past heading and any description
                for i, line in enumerate(lines[1:], 1):
                    if line.startswith("#") or line == "":
                        continue
                    toc_insert_pos = i
                    break

                lines.insert(toc_insert_pos, "")
                lines.insert(toc_insert_pos + 1, "## Table of Contents")
                lines.insert(toc_insert_pos + 2, "")
                lines[toc_insert_pos + 3:toc_insert_pos + 3] = toc_lines
                lines.insert(toc_insert_pos + 3 + len(toc_lines), "")

        markdown_content = "\n".join(lines)
        return markdown_content

    def render_toc(self) -> list:
        """Generate TOC for this Doc including metadata fields and children.

        Generates entries for:
        - Metadata field keys (rendered as sections)
        - Child nodes (rendered as nested headings)

        Returns:
            List of TOC lines with proper indentation and anchors.
        """
        doc_dict = json.loads(self.model_dump_json(exclude_none=True))
        toc_lines = []

        # Add TOC entries for metadata fields
        metadata = doc_dict.get("metadata", {})
        if metadata:
            for key in metadata.keys():
                # Format anchor: lowercase, spaces/underscores to hyphens, remove special chars
                anchor = key.lower()
                anchor = anchor.replace(" ", "-").replace("_", "-")
                anchor = re.sub(r'[^\w-]', '', anchor)

                formatted_key = Doc._format_key(key)
                toc_lines.append(f"- [{formatted_key}](#{anchor})")

        # Add TOC entries for children
        children = doc_dict.get("children", {})
        if children:
            sorted_children = Doc._sort_children_by_priority(children)
            for child_id, child_node in sorted_children:
                label = child_node.get("label", child_id)
                # Generate anchor matching standard markdown
                anchor = label.lower()
                anchor = anchor.replace(' ', '-')
                anchor = re.sub(r'[^\w-]', '', anchor)

                toc_lines.append(f"- [{label}](#{anchor})")

                # Recursively add child's TOC (its metadata and children)
                child_toc = Doc._generate_toc(child_node, level=2)
                if child_toc:
                    for line in child_toc:
                        toc_lines.append("  " + line)

        return toc_lines

    @staticmethod
    def _render_node(node: Dict[str, Any], lines: list, level: int = 1) -> None:
        """Recursively render a Doc node and its children.

        Args:
            node: Doc node dictionary
            lines: Output lines list
            level: Current heading level (1-6)
        """
        # Add heading for this node
        label = node.get("label", "Untitled")
        heading = "#" * level + " " + label
        lines.append(heading)

        # Add description if present (right after heading)
        description = node.get("description")
        if description:
            lines.append(description)
            lines.append("")

        # Add metadata information (skip opts field - non-displayable)
        metadata = node.get("metadata", {})
        if metadata:
            lines.extend(Doc._render_metadata(metadata))
            lines.append("")

        # Add children as list or recursively (sorted by render_priority)
        children = node.get("children", {})
        if children:
            # Sort children: render_priority=true first, then others
            sorted_children = Doc._sort_children_by_priority(children)

            if level >= 5:
                # For deep nesting, use bullet list instead of more headings
                lines.append("**Sections:**")
                lines.append("")
                for child_id, child_node in sorted_children:
                    child_label = child_node.get("label", child_id)
                    lines.append(f"- {child_label}")
                lines.append("")
            else:
                # Use heading levels for shallow nesting
                for child_id, child_node in sorted_children:
                    Doc._render_node(child_node, lines, level=level + 1)

    @staticmethod
    def _generate_toc(node: Dict[str, Any], level: int = 1, parent_label: str = "") -> list:
        """Generate table of contents lines from document structure.

        Args:
            node: Doc node dictionary
            level: Current heading level (1-6)
            parent_label: Label of parent node for context

        Returns:
            List of TOC lines
        """
        toc_lines = []

        children = node.get("children", {})
        if children:
            sorted_children = Doc._sort_children_by_priority(children)

            for child_id, child_node in sorted_children:
                label = child_node.get("label", child_id)
                # Generate anchor matching standard markdown: lowercase, spaces→hyphens, remove other special chars
                anchor = label.lower()
                anchor = anchor.replace(' ', '-')  # Convert spaces to hyphens first
                anchor = re.sub(r'[^\w-]', '', anchor)  # Then remove other special chars

                indent = "  " * (level - 1)
                toc_lines.append(f"{indent}- [{label}](#{anchor})")

                # Recursively add child's children
                child_toc = Doc._generate_toc(child_node, level + 1, label)
                toc_lines.extend(child_toc)

        return toc_lines

    @staticmethod
    def _sort_children_by_priority(children: Dict[str, Any]) -> list:
        """Sort children by render_priority (true first, then false/absent).

        Args:
            children: Dictionary of child nodes

        Returns:
            List of (child_id, child_node) tuples sorted by priority
        """

        def get_priority(item: tuple) -> bool:
            child_id, child_node = item
            opts = child_node.get("opts", {})
            return not opts.get("render_priority", False)  # False (priority) comes first

        return sorted(children.items(), key=get_priority)

    @staticmethod
    def _render_metadata(metadata: Dict[str, Any]) -> list:
        """Render metadata fields as formatted text with anchors for TOC linking.

        Args:
            metadata: Metadata dictionary

        Returns:
            List of formatted lines
        """
        lines = []
        description = metadata.get("description")
        code = metadata.get("code")
        first_field = True

        if code:
            lines.append("```")
            lines.append(str(code))
            lines.append("```")
            first_field = False

        if description:
            if not first_field:
                lines.append("")
            lines.append(str(description))
            first_field = False

        for key, value in metadata.items():
            if key in ("description", "code"):
                continue

            # Add empty line before each field
            if not first_field:
                lines.append("")
            first_field = False

            # Generate anchor for this field matching TOC anchor format
            anchor = key.lower()
            anchor = anchor.replace(" ", "-").replace("_", "-")
            anchor = re.sub(r'[^\w-]', '', anchor)
            formatted_key = Doc._format_key(key)

            # Add HTML anchor to enable TOC links
            lines.append(f"<a name=\"{anchor}\"></a>")

            if isinstance(value, list):
                lines.append(f"**{formatted_key}:**")
                # Check if list items already start with number pattern (1., 2., etc.)
                is_ordered = all(
                    isinstance(item, str) and re.match(r"^\d+\.\s", item)
                    for item in value
                )
                for item in value:
                    if is_ordered:
                        # Already numbered, render as-is
                        lines.append(f"  {item}")
                    else:
                        # Bullet list
                        lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"**{formatted_key}:**")
                for sub_key, sub_value in value.items():
                    lines.append(f"  - {Doc._format_key(sub_key)}: {sub_value}")
            elif value:
                lines.append(f"**{formatted_key}:** {value}")

        return lines

    @staticmethod
    def _format_key(key: str) -> str:
        """Format snake_case key to Title Case.

        Args:
            key: Input key string

        Returns:
            Formatted key
        """
        return key.replace("_", " ").title()

    def tips(self, json_path: str = "") -> list:
        """Check for best practice violations and return tips recursively.

        Checks this document and all children for best practice violations.

        Args:
            json_path: Current JSON path in document tree (e.g., /children/scripts/children/task_create)

        Returns:
            List of tip strings about best practices.
        """
        tips = []

        # Build current JSON path
        current_json_path = f"{json_path}/children/{self.id}" if json_path else f"/{self.id}"

        # Check this document's metadata
        if self.metadata:
            metadata_lower = {k.lower(): k for k, v in self.metadata.items()}  # Map to original key

            # Check for usage/command in metadata - should be in code attr
            # for key_lower, key_orig in metadata_lower.items():
            #     if key_lower in ("usage", "command"):
            #         full_path = f"{current_json_path}/metadata/{key_orig}"
            #         tips.append(
            #             f'⚠️  {full_path}: Found "{key_lower}" in metadata. '
            #             'Move to top-level "code" attribute.'
            #         )

            # Check for description in metadata - should use top-level field
            if "description" in metadata_lower:
                key_orig = metadata_lower["description"]
                full_path = f"{current_json_path}/metadata/{key_orig}"
                tips.append(
                    f'⚠️  {full_path}: Found "description" in metadata. '
                    'Use top-level "description" attribute instead.'
                )

        # Recursively check children
        if self.children:
            for child in self.children.values():
                tips.extend(child.tips(json_path=current_json_path))

        return tips


Doc.model_rebuild()
