# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy: knife_gate."""

from __future__ import annotations

import FreeCAD
import Part

from ...domain.pipe_sizes import PIPE_OUTSIDE_DIAMETERS_MM as pipe_OD
from ..geometry import FeatureGeometry
from ...application.valve import ValveContext
from .strategy import register_strategy


class KnifeGateValveStrategy:
    key = "knife_gate"

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        fp = ctx.feature
        H = ctx.height
        """Build a simple wafer-style knife gate valve for legacy CSV rows."""
        import math

        pipe_od = pipe_OD.get(fp.PSize, float(fp.ID))
        bore_d = max(float(fp.ID), pipe_od * 0.9)
        body_d = max(float(fp.ODBody), pipe_od * 1.25)
        gate_t = max(3.0, min(12.0, pipe_od * 0.035))

        body = Part.makeCylinder(
            body_d / 2.0,
            H,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        bore = Part.makeCylinder(
            bore_d / 2.0,
            H + 2.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - 1.0),
            FreeCAD.Vector(0, 0, 1),
        )
        body = body.cut(bore)

        # Flat bonnet/packing box across the top of the wafer body.
        bonnet_w = body_d * 0.72
        bonnet_h = max(pipe_od * 0.18, 18.0)
        bonnet = Part.makeBox(
            bonnet_w,
            bonnet_h,
            H * 1.12,
            FreeCAD.Vector(-bonnet_w / 2.0, body_d / 2.0 - bonnet_h * 0.25, -H * 0.56),
        )

        # Visible knife gate blade rising through the yoke.
        blade_h = body_d * 0.95
        blade_w = max(bore_d * 0.72, pipe_od * 0.55)
        blade = Part.makeBox(
            blade_w,
            gate_t,
            H * 0.45,
            FreeCAD.Vector(-blade_w / 2.0, body_d / 2.0 - gate_t / 2.0, -H * 0.225),
        )
        blade.translate(FreeCAD.Vector(0, blade_h * 0.36, 0))

        stem_r = max(3.0, min(10.0, pipe_od * 0.035))
        stem_base_y = body_d / 2.0 + bonnet_h * 0.35
        stem_h = body_d * 1.2
        stem = Part.makeCylinder(
            stem_r,
            stem_h,
            FreeCAD.Vector(0, stem_base_y, 0),
            FreeCAD.Vector(0, 1, 0),
        )

        # Two yoke posts and a crosshead frame around the rising stem.
        post_r = max(3.0, stem_r * 0.8)
        post_offset = body_d * 0.24
        post_h = stem_h * 0.72
        post_y0 = body_d / 2.0 + bonnet_h * 0.1
        post1 = Part.makeCylinder(
            post_r,
            post_h,
            FreeCAD.Vector(-post_offset, post_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        post2 = Part.makeCylinder(
            post_r,
            post_h,
            FreeCAD.Vector(post_offset, post_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        cross = Part.makeBox(
            post_offset * 2.0 + post_r * 2.0,
            post_r * 2.0,
            max(H * 0.35, gate_t * 2.0),
            FreeCAD.Vector(
                -post_offset - post_r,
                post_y0 + post_h - post_r,
                -max(H * 0.35, gate_t * 2.0) / 2.0,
            ),
        )

        wheel_r = max(pipe_od * 0.32, 32.0)
        wheel_tube_r = max(2.5, wheel_r * 0.06)
        wheel_center = FreeCAD.Vector(0, stem_base_y + stem_h, 0)
        wheel = Part.makeTorus(wheel_r, wheel_tube_r, wheel_center, FreeCAD.Vector(0, 1, 0))
        hub = Part.makeCylinder(
            wheel_tube_r * 1.6,
            wheel_tube_r * 4.0,
            wheel_center - FreeCAD.Vector(0, wheel_tube_r * 2.0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        spoke_r = max(1.5, wheel_tube_r * 0.45)
        spokes = None
        for angle in (0, 90, 180, 270):
            rad = math.radians(angle)
            direction = FreeCAD.Vector(math.cos(rad), 0, math.sin(rad))
            spoke = Part.makeCylinder(
                spoke_r,
                wheel_r,
                wheel_center,
                direction,
            )
            spokes = spoke if spokes is None else spokes.fuse(spoke)

        valve = body.fuse(bonnet)
        valve = valve.fuse(blade)
        valve = valve.fuse(stem)
        valve = valve.fuse(post1)
        valve = valve.fuse(post2)
        valve = valve.fuse(cross)
        valve = valve.fuse(wheel)
        valve = valve.fuse(hub)
        if spokes is not None:
            valve = valve.fuse(spokes)
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


register_strategy(KnifeGateValveStrategy())
