# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy: swing_check."""

from __future__ import annotations

import FreeCAD
import Part

from ...domain.pipe_sizes import PIPE_OUTSIDE_DIAMETERS_MM as pipe_OD
from ..geometry import FeatureGeometry
from ...application.valve import ValveContext
from .strategy import register_strategy


class SwingCheckValveStrategy:
    key = "swing_check"

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        fp = ctx.feature
        H = ctx.height
        """Build a flanged swing check valve using catalog envelope dimensions.

        Local Z is the flow axis.  The swing-check-specific details are the
        larger hinged body chamber, raised bolted bonnet, and side hinge boss.
        """
        import math

        flgD = float(fp.FlgD)
        flgt = float(fp.Flgt)
        flgDrf = float(fp.FlgDrf)
        flgTrf = float(fp.FlgTrf)
        flgDf = float(fp.FlgDf)
        flgF = float(fp.FlgF)
        flgN = int(fp.FlgN)

        pipe_od = pipe_OD.get(fp.PSize, max(flgDrf * 0.65, 1.0))
        bore_r = max(pipe_od * 0.95 / 2.0, 1.0)
        bottom_h = float(getattr(fp, "BottomH", 0)) or max(pipe_od * 0.9, flgDrf * 0.45)
        top_h = float(getattr(fp, "TopH", 0)) or max(pipe_od * 1.8, flgD * 0.85)

        def make_bl_flange(z_face, face_up):
            sign = 1.0 if face_up else -1.0
            base = Part.Face(Part.Wire(Part.makeCircle(flgD / 2.0)))
            if flgN > 0 and flgF > 0 and flgDf > 0:
                hole = Part.Face(
                    Part.Wire(
                        Part.makeCircle(
                            flgF / 2.0,
                            FreeCAD.Vector(flgDf / 2.0, 0, 0),
                            FreeCAD.Vector(0, 0, 1),
                        )
                    )
                )
                hole.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 360.0 / flgN / 2.0)
                for i in range(flgN):
                    base = base.cut(hole)
                    hole.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 360.0 / flgN)

            flange = base.extrude(FreeCAD.Vector(0, 0, sign * flgt))
            if flgTrf > 0 and flgDrf > 0:
                rf = Part.makeCylinder(
                    flgDrf / 2.0,
                    flgTrf,
                    FreeCAD.Vector(0, 0, 0),
                    FreeCAD.Vector(0, 0, -sign),
                )
                flange = flange.fuse(rf)
            flange.translate(FreeCAD.Vector(0, 0, z_face + flgTrf * sign))
            return flange

        flange_bot = make_bl_flange(-H / 2.0, face_up=True)
        flange_top = make_bl_flange(H / 2.0, face_up=False)

        sleeve_r = max(flgDrf / 2.0, bore_r + max(6.0, flgt * 0.35))
        sleeve = Part.makeCylinder(
            sleeve_r,
            H,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )

        chamber_len = max(pipe_od * 1.55, min(H - 2.0 * flgt, H * 0.58))
        chamber_r = max(
            bore_r + max(8.0, flgt * 0.35),
            min(flgD * 0.46, bottom_h * 0.92, top_h * 0.55),
        )
        chamber = Part.makeCylinder(
            chamber_r,
            chamber_len,
            FreeCAD.Vector(0, 0, -chamber_len / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )

        # Raised bonnet and cover plate.  These are intentionally round in plan
        # so the generated model remains robust across the full ASME size range.
        cover_base_y = min(chamber_r * 0.70, top_h * 0.45)
        cover_top_y = max(top_h, cover_base_y + max(12.0, flgt * 0.45))
        cover_h = cover_top_y - cover_base_y
        cover_r = max(
            pipe_od * 0.42,
            min(chamber_len * 0.34, chamber_r * 0.78, flgD * 0.34),
        )
        bonnet = Part.makeCone(
            cover_r * 1.18,
            cover_r * 0.82,
            cover_h,
            FreeCAD.Vector(0, cover_base_y, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        cover_plate_t = max(6.0, flgt * 0.18)
        cover_plate = Part.makeCylinder(
            cover_r * 1.05,
            cover_plate_t,
            FreeCAD.Vector(0, cover_top_y - cover_plate_t * 0.45, 0),
            FreeCAD.Vector(0, 1, 0),
        )

        # External hinge boss and end caps.
        hinge_r = max(6.0, min(pipe_od * 0.12, chamber_r * 0.18))
        hinge_len = max(flgD * 0.58, hinge_r * 5.0)
        hinge_y = min(chamber_r * 0.46, bottom_h * 0.72)
        hinge_z = -min(chamber_len * 0.20, H * 0.09)
        hinge = Part.makeCylinder(
            hinge_r,
            hinge_len,
            FreeCAD.Vector(-hinge_len / 2.0, hinge_y, hinge_z),
            FreeCAD.Vector(1, 0, 0),
        )
        cap_t = max(4.0, hinge_r * 0.55)
        cap_l = Part.makeCylinder(
            hinge_r * 1.45,
            cap_t,
            FreeCAD.Vector(-hinge_len / 2.0 - cap_t * 0.35, hinge_y, hinge_z),
            FreeCAD.Vector(1, 0, 0),
        )
        cap_r = Part.makeCylinder(
            hinge_r * 1.45,
            cap_t,
            FreeCAD.Vector(hinge_len / 2.0 - cap_t * 0.65, hinge_y, hinge_z),
            FreeCAD.Vector(1, 0, 0),
        )

        valve = flange_bot.fuse(flange_top)
        for shape in (sleeve, chamber, bonnet, cover_plate, hinge, cap_l, cap_r):
            valve = valve.fuse(shape)

        # Cover bolts are fused with a small overlap into the cover plate.
        bolt_count = max(6, min(16, int(round(cover_r / 18.0)) * 2))
        bolt_r = max(2.0, min(8.0, cover_r * 0.045))
        bolt_h = max(3.0, cover_plate_t * 0.55)
        bolt_circle = cover_r * 0.72
        bolt_y = cover_top_y + cover_plate_t * 0.06
        for i in range(bolt_count):
            a = 2.0 * math.pi * i / bolt_count
            pos = FreeCAD.Vector(
                bolt_circle * math.cos(a),
                bolt_y,
                bolt_circle * math.sin(a),
            )
            bolt = Part.makeCylinder(
                bolt_r,
                bolt_h,
                pos,
                FreeCAD.Vector(0, 1, 0),
            )
            valve = valve.fuse(bolt)

        bore = Part.makeCylinder(
            bore_r,
            H + 2.0 * flgt + 4.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - flgt - 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        valve = valve.cut(bore)
        valve = valve.removeSplitter()
        fp.Shape = valve

        fp.Ports = [
            FreeCAD.Vector(0, 0, H / 2.0),
            FreeCAD.Vector(0, 0, -H / 2.0),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, 1),
            FreeCAD.Vector(0, 0, -1),
        ]

        return FeatureGeometry(
            shape=fp.Shape,
            ports=tuple(fp.Ports),
            directions=tuple(fp.PortDirections),
        )


register_strategy(SwingCheckValveStrategy())
