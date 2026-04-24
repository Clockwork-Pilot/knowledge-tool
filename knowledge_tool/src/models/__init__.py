"""Shared knowledge models for knowledge base and task lifecycle."""

from .base_model import RenderableModel
from .doc_model import Doc, Opts
from .feature_model import Feature
from .results_model import ConstraintBashResult, FeatureResult, ChecksResults
from .constraints_model import (
    ConstraintBash,
)
from .spec_model import Spec
from .project_model import Project, SpecRef, EnvVar

# Registry mapping model type string to model class.
# Add all RenderableModel subclasses that can be root nodes in knowledge documents.
# These are used by render.py for polymorphic instantiation and rendering.
MODEL_REGISTRY = {
    "Doc": Doc,
    "Feature": Feature,
    "ChecksResults": ChecksResults,
    "Spec": Spec,
    "Project": Project,
}

__all__ = [
    "RenderableModel",
    "Doc",
    "Opts",
    "Feature",
    "ConstraintBash",
    "ConstraintBashResult",
    "FeatureResult",
    "ChecksResults",
    "Spec",
    "Project",
    "SpecRef",
    "EnvVar",
    "MODEL_REGISTRY",
]

