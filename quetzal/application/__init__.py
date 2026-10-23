# SPDX-License-Identifier: LGPL-3.0-or-later
"""Application layer: use cases and ports, independent from FreeCAD."""

from .feature_registry import FeatureDefinition, FeatureRegistry
from .insertion import DocumentPort, FeatureInserter, InMemoryDocument

__all__ = [
    "DocumentPort",
    "FeatureDefinition",
    "FeatureInserter",
    "FeatureRegistry",
    "InMemoryDocument",
]
