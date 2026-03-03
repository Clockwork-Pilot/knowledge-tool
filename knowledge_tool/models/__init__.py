"""Shared knowledge models for knowledge base and task lifecycle."""

from .base_model import RenderableModel
from .doc_model import Doc, Opts

# Try to import task models if available
try:
    from .task_model import Task, Iteration, CodeStats, TaskTestMetrics
    _has_task_models = True
except ImportError:
    _has_task_models = False

# Registry mapping model type string to model class.
# Add all RenderableModel subclasses that can be root nodes in knowledge documents.
# These are used by render.py for polymorphic instantiation and rendering.
MODEL_REGISTRY = {
    "Doc": Doc,
}

if _has_task_models:
    MODEL_REGISTRY.update({
        "Task": Task,
        "Iteration": Iteration,
    })

__all__ = [
    "RenderableModel",
    "Doc",
    "Opts",
    "MODEL_REGISTRY",
]

if _has_task_models:
    __all__.extend([
        "Task",
        "Iteration",
        "CodeStats",
        "TaskTestMetrics",
    ])
