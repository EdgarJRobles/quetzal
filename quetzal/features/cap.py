# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cap feature (PType ``Cap``)."""

from __future__ import annotations

from typing import Any

import FreeCAD
import Part

from ..application.feature_registry import FeatureDefinition
from ..infrastructure.freecad.properties import PropertySpec, define_properties
from .base import PypeFeature
from .geometry import FeatureGeometry

CAP_PROPERTIES = (
    PropertySpec("App::PropertyLength", "OD", "Cap", "Outside diameter"),
    PropertySpec("App::PropertyLength", "thk", "Cap", "Wall thickness"),
    PropertySpec("App::PropertyLength", "ID", "Cap", "Inside diameter"),
    PropertySpec("App::PropertyString", "Profile", "Cap", "Section dim."),
)


class CapShapeBuilder:
    """Build the rounded cap shape and its single port."""

    def build(self, fp: Any) -> FeatureGeometry:
        diameter = float(fp.OD)
        thickness = float(fp.thk)
        sfera = Part.makeSphere(
            0.8 * diameter, FreeCAD.Vector(0, 0, -(0.55 * diameter - 6 * thickness))
        )
        cilindro = Part.makeCylinder(
            diameter / 2,
            diameter * 1.7,
            FreeCAD.Vector(0, 0, -(0.55 * diameter - 6 * thickness + 1)),
            FreeCAD.Vector(0, 0, 1),
        )
        common = sfera.common(cilindro)
        fil = common.makeFillet(diameter / 6.5, common.Edges)
        cut = fil.cut(
            Part.makeCylinder(
                diameter * 1.1,
                diameter * 2,
                FreeCAD.Vector(0, 0, 0),
                FreeCAD.Vector(0, 0, -1),
            )
        )
        cap = cut.makeThickness(
            [f for f in cut.Faces if type(f.Surface) is Part.Plane],
            -thickness,
            1.0e-3,
        )
        return FeatureGeometry(
            shape=cap,
            ports=(FreeCAD.Vector(),),
            directions=(FreeCAD.Vector(0, 0, -1),),
        )


class Cap(PypeFeature):
    """Class for object PType="Cap".

    ``Cap(obj, [PSize="DN50", OD=60.3, thk=3])``
    """

    shape_builder_class = CapShapeBuilder

    def __init__(
        self,
        obj: Any,
        rating: str = "SCH-STD",
        DN: str = "DN50",
        OD: float = 60.3,
        thk: float = 3,
    ) -> None:
        super(Cap, self).__init__(obj)
        obj.PType = "Cap"
        obj.Proxy = self
        obj.PRating = rating
        obj.PSize = DN
        define_properties(
            obj,
            CAP_PROPERTIES,
            {"OD": OD, "thk": thk, "ID": float(OD) - 2 * float(thk)},
        )
        self.execute(obj)

    def onChanged(self, fp: Any, prop: str) -> None:
        return None

    def execute(self, fp: Any) -> None:
        if fp.thk > fp.OD / 2:
            fp.thk = fp.OD / 2.1
        fp.ID = fp.OD - 2 * fp.thk
        fp.Profile = str(fp.OD) + "x" + str(fp.thk)

        geometry = self.shape_builder_class().build(fp)
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super(Cap, self).execute(fp)


CAP_FEATURE = FeatureDefinition(
    key="Cap",
    proxy=Cap,
    label="Cap",
    icon="Quetzal_InsertCap",
    accepted_prop_counts=(3,),
)
