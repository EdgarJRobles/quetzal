# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pipe feature (PType ``Pipe``).

The class keeps the historic public API (``pFeatures.Pipe`` re-exports it) but
delegates property registration, geometry and port bookkeeping to dedicated
collaborators.
"""

from __future__ import annotations

from math import tan
from typing import Any

import FreeCAD
import Part

from ..application.feature_registry import FeatureDefinition
from ..infrastructure.freecad.properties import PropertySpec, define_properties
from .base import PypeFeature
from .geometry import FeatureGeometry

PIPE_PROPERTIES = (
    PropertySpec("App::PropertyLength", "OD", "Pipe", "Outside diameter"),
    PropertySpec("App::PropertyLength", "thk", "Pipe", "Wall thickness"),
    PropertySpec("App::PropertyLength", "ID", "Pipe", "Inside diameter"),
    PropertySpec("App::PropertyLength", "Height", "Pipe", "Length of tube"),
    PropertySpec("App::PropertyString", "Profile", "Pipe", "Section dim."),
)


class PipeShapeBuilder:
    """Build the hollow cylinder and its ports from a pipe document object."""

    def build(self, fp: Any) -> FeatureGeometry:
        if fp.ID:
            shape = Part.makeCylinder(fp.OD / 2, fp.Height).cut(
                Part.makeCylinder(fp.ID / 2, fp.Height)
            )
        else:
            shape = Part.makeCylinder(fp.OD / 2, fp.Height)
        return FeatureGeometry(
            shape=shape,
            ports=(FreeCAD.Vector(), FreeCAD.Vector(0, 0, float(fp.Height))),
            directions=(FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)),
        )


class Pipe(PypeFeature):
    """Class for object PType="Pipe".

    ``Pipe(obj, [PSize="DN50", OD=60.3, thk=3, H=100])``
    """

    shape_builder_class = PipeShapeBuilder

    def __init__(
        self,
        obj: Any,
        rating: str,
        DN: str = "DN50",
        OD: float = 60.3,
        thk: float = 3,
        H: float = 100,
    ) -> None:
        super(Pipe, self).__init__(obj)
        obj.PType = "Pipe"
        obj.Proxy = self
        obj.PRating = rating
        obj.PSize = DN
        define_properties(
            obj,
            PIPE_PROPERTIES,
            {
                "OD": OD,
                "thk": thk,
                "ID": float(OD) - 2 * float(thk),
                "Height": H,
            },
        )
        self.execute(obj)

    def onChanged(self, fp: Any, prop: str) -> None:
        if prop == "ID" and fp.ID < fp.OD:
            fp.thk = (fp.OD - fp.ID) / 2

    def execute(self, fp: Any) -> None:
        _update_height_from_parent_group(fp)
        if fp.thk > fp.OD / 2:
            fp.thk = fp.OD / 2
        fp.ID = fp.OD - 2 * fp.thk
        fp.Profile = str(fp.OD) + "x" + str(fp.thk)

        geometry = self.shape_builder_class().build(fp)
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super(Pipe, self).execute(fp)


def _update_height_from_parent_group(fp: Any) -> None:
    """Keep the historical pype-line length adjustment out of the geometry."""

    try:
        parent = fp.getParentGroup()
        index = parent.Tubes.index(fp.Name)
        edges = parent.Base.Shape.Edges
        length = edges[index].Length
        radius = parent.BendRadius
        if index < len(parent.Curves):
            v1, v2 = [e.tangentAt(0) for e in edges[index : index + 2]]
            alfa = float(v1.getAngle(v2)) / 2
            length -= float(radius * tan(alfa))
        if index:
            v1, v2 = [e.tangentAt(0) for e in edges[index - 1 : index + 1]]
            alfa = float(v1.getAngle(v2)) / 2
            tang = float(radius * tan(alfa))
            length -= tang
            fp.AttachmentOffset.Base = FreeCAD.Vector(0, 0, tang)
        fp.Height = length
    except Exception:
        # Not part of a pype line: the property keeps its user-supplied value.
        pass


PIPE_FEATURE = FeatureDefinition(
    key="Pipe",
    proxy=Pipe,
    label="Tube",
    icon="Quetzal_InsertPipe",
    accepted_prop_counts=(4,),
)
