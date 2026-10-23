# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy: pinch."""

from __future__ import annotations

import FreeCAD
import Part

from ...domain.pipe_sizes import PIPE_OUTSIDE_DIAMETERS_MM as pipe_OD
from ..geometry import FeatureGeometry
from ...application.valve import ValveContext
from .strategy import register_strategy


class PinchValveStrategy:
    key = "pinch"

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        fp = ctx.feature
        H = ctx.height
        """Build a simple manual pinch valve for legacy CSV rows."""
        pipe_od = pipe_OD.get(fp.PSize, float(fp.ID))
        bore_d = max(float(fp.ID), pipe_od * 0.9)
        body_d = max(float(fp.ODBody), pipe_od * 1.15)
        flange_t = max(8.0, min(32.0, H * 0.09))

        body = Part.makeCylinder(
            body_d * 0.42,
            H,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )

        flange_neg = Part.makeCylinder(
            body_d / 2.0,
            flange_t,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        flange_pos = Part.makeCylinder(
            body_d / 2.0,
            flange_t,
            FreeCAD.Vector(0, 0, H / 2.0 - flange_t),
            FreeCAD.Vector(0, 0, 1),
        )

        # Flexible sleeve body with a pinched waist under the handwheel.
        sleeve_len = max(1.0, H - 2.0 * flange_t)
        sleeve = Part.makeCylinder(
            body_d * 0.36,
            sleeve_len,
            FreeCAD.Vector(0, 0, -sleeve_len / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        pinch_h = max(pipe_od * 0.16, 8.0)
        pinch_w = body_d * 0.78
        pinch_len = sleeve_len * 0.34
        pinch_cut_top = Part.makeBox(
            pinch_w,
            pinch_h,
            pinch_len,
            FreeCAD.Vector(-pinch_w / 2.0, body_d * 0.18, -pinch_len / 2.0),
        )
        pinch_cut_bot = Part.makeBox(
            pinch_w,
            pinch_h,
            pinch_len,
            FreeCAD.Vector(-pinch_w / 2.0, -body_d * 0.18 - pinch_h, -pinch_len / 2.0),
        )
        sleeve = sleeve.cut(pinch_cut_top)
        sleeve = sleeve.cut(pinch_cut_bot)

        bore = Part.makeCylinder(
            bore_d / 2.0,
            H + 2.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - 1.0),
            FreeCAD.Vector(0, 0, 1),
        )

        bonnet_w = body_d * 0.58
        bonnet_h = max(pipe_od * 0.16, 18.0)
        bonnet_l = H * 0.42
        bonnet = Part.makeBox(
            bonnet_w,
            bonnet_h,
            bonnet_l,
            FreeCAD.Vector(-bonnet_w / 2.0, body_d * 0.34, -bonnet_l / 2.0),
        )

        stem_r = max(3.0, min(10.0, pipe_od * 0.035))
        stem_y0 = body_d * 0.34 + bonnet_h
        stem_h = body_d * 0.72
        stem = Part.makeCylinder(
            stem_r,
            stem_h,
            FreeCAD.Vector(0, stem_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )

        yoke_r = max(3.0, stem_r * 0.85)
        yoke_offset = body_d * 0.22
        yoke_h = stem_h * 0.78
        yoke_y0 = body_d * 0.35
        yoke1 = Part.makeCylinder(
            yoke_r,
            yoke_h,
            FreeCAD.Vector(-yoke_offset, yoke_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        yoke2 = Part.makeCylinder(
            yoke_r,
            yoke_h,
            FreeCAD.Vector(yoke_offset, yoke_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        cross_l = max(H * 0.22, yoke_r * 3.0)
        cross = Part.makeBox(
            yoke_offset * 2.0 + yoke_r * 2.0,
            yoke_r * 2.0,
            cross_l,
            FreeCAD.Vector(-yoke_offset - yoke_r, yoke_y0 + yoke_h - yoke_r, -cross_l / 2.0),
        )

        wheel_r = max(pipe_od * 0.3, 32.0)
        wheel_tube = max(2.5, wheel_r * 0.06)
        wheel_center = FreeCAD.Vector(0, stem_y0 + stem_h, 0)
        wheel = Part.makeTorus(wheel_r, wheel_tube, wheel_center, FreeCAD.Vector(0, 1, 0))
        hub = Part.makeCylinder(
            wheel_tube * 1.6,
            wheel_tube * 4.0,
            wheel_center - FreeCAD.Vector(0, wheel_tube * 2.0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        spoke_x = Part.makeCylinder(
            wheel_tube * 0.45,
            wheel_r * 2.0,
            wheel_center - FreeCAD.Vector(wheel_r, 0, 0),
            FreeCAD.Vector(1, 0, 0),
        )
        spoke_z = Part.makeCylinder(
            wheel_tube * 0.45,
            wheel_r * 2.0,
            wheel_center - FreeCAD.Vector(0, 0, wheel_r),
            FreeCAD.Vector(0, 0, 1),
        )

        valve = body.fuse(flange_neg)
        valve = valve.fuse(flange_pos)
        valve = valve.fuse(sleeve)
        valve = valve.fuse(bonnet)
        valve = valve.fuse(stem)
        valve = valve.fuse(yoke1)
        valve = valve.fuse(yoke2)
        valve = valve.fuse(cross)
        valve = valve.fuse(wheel)
        valve = valve.fuse(hub)
        valve = valve.fuse(spoke_x)
        valve = valve.fuse(spoke_z)
        valve = valve.cut(bore)
        fp.Shape = valve.removeSplitter()
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


register_strategy(PinchValveStrategy())
