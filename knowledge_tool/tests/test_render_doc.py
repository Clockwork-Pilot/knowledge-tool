#!/usr/bin/env python3
"""Tests for Doc model rendering functionality and external model support."""

import json
import os
import sys
import tempfile
from pathlib import Path
import pytest

# pytest adds src to pythonpath via pyproject.toml
# conftest.py also adds test_models to pythonpath
from models import Doc
from common.render import render

# TestModel is loaded by conftest.py and available as a direct import
# (conftest adds test_models dir to sys.path, and test_models/models.py is handled)
test_models_module_path = Path(__file__).parent / "test_models" / "models.py"
import importlib.util
spec = importlib.util.spec_from_file_location("test_models_module", str(test_models_module_path))
test_models_module_loaded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_models_module_loaded)
TestModel = test_models_module_loaded.TestModel


class TestDocRender:
    """Test Doc model render() method."""

    def test_render_document_with_structure(self):
        """Test rendering a document with metadata and nested structure."""
        doc = Doc(
            id="test",
            label="Test Document",
            metadata={
                "description": "A test document",
                "version": "1.0"
            },
            children={
                "section1": Doc(
                    id="section1",
                    label="First Section",
                    metadata={"status": "complete"}
                )
            }
        )

        result = doc.render()

        assert result is not None
        assert "# Test Document" in result
        assert "## First Section" in result
        assert "A test document" in result
        assert "1.0" in result

    def test_render_writes_md_file(self):
        """Test that render() function creates a .md file from JSON."""
        doc = Doc(
            id="test",
            label="Test Document",
            metadata={"description": "A test"}
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(doc.model_dump(), f)
            temp_path = f.name

        try:
            # Use render() function which handles file I/O
            result = render(temp_path)

            assert result is not None
            md_path = Path(temp_path).with_suffix(".md")
            assert md_path.exists()

            md_content = md_path.read_text()
            assert "# Test Document" in md_content
            assert "A test" in md_content
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)


class TestRenderWithExternalModels:
    """Test rendering with pluggable external models."""

    @pytest.fixture
    def test_models_path(self):
        """Path to test models for testing external/pluggable models."""
        # Get path to test_models directory
        return str(Path(__file__).parent / "test_models")

    def test_render_with_external_models(self, test_models_path):
        """Test rendering a custom Test model using external models configured via env var."""
        test_model = TestModel(
            id="test_1",
            title="Test Document",
            description="A test document",
            metadata={"status": "active"}
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(test_model.model_dump(), f)
            temp_path = f.name

        try:
            # Set environment variable to point to test models
            old_root = os.environ.get('KNOWLEDGE_TOOL_CONFIG_ROOT')
            try:
                os.environ['KNOWLEDGE_TOOL_CONFIG_ROOT'] = str(Path(test_models_path).parent)

                # Render with external models configured
                result = render(temp_path)

                assert result is not None
                assert "# Test Document" in result
                assert "A test document" in result

                # Verify markdown file was created
                md_path = Path(temp_path).with_suffix(".md")
                assert md_path.exists()

                md_content = md_path.read_text()
                assert "# Test Document" in md_content
                assert "## Metadata" in md_content
                assert "status" in md_content
            finally:
                # Restore original environment
                if old_root is not None:
                    os.environ['KNOWLEDGE_TOOL_CONFIG_ROOT'] = old_root
                else:
                    os.environ.pop('KNOWLEDGE_TOOL_CONFIG_ROOT', None)
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)

    def test_render_without_external_models_fails_for_unknown_type(self):
        """Test that rendering unknown model type without external models configured fails."""
        test_model = TestModel(
            id="test_1",
            title="Test Document"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(test_model.model_dump(), f)
            temp_path = f.name

        try:
            # Clear environment variable to ensure no external models are configured
            old_root = os.environ.get('KNOWLEDGE_TOOL_CONFIG_ROOT')
            try:
                os.environ.pop('KNOWLEDGE_TOOL_CONFIG_ROOT', None)

                # Render without external models should fail (return None)
                result = render(temp_path)
                assert result is None

                # Markdown file should not be created
                md_path = Path(temp_path).with_suffix(".md")
                assert not md_path.exists()
            finally:
                # Restore original environment
                if old_root is not None:
                    os.environ['KNOWLEDGE_TOOL_CONFIG_ROOT'] = old_root
        finally:
            Path(temp_path).unlink()
            Path(temp_path).with_suffix(".md").unlink(missing_ok=True)


class TestIterationRender:
    """Test Iteration model render() method with children."""

    def test_iteration_render_with_children(self):
        """Test rendering an Iteration with child documents."""
        from models import Iteration

        child_doc = Doc(
            id="summary",
            label="Summary",
            description="Fixed authentication bug and improved performance"
        )

        iteration = Iteration(
            id="iteration_1",
            children={"summary": child_doc}
        )

        rendered = iteration.render()

        assert "### iteration_1" in rendered
        assert "Fixed authentication bug and improved performance" in rendered

    def test_iteration_render_without_children(self):
        """Test rendering an Iteration without children."""
        from models import Iteration

        iteration = Iteration(id="iteration_1")

        rendered = iteration.render()

        assert "### iteration_1" in rendered
        # No children should render cleanly
        assert "None" not in rendered


class TestTaskRender:
    """Test Task model render() method with TOC generation."""

    def test_task_render_without_toc(self):
        """Test rendering a Task without TOC."""
        from models import Task, Opts, Spec

        description = Doc(
            id="description",
            label="Specification",
            description="Task specification"
        )

        spec = Spec(version=1, description="Task specification")

        task = Task(
            id="task_1",
            spec=spec,
            opts=Opts(render_toc=False)
        )

        rendered = task.render()

        assert "# Task: task_1" in rendered
        assert "## Specification" in rendered
        assert "## Table of Contents" not in rendered

    def test_task_render_with_toc_no_iterations(self):
        """Test rendering a Task with TOC but no iterations."""
        from models import Task, Opts, Spec

        description = Doc(
            id="description",
            label="Specification",
            description="Task specification"
        )

        spec = Spec(version=1, description="Task specification")

        task = Task(
            id="task_1",
            spec=spec,
            opts=Opts(render_toc=True)
        )

        rendered = task.render()

        assert "# Task: task_1" in rendered
        assert "## Table of Contents" in rendered
        assert "- [Specification" in rendered
        # No Iterations section should be in TOC
        assert "[Iterations]" not in rendered

    def test_task_render_with_toc_with_iterations(self):
        """Test rendering a Task with TOC and iterations."""
        from models import Task, Iteration, Opts, Spec

        description = Doc(
            id="description",
            label="Specification",
            description="Task specification"
        )

        spec = Spec(version=1, description="Task specification")

        iteration1 = Iteration(id="iteration_1")
        iteration2 = Iteration(id="iteration_2")

        task = Task(
            id="task_1",
            spec=spec,
            iterations={
                "iteration_1": iteration1,
                "iteration_2": iteration2,
            },
            opts=Opts(render_toc=True)
        )

        rendered = task.render()

        assert "# Task: task_1" in rendered
        assert "## Table of Contents" in rendered
        assert "- [Specification" in rendered
        assert "- [Iterations](#iterations)" in rendered
        assert "- [iteration_1](#iteration_1)" in rendered
        assert "- [iteration_2](#iteration_2)" in rendered

    def test_task_render_with_spec_toc(self):
        """Test Task TOC includes Spec's description nested TOC when description.opts.render_toc is enabled."""
        from models import Task, Opts, Spec

        spec_child = Doc(
            id="section1",
            label="Section 1",
            description="First section"
        )

        description = Doc(
            id="description",
            label="Specification",
            description="Task specification",
            children={"section1": spec_child},
            opts=Opts(render_toc=True)
        )

        spec = Spec(version=1, description="Task specification")

        task = Task(
            id="task_1",
            spec=spec,
            opts=Opts(render_toc=True)
        )

        rendered = task.render()

        assert "## Table of Contents" in rendered
        assert "- [Specification" in rendered
        # With string-based description, nested TOC from Doc children is not included
        assert "  - [Section 1](#section-1)" not in rendered

    def test_task_render_without_spec_toc(self):
        """Test Task TOC does not include Spec's description nested TOC when description.opts.render_toc is not enabled."""
        from models import Task, Opts, Spec

        spec_child = Doc(
            id="section1",
            label="Section 1",
            description="First section"
        )

        description = Doc(
            id="description",
            label="Specification",
            description="Task specification",
            children={"section1": spec_child},
            opts=Opts(render_toc=False)
        )

        spec = Spec(version=1, description="Task specification")

        task = Task(
            id="task_1",
            spec=spec,
            opts=Opts(render_toc=True)
        )

        rendered = task.render()

        assert "## Table of Contents" in rendered
        assert "- [Specification" in rendered
        # Spec's children TOC should NOT be included
        assert "  - [Section 1]" not in rendered

    def test_task_render_with_iteration_children_toc(self):
        """Test Task TOC includes iteration children TOC when children have render_toc enabled."""
        from models import Task, Iteration, Opts, Spec

        description = Doc(
            id="description",
            label="Specification",
            description="Task specification"
        )

        spec = Spec(version=1, description="Task specification")

        # Child with metadata so it generates TOC entries
        child_section = Doc(
            id="section1",
            label="Section 1",
            description="Child section content",
            metadata={"status": "active"},
            opts=Opts(render_toc=True)
        )

        iteration1 = Iteration(
            id="iteration_1",
            children={"section1": child_section}
        )

        task = Task(
            id="task_1",
            spec=spec,
            iterations={"iteration_1": iteration1},
            opts=Opts(render_toc=True)
        )

        rendered = task.render()

        assert "## Table of Contents" in rendered
        assert "- [Iterations](#iterations)" in rendered
        assert "  - [iteration_1](#iteration_1)" in rendered
        # Child's TOC entries should be indented under iteration
        # The child has metadata, so it generates a "Status" TOC entry
        assert "    - [Status](#status)" in rendered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
