# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD document adapter implementing the application ``DocumentPort``."""

from __future__ import annotations

from typing import Any, Callable, Optional

import FreeCAD

from ...domain.ports import Vec3
from .view_provider import FreeCADViewFactory

DocumentProvider = Callable[[], Any]


class FreeCADDocumentAdapter:
    """Translate domain-level operations into FreeCAD API calls."""

    def __init__(
        self,
        document_provider: Optional[DocumentProvider] = None,
        view_factory: Optional[FreeCADViewFactory] = None,
    ) -> None:
        self._document_provider = document_provider or (lambda: FreeCAD.ActiveDocument)
        self._view_factory = view_factory or FreeCADViewFactory()

    def _document(self) -> Any:
        document = self._document_provider()
        if document is None:
            raise RuntimeError("Quetzal: no active FreeCAD document")
        return document

    def add_object(self, object_type: str, name: str) -> Any:
        return self._document().addObject(object_type, name)

    def place(self, obj: Any, position: Vec3, direction: Vec3, axis: Vec3) -> None:
        obj.Placement.Base = FreeCAD.Vector(*position.as_tuple())
        rotation = FreeCAD.Rotation(
            FreeCAD.Vector(*axis.as_tuple()),
            FreeCAD.Vector(*direction.as_tuple()),
        )
        obj.Placement.Rotation = rotation.multiply(obj.Placement.Rotation)

    def attach_view(self, obj: Any, icon: str) -> None:
        view_object = getattr(obj, "ViewObject", None)
        if view_object is not None:
            self._view_factory.attach(view_object, icon)

    def recompute(self) -> None:
        self._document().recompute()
