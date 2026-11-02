# SPDX-License-Identifier: LGPL-3.0-or-later
"""Batch operations for the PypeLine Manager."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

import FreeCAD
import FreeCADGui

import pCmd
import pFeatures
from ...application.pype_line_spec import PypeLineSpec


def line_group(line: Any) -> Any:
    document = getattr(line, "Document", None) or FreeCAD.ActiveDocument
    groups = document.getObjectsByLabel(str(line.Group))
    return groups[0] if groups else None


def line_pieces(line: Any) -> List[Any]:
    """Return the line's pipes, bends and branch children."""

    group = line_group(line)
    if group is None:
        return []
    pieces = []
    for obj in group.OutList:
        if obj is line or not hasattr(obj, "PType"):
            continue
        if obj.PType == "PypeBranch":
            for name in list(getattr(obj, "Tubes", [])) + list(getattr(obj, "Curves", [])):
                child = obj.Document.getObject(name)
                if child is not None:
                    pieces.append(child)
        else:
            pieces.append(obj)
    return pieces


def spec_from_line(line: Any) -> PypeLineSpec:
    return PypeLineSpec.from_line(line)


def apply_spec(
    line: Any,
    spec: PypeLineSpec,
    update_children: bool = True,
) -> int:
    """Apply a spec to the line and, optionally, to its existing pieces."""

    line.PSize = spec.dn
    line.PRating = spec.rating
    line.OD = spec.od
    line.thk = spec.thk
    line.BendRadius = spec.bend_radius

    changed = 0
    if not update_children:
        return changed

    for obj in line_pieces(line):
        if obj.PType not in ("Pipe", "Elbow"):
            continue
        obj.PSize = spec.dn
        obj.PRating = spec.rating
        if hasattr(obj, "OD"):
            obj.OD = spec.od
        if hasattr(obj, "thk"):
            obj.thk = spec.thk
        if obj.PType == "Elbow" and hasattr(obj, "BendRadius"):
            obj.BendRadius = spec.bend_radius
        changed += 1

    if changed:
        line.Document.recompute()
    return changed


def clone_line(
    source: Any,
    label: Optional[str] = None,
    copy_base: bool = True,
) -> Any:
    """Create a new PypeLine2 with the same parameters and optional path."""

    document = source.Document
    spec = spec_from_line(source)
    new_label = label or f"{source.Label}_copy"
    transaction = "Clone pype line"
    document.openTransaction(transaction)
    try:
        clone = document.addObject("Part::FeaturePython", new_label)
        pFeatures.PypeLine2(
            clone,
            spec.rating,
            spec.dn,
            spec.od,
            spec.thk,
            spec.bend_radius,
            new_label,
        )
        if FreeCAD.GuiUp:
            pFeatures.ViewProviderPypeLine(clone.ViewObject)
            try:
                clone.ViewObject.ShapeColor = source.ViewObject.ShapeColor
            except Exception:
                pass
        if copy_base and getattr(source, "Base", None) is not None:
            clone.Base = source.Base
            clone.Proxy.update(clone)
        document.recompute()
        return clone
    finally:
        document.commitTransaction()


def assign_to_line(line: Any, objects: Iterable[Any]) -> int:
    count = 0
    for obj in objects:
        if obj is line or not hasattr(obj, "PType"):
            continue
        pCmd.moveToPyLi(obj, line.Label)
        count += 1
    if count:
        line.Document.recompute()
    return count


def select_pieces(line: Any) -> int:
    pieces = line_pieces(line)
    FreeCADGui.Selection.clearSelection()
    for obj in pieces:
        FreeCADGui.Selection.addSelection(obj)
    return len(pieces)
