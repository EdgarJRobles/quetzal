# SPDX-License-Identifier: LGPL-3.0-or-later
"""Application layer: use cases and ports, independent from FreeCAD."""

from .feature_registry import FeatureDefinition, FeatureRegistry
from .form_services import FormServices
from .reporting import NullReporter, RecordingReporter, UserReporter
from .insertion import DocumentPort, FeatureInserter, InMemoryDocument
from .valve import ValveContext
from .workbench_state import WorkbenchState, default_workbench_state

__all__ = [
    "DocumentPort",
    "FeatureDefinition",
    "FeatureInserter",
    "FeatureRegistry",
    "FormServices",
    "InMemoryDocument",
    "NullReporter",
    "RecordingReporter",
    "UserReporter",
    "ValveContext",
    "WorkbenchState",
    "default_workbench_state",
]
