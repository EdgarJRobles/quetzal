# SPDX-License-Identifier: LGPL-3.0-or-later
"""Shared base class for every pipe feature.

This replaces the former ``pFeatures.pypeType`` god-base.  It keeps the exact
public contract (common properties, ``execute`` hook, ``nearestPort``) but no
longer imports ``pCmd``: port maths now lives in the pure domain layer.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import FreeCAD
import FreeCADGui
import Part

from ..domain.ports import Port, Vec3, nearest_port_index
from ..infrastructure.freecad.properties import PropertySpec, define_properties
from quetzal_config import FREECADVERSION

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP

COMMON_PROPERTIES: Tuple[PropertySpec, ...] = (
    PropertySpec(
        "App::PropertyString",
        "PType",
        "PBase",
        "Type of tubeFeature",
    ),
    PropertySpec(
        "App::PropertyString",
        "PRating",
        "PBase",
        "Rating of pipeFeature",
    ),
    PropertySpec(
        "App::PropertyString",
        "PSize",
        "PBase",
        "Nominal diameter",
    ),
    PropertySpec(
        "App::PropertyVectorList",
        "Ports",
        "PBase",
        "Ports position relative to the origin of Shape",
    ),
    PropertySpec(
        "App::PropertyVectorList",
        "PortDirections",
        "PBase",
        "Port direction vectors (unit vectors pointing outward from each port)",
    ),
    PropertySpec(
        "App::PropertyFloat",
        "Kv",
        "PBase",
        "Flow factor (m3/h/bar)",
    ),
)

TWO_WAY_TYPES = ("Pipe", "Reduct", "Flange")


class PypeFeature:
    """Base proxy implementing the common pype-object contract."""

    def __init__(self, obj: Any) -> None:
        define_properties(obj, COMMON_PROPERTIES)
        if FREECADVERSION > 0.19:
            obj.addExtension("Part::AttachExtensionPython")
        else:
            obj.addExtension("Part::AttachExtensionPython", obj)  # FreeCAD <= 0.19
        self.Name = obj.Name

    def execute(self, fp: Any) -> None:
        # Recompute placement according to the Support property.
        fp.positionBySupport()

    def nearestPort(self, point: Any = None) -> Optional[Tuple[int, Any, Any]]:
        """Return ``(index, position, direction)`` of the port nearest to a point.

        Without an explicit point, the current selection is used, preserving
        the historical behaviour used by the join/mate tools.
        """

        if not FreeCAD.ActiveDocument:
            return None
        obj = FreeCAD.ActiveDocument.getObject(self.Name)
        if obj is None:
            return None
        if not point and FreeCADGui.ActiveDocument:
            try:
                selex = FreeCADGui.Selection.getSelectionEx()
                target = selex[0].Object
                so = selex[0].SubObjects[0]
            except Exception:
                FreeCAD.Console.PrintError("No geometry selected\n")
                return None
            if isinstance(so, Part.Vertex):
                point = so.Point
            else:
                point = so.CenterOfMass
        if not point:
            return None

        positions = [obj.Placement.multVec(p) for p in obj.Ports]
        directions = _port_directions(obj)
        if not positions:
            return None
        index = nearest_port_index(
            [Port(Vec3(p.x, p.y, p.z)) for p in positions],
            Vec3(point.x, point.y, point.z),
        )
        return index, positions[index], directions[index]


def _port_directions(obj: Any) -> List[Any]:
    """World-space port directions with the legacy fallbacks."""

    if hasattr(obj, "PortDirections") and obj.PortDirections:
        return [
            obj.Placement.Rotation.multVec(d).normalize()
            for d in obj.PortDirections
        ]
    if getattr(obj, "PType", "") in TWO_WAY_TYPES:
        return [obj.Placement.Rotation.multVec(v) for v in (FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1))]
    directions = []
    for port in getattr(obj, "Ports", []):
        if port.Length:
            directions.append(obj.Placement.Rotation.multVec(port).normalize())
        else:
            directions.append(
                obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, -1)).normalize()
            )
    return directions
