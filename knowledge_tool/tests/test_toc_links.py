#!/usr/bin/env python3
"""Tests for TOC link validation in rendered markdown documents."""

import re
from pathlib import Path
import pytest


class TestTocLinks:
    """Test that table of contents links are valid and working."""

    @staticmethod
    def heading_to_id(heading: str) -> str:
        """Convert heading text to markdown ID.

        Matches Doc model's _generate_anchor() behavior:
        - Strip leading emojis (non-ASCII chars) to match _render_node() heading rendering
        - Convert to lowercase
        - Replace spaces with hyphens
        - Remove special characters (except hyphens and dots initially)
        - Remove dots for markdown compatibility
        - Clean up multiple hyphens
        - Strip leading/trailing hyphens

        Args:
            heading: Heading text (e.g., "# My Heading" or "## 🎯 Core Concept")
                     Leading markdown symbols (#) are ignored

        Returns:
            Markdown-compatible ID matching _generate_anchor() (e.g., "my-heading", "core-concept")

        Note:
            Duplicate headings are handled by _make_unique_anchor() in the Doc model,
            which appends -2, -3, etc. suffixes for collisions.
        """
        # Remove markdown formatting
        heading = re.sub(r'\*\*(.+?)\*\*', r'\1', heading)  # Remove bold
        heading = re.sub(r'`(.+?)`', r'\1', heading)  # Remove code

        # Strip emojis (any non-ASCII characters at start and surrounding whitespace)
        # This matches _render_node() which strips emojis for heading display
        heading = re.sub(r'^[^\x00-\x7F]+\s*', '', heading)

        # Convert to lowercase
        anchor = heading.lower().strip()
        # Replace spaces with hyphens
        anchor = anchor.replace(' ', '-')
        # Remove dots for standard markdown compatibility
        anchor = anchor.replace('.', '')
        # Remove parentheses and other special chars, but keep hyphens
        anchor = re.sub(r'[^\w\-.]', '', anchor)
        # Clean up multiple hyphens
        anchor = re.sub(r'-+', '-', anchor)
        # Remove leading/trailing hyphens
        anchor = anchor.strip('-')

        return anchor

    def test_knowledge_tool_toc_links(self):
        """Test that all TOC links in knowledge_tool.md are valid."""
        md_path = Path(__file__).parent.parent.parent / "knowledge_tool.md"

        assert md_path.exists(), f"knowledge_tool.md not found at {md_path}"

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self._validate_toc_links(content, "knowledge_tool.md")

    def _validate_toc_links(self, content: str, doc_name: str = "document"):
        """Validate that all TOC links in markdown content are valid.

        Handles duplicate headings with numeric suffixes (-2, -3, etc.) as implemented
        in Doc._make_unique_anchor(). When the same base anchor ID appears multiple times:
        - First occurrence: uses base anchor (e.g., "benefit")
        - Second occurrence: appends -2 (e.g., "benefit-2")
        - Third occurrence: appends -3 (e.g., "benefit-3"), etc.

        Args:
            content: Markdown content to validate
            doc_name: Name of document for error messages
        """
        # Extract all TOC links: [text](#anchor)
        toc_links = re.findall(r'\]\(#([^)]+)\)', content)
        assert len(toc_links) > 0, f"No TOC links found in {doc_name}"

        # Extract all heading texts: # Heading, ## Sub Heading, etc.
        headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        assert len(headings) > 0, f"No headings found in {doc_name}"

        # Generate base IDs from headings
        base_ids = [self.heading_to_id(h) for h in headings]

        # Build set of valid anchor IDs including duplicates with suffixes
        valid_ids = set()
        id_counts = {}
        for base_id in base_ids:
            if base_id not in id_counts:
                id_counts[base_id] = 1
                valid_ids.add(base_id)
            else:
                id_counts[base_id] += 1
                # Add numbered duplicate suffix
                for i in range(2, id_counts[base_id] + 1):
                    valid_ids.add(f"{base_id}-{i}")

        toc_links_set = set(toc_links)

        # Find broken links
        broken = toc_links_set - valid_ids
        working = toc_links_set & valid_ids

        # Report results
        assert len(broken) == 0, (
            f"Found {len(broken)} broken TOC link(s) in {doc_name}: {sorted(broken)}\n"
            f"Working links: {len(working)}"
        )

        # Success message (visible with -v flag)
        print(f"\n✓ TOC validation ({doc_name}): {len(working)} links working, 0 broken")

    def test_no_duplicate_toc_links(self):
        """Test that TOC doesn't have duplicate links."""
        md_path = Path(__file__).parent.parent.parent / "knowledge_tool.md"

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract all TOC links
        toc_links = re.findall(r'\]\(#([^)]+)\)', content)

        # Check for duplicates
        duplicates = [link for link in set(toc_links) if toc_links.count(link) > 1]

        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate TOC link(s): {duplicates}"
        )

    def test_heading_consistency(self):
        """Test that special character handling is consistent in headings and anchors."""
        md_path = Path(__file__).parent.parent.parent / "knowledge_tool.md"

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all headings with special characters
        special_char_headings = re.findall(
            r'^#+\s+(.+[.()_-].+)$',
            content,
            re.MULTILINE
        )

        # Verify each can be converted to a valid anchor
        for heading in special_char_headings:
            anchor = self.heading_to_id(heading)
            # Anchor should not be empty and should be valid markdown
            assert len(anchor) > 0, f"Invalid anchor generated from heading: {heading}"
            # Anchor should only contain word characters and hyphens
            assert re.match(r'^[\w-]+$', anchor), (
                f"Anchor contains invalid characters: {anchor} (from {heading})"
            )

    def test_emoji_heading_handling(self):
        """Test that emoji-prefixed headings generate correct anchors.

        Verifies that:
        - TOC links with emoji labels point to emoji-stripped heading anchors
        - Emoji stripping is consistent between TOC generation and heading rendering
        - Doc model correctly strips leading emojis for display and anchor generation
        """
        # Test cases: (heading_with_emoji, expected_anchor)
        test_cases = [
            ("🎯 Core Concept", "core-concept"),
            ("🏗️ Architecture", "architecture"),
            ("📡 Sentinel Protocol", "sentinel-protocol"),
            ("⚙️ Core Components", "core-components"),
            ("🗂️ FIFO Convention", "fifo-convention"),
            ("📊 Benefits vs Polling", "benefits-vs-polling"),
            ("📝 Usage Workflow", "usage-workflow"),
            ("✅ Testing", "testing"),
            ("🔄 Removed from Polling", "removed-from-polling"),
        ]

        for heading, expected_anchor in test_cases:
            anchor = self.heading_to_id(heading)
            assert anchor == expected_anchor, (
                f"Heading '{heading}' generated '{anchor}' but expected '{expected_anchor}'"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
