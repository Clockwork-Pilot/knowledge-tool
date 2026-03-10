"""Shared knowledge models for knowledge base and task lifecycle."""

from .base_model import RenderableModel
from .doc_model import Doc, Opts
from .feature_model import Feature
from .results_model import ConstraintBashResult, ConstraintPromptResult, FeatureResult, Tests
from .constraints_model import (
    FeaturesScope,
    ConstraintBash,
    ConstraintPrompt,
    Constraint,
)
from .task_model import Task, Iteration, CodeStats, TaskTestMetrics

# Registry mapping model type string to model class.
# Add all RenderableModel subclasses that can be root nodes in knowledge documents.
# These are used by render.py for polymorphic instantiation and rendering.
MODEL_REGISTRY = {
    "Doc": Doc,
    "Feature": Feature,
    "FeaturesScope": FeaturesScope,
    "Tests": Tests,
    "Task": Task,
    "Iteration": Iteration,
}

__all__ = [
    "RenderableModel",
    "Doc",
    "Opts",
    "Feature",
    "FeaturesScope",
    "ConstraintBash",
    "ConstraintPrompt",
    "ConstraintBashResult",
    "ConstraintPromptResult",
    "FeatureResult",
    "Constraint",
    "Tests",
    "Task",
    "Iteration",
    "CodeStats",
    "TaskTestMetrics",
    "MODEL_REGISTRY",
]

# Resolve forward references after all modules are loaded
FeaturesScope.model_rebuild()
