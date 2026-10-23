# SPDX-License-Identifier: LGPL-3.0-or-later
"""Gasket feature (PType ``Gasket``)."""

from __future__ import annotations

from typing import Any

import FreeCAD
import Part

from ..application.feature_registry import FeatureDefinition
from ..infrastructure.freecad.properties import PropertySpec, define_properties
from .base import PypeFeature
from .geometry import FeatureGeometry

GASKET_PROPERTIES = (
    PropertySpec("App::PropertyString", "FClass", "Gasket", "Flange class / pressure rating"),
    PropertySpec("App::PropertyLength", "IRID", "Gasket", "Inner ring inner diameter"),
    PropertySpec("App::PropertyLength", "SEID", "Gasket", "Sealing element inner diameter"),
    PropertySpec("App::PropertyLength", "SEOD", "Gasket", "Sealing element outer diameter"),
    PropertySpec("App::PropertyLength", "CROD", "Gasket", "Centering ring outer diameter"),
    PropertySpec("App::PropertyLength", "SEthk", "Gasket", "Sealing element thickness"),
    PropertySpec("App::PropertyLength", "Rthk", "Gasket", "Inner and centering ring thickness"),
)


class GasketShapeBuilder:
    """Build the inner ring, sealing element and centering ring."""

    def build(self, fp: Any) -> FeatureGeometry:
        if not (
            fp.IRID > 0
            and fp.SEID > fp.IRID
            and fp.SEOD > fp.SEID
            and fp.CROD > fp.SEOD
            and fp.SEthk > 0
            and fp.Rthk > 0
        ):
            raise ValueError("Gasket: invalid dimensions")
        origin = FreeCAD.Vector(0, 0, 0)
        z_axis = FreeCAD.Vector(0, 0, 1)
        ring_offset = (float(fp.SEthk) - float(fp.Rthk)) / 2.0
        inner_ring = Part.makeCylinder(
            fp.SEID / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), z_axis
        ).cut(Part.makeCylinder(fp.IRID / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), z_axis))
        sealing_element = Part.makeCylinder(fp.SEOD / 2, fp.SEthk, origin, z_axis).cut(
            Part.makeCylinder(fp.SEID / 2, fp.SEthk, origin, z_axis)
        )
        centering_ring = Part.makeCylinder(
            fp.CROD / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), z_axis
        ).cut(Part.makeCylinder(fp.SEOD / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), z_axis))
        shape = inner_ring.fuse(sealing_element).fuse(centering_ring).removeSplitter()
        return FeatureGeometry(
            shape=shape,
            ports=(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, float(fp.SEthk))),
            directions=(FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)),
        )


class Gasket(PypeFeature):
    """Class for object PType="Gasket"."""

    shape_builder_class = GasketShapeBuilder

    def __init__(
        self,
        obj: Any,
        rating: str,
        DN: str = "DN50",
        FClass: str = "150lb",
        IRID: float = 55.6,
        SEID: float = 69.9,
        SEOD: float = 85.9,
        CROD: float = 104.9,
        SEthk: float = 4.5,
        Rthk: float = 3.2,
    ) -> None:
        super(Gasket, self).__init__(obj)
        obj.PType = "Gasket"
        obj.Proxy = self
        obj.PRating = rating
        obj.PSize = DN
        define_properties(
            obj,
            GASKET_PROPERTIES,
            {
                "FClass": FClass,
                "IRID": IRID,
                "SEID": SEID,
                "SEOD": SEOD,
                "CROD": CROD,
                "SEthk": SEthk,
                "Rthk": Rthk,
            },
        )
        self.execute(obj)

    def onChanged(self, fp: Any, prop: str) -> None:
        if prop == "Rthk" and hasattr(fp, "SEthk") and fp.Rthk > fp.SEthk:
            FreeCAD.Console.PrintError(
                "Gasket: Ring thickness (Rthk) must not exceed sealing element thickness (SEthk)\n"
            )
        return None

    def execute(self, fp: Any) -> None:
        try:
            geometry = self.shape_builder_class().build(fp)
        except ValueError:
            FreeCAD.Console.PrintError("Gasket: invalid dimensions -- shape not updated\n")
            return
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super(Gasket, self).execute(fp)


GASKET_FEATURE = FeatureDefinition(
    key="Gasket",
    proxy=Gasket,
    label="Gasket",
    icon="Quetzal_InsertGasket",
    accepted_prop_counts=(8,),
)
