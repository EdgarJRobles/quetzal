# SPDX-License-Identifier: LGPL-3.0-or-later
"""Terminal adapter feature (PType ``TerminalAdapter``)."""

from __future__ import annotations

from math import tan
from typing import Any

import FreeCAD
import Part

from ..application.feature_registry import FeatureDefinition
from ..infrastructure.freecad.properties import PropertySpec, define_properties
from .base import PypeFeature
from .geometry import FeatureGeometry
from .shapes import make_regular_polygon

TERMINAL_ADAPTER_PROPERTIES = (
    PropertySpec("App::PropertyLength", "OD", "TerminalAdapter", "Outside diameter"),
    PropertySpec("App::PropertyLength", "L", "TerminalAdapter", "Overall length"),
    PropertySpec("App::PropertyLength", "SW", "TerminalAdapter", "Support width"),
    PropertySpec("App::PropertyLength", "OD2", "TerminalAdapter", "Outside thread side"),
)


class TerminalAdapterShapeBuilder:
    """Build the hex support, threaded cone and bore of the adapter."""

    def build(self, fp: Any) -> FeatureGeometry:
        polygon_thickness = fp.SW / 5
        thread_thickness = fp.L - fp.SW
        cylinder = Part.makeCylinder(
            fp.OD / 2,
            fp.SW - polygon_thickness,
            FreeCAD.Vector(0, 0, -polygon_thickness),
            FreeCAD.Vector(0, 0, -1),
        )
        polygon_face = Part.Face(make_regular_polygon(6, (fp.OD * 1.2) / 2))
        extrusion = polygon_face.extrude(FreeCAD.Vector(0, 0, -polygon_thickness))
        body = cylinder.fuse(extrusion)

        outer_cone = Part.makeCone(
            fp.OD2 / 2,
            (fp.OD2 / 2 - (tan(0.0312396483) * thread_thickness)),
            thread_thickness,
            FreeCAD.Vector(0, 0, -polygon_thickness),
            FreeCAD.Vector(0, 0, 1),
            360,
        )
        body = outer_cone.fuse(body)
        body = body.makeFillet(
            2.5,
            [
                body.Edges[16],
                body.Edges[12],
                body.Edges[9],
                body.Edges[10],
                body.Edges[14],
                body.Edges[18],
            ],
        )

        bore = Part.makeCylinder(
            fp.OD / 3,
            fp.SW,
            FreeCAD.Vector(0, 0, -polygon_thickness),
            FreeCAD.Vector(0, 0, -1),
        )
        body = body.cut(bore)
        inner_cone = Part.makeCone(
            fp.OD2 / 2 * 0.8,
            (fp.OD2 / 2 - (tan(0.0312396483) * thread_thickness)) * 0.8,
            thread_thickness,
            FreeCAD.Vector(0, 0, -polygon_thickness),
            FreeCAD.Vector(0, 0, 1),
            360,
        )
        body = body.cut(inner_cone)

        # This legacy feature never exposed connection ports.
        return FeatureGeometry(shape=body, ports=(), directions=())


class TerminalAdapter(PypeFeature):
    """Class for object PType="TerminalAdapter"."""

    shape_builder_class = TerminalAdapterShapeBuilder

    def __init__(
        self,
        obj: Any,
        rating: str,
        DN: str = "PCV-1/2",
        OD: float = 21.3,
        L: float = 33.2,
        SW: float = 18.7,
        OD2: float = 21.33,
    ) -> None:
        super(TerminalAdapter, self).__init__(obj)
        obj.Proxy = self
        obj.PType = "TerminalAdapter"
        obj.PRating = rating
        obj.PSize = DN
        define_properties(
            obj,
            TERMINAL_ADAPTER_PROPERTIES,
            {"OD": OD, "L": L, "SW": SW, "OD2": OD2},
        )
        self.execute(obj)

    def onChanged(self, fp: Any, prop: str) -> None:
        return None

    def execute(self, fp: Any) -> None:
        geometry = self.shape_builder_class().build(fp)
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super(TerminalAdapter, self).execute(fp)


TERMINAL_ADAPTER_FEATURE = FeatureDefinition(
    key="TerminalAdapter",
    proxy=TerminalAdapter,
    label="TerminalAdapter",
    icon="Quetzal_TerminalAdapter",
    accepted_prop_counts=(5,),
)
