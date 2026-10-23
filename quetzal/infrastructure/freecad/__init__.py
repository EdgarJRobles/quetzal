# SPDX-License-Identifier: LGPL-3.0-or-later
"""Infrastructure adapters for FreeCAD."""

from .document import FreeCADDocumentAdapter
from .properties import PropertySpec, UNSET, define_properties
from .view_provider import FreeCADViewFactory, ViewProvider

__all__ = [
    "FreeCADDocumentAdapter",
    "FreeCADViewFactory",
    "PropertySpec",
    "UNSET",
    "ViewProvider",
    "define_properties",
]
