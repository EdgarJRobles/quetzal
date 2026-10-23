# SPDX-License-Identifier: LGPL-3.0-or-later
"""Selection predicates for the Quetzal task watchers."""

from __future__ import annotations

from typing import Any, Optional

import FreeCAD
import FreeCADGui


def _selected() -> Optional[Any]:
    try:
        selection = FreeCADGui.Selection.getSelection()
    except Exception:
        return None
    return selection[0] if selection else None


def no_objects() -> bool:
    document = FreeCAD.ActiveDocument
    return document is not None and document.ActiveObject is None


def wire_objects() -> bool:
    document = FreeCAD.ActiveDocument
    if document is None or document.ActiveObject is None:
        return False
    obj = _selected()
    return bool(obj is not None and hasattr(obj, "Shape") and obj.Shape.Edges)


def tube_objects() -> bool:
    document = FreeCAD.ActiveDocument
    if document is None or document.ActiveObject is None:
        return False
    obj = _selected()
    if obj is None:
        return False
    try:
        from pCmd import isPipe

        return bool(isPipe(obj))
    except Exception:
        return False
