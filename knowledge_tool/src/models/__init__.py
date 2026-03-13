"""Shared knowledge models for knowledge base and task lifecycle."""

from .base_model import RenderableModel
from .doc_model import Doc, Opts
from .feature_model import Feature
from .results_model import ConstraintBashResult, ConstraintPromptResult, FeatureResult, ChecksResults
from .constraints_model import (
    FeaturesScope,
    ConstraintBash,
    ConstraintPrompt,
    Constraint,
)
from .task_model import Task, Iteration, CodeStats, TaskTestMetrics
from .spec_model import Spec

# Registry mapping model type string to model class.
# Add all RenderableModel subclasses that can be root nodes in knowledge documents.
# These are used by render.py for polymorphic instantiation and rendering.
MODEL_REGISTRY = {
    "Doc": Doc,
    "Feature": Feature,
    "FeaturesScope": FeaturesScope,
    "ChecksResults": ChecksResults,
    "Task": Task,
    "Iteration": Iteration,
    "Spec": Spec,
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
    "ChecksResults",
    "Task",
    "Iteration",
    "CodeStats",
    "TaskTestMetrics",
    "Spec",
    "MODEL_REGISTRY",
]

# Resolve forward references after all modules are loaded
FeaturesScope.model_rebuild()
