# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy: generic two-cone P&ID valve."""

from __future__ import annotations

import FreeCAD
import Part

from ..geometry import FeatureGeometry
from ...application.valve import ValveContext
from .strategy import register_strategy


class GenericValveStrategy:
    key = "generic"

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        fp = ctx.feature
        H = ctx.height

        rating = fp.PRating.lower()
        c = Part.makeCone(
            fp.ODBody / 2,
            fp.ODBody / 5,
            H / 2,
            FreeCAD.Vector(0, 0, -H / 2),
        )
        v = c.fuse(c.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1)))
        if rating.find("ball") + 1 or rating.find("globe") + 1:
            r = min(H * 0.45, float(fp.ODBody) / 2)
            v = v.fuse(Part.makeSphere(r, FreeCAD.Vector(0, 0, 0)))
        fp.Shape = v
        fp.Ports = [
            FreeCAD.Vector(0, 0, -H / 2),
            FreeCAD.Vector(0, 0, H / 2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0, 1),
        ]
        return FeatureGeometry(
            shape=fp.Shape,
            ports=tuple(fp.Ports),
            directions=tuple(fp.PortDirections),
        )


register_strategy(GenericValveStrategy())
