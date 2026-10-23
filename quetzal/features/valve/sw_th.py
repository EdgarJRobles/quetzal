# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy: sw_th."""

from __future__ import annotations

import FreeCAD
import Part

from ..geometry import FeatureGeometry
from ...application.valve import ValveContext
from .strategy import register_strategy


class SocketThreadedValveStrategy:
    key = "sw_th"

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        fp = ctx.feature
        H = ctx.height
        import math

        OD = float(fp.OD)
        ODBody = float(fp.ODBody)
        E = float(fp.E)

        # ── hexagonal body ─────────────────────────────────────────────────────
        hex_r = (ODBody / 2.0) / math.cos(math.radians(30))
        pts = []
        for i in range(6):
            angle = math.radians(i * 60)
            pts.append(FreeCAD.Vector(hex_r * math.cos(angle), hex_r * math.sin(angle), 0))
        pts.append(pts[0])
        poly = Part.makePolygon(pts)
        face = Part.Face(poly)
        body = face.extrude(FreeCAD.Vector(0, 0, H))
        body.translate(FreeCAD.Vector(0, 0, -H / 2))

        # ── through bore  (ID = OD - 6 mm) ────────────────────────────────────
        bore_r = (OD - 6.0) / 2.0
        bore = Part.makeCylinder(bore_r, H, FreeCAD.Vector(0, 0, -H / 2), FreeCAD.Vector(0, 0, 1))
        body = body.cut(bore)

        # ── socket / thread pockets ────────────────────────────────────────────
        sock_r = OD / 2.0
        sock_pos = Part.makeCylinder(
            sock_r, E, FreeCAD.Vector(0, 0, H / 2), FreeCAD.Vector(0, 0, -1)
        )
        sock_neg = Part.makeCylinder(
            sock_r, E, FreeCAD.Vector(0, 0, -H / 2), FreeCAD.Vector(0, 0, 1)
        )
        body = body.cut(sock_pos)
        body = body.cut(sock_neg)

        # ── handle stem ────────────────────────────────────────────────────────
        stem_y0 = ODBody / 2.0
        stem_height = min(25.0, OD)
        stem = Part.makeCylinder(
            5.0, stem_height, FreeCAD.Vector(0, stem_y0, 0), FreeCAD.Vector(0, 1, 0)
        )

        # ── handle paddle — per-segment extrusions ─────────────────────────────
        # Spine waypoints in the YZ plane:
        #   P0 = (0, py0, -15)
        #   P1 = (0, py0, +15)   segment 0: straight up in Z, length 30
        #   P2 = (0, py1, +30)   segment 1: diagonal (+Y, +Z), length sqrt(2)*15
        #   P3 = (0, py1, pz_end) segment 2: straight up in Z
        #
        # Each segment is extruded as a rectangular prism with cross-section
        # (2*hw) x (2*ht) perpendicular to the segment direction, then fused.
        # It ain't perfect, as it has gaps at the bends in the handle, so maybe fix that when you get a chance
        hw = min(25.0, OD) / 2.0
        ht = 1.5  # half-thickness = 1.5 mm (3 mm total)
        paddle_base_y = stem_y0 + stem_height - 5.0
        py0 = paddle_base_y
        py1 = paddle_base_y + 15.0
        pz_end = max(50.0, H)

        P0 = FreeCAD.Vector(0, py0, -15.0)
        P1 = FreeCAD.Vector(0, py0, 15.0)
        P2 = FreeCAD.Vector(0, py1, 30.0)
        P3 = FreeCAD.Vector(0, py1, pz_end)

        def _seg_prism(start, end):
            """Solid rectangular prism from start to end with cross-section 2*hw x 2*ht.
            The cross-section is centered on start, in the plane perpendicular to
            (end - start).  Width (2*hw) lies along the global X axis; thickness
            (2*ht) lies in the perpendicular-to-X direction within that plane.
            """
            seg = end - start
            length = seg.Length
            if length < 1e-6:
                return None
            d = FreeCAD.Vector(seg).normalize()

            # Choose a reference 'up' not parallel to d
            up = FreeCAD.Vector(0, 0, 1)
            if abs(d.dot(up)) > 0.99:
                up = FreeCAD.Vector(0, 1, 0)

            # Two orthogonal in-plane axes
            ax1 = d.cross(up).normalize()  # lies in plane perp to d
            ax2 = d.cross(ax1).normalize()  # lies in plane perp to d, perp to ax1

            # Rectangle corners at start
            c0 = start + ax1 * hw + ax2 * ht
            c1 = start - ax1 * hw + ax2 * ht
            c2 = start - ax1 * hw - ax2 * ht
            c3 = start + ax1 * hw - ax2 * ht
            wire = Part.Wire(
                [
                    Part.makeLine(c0, c1),
                    Part.makeLine(c1, c2),
                    Part.makeLine(c2, c3),
                    Part.makeLine(c3, c0),
                ]
            )
            face = Part.Face(wire)
            return face.extrude(d * length)

        prism0 = _seg_prism(P0, P1)
        prism1 = _seg_prism(P1, P2)
        prism2 = _seg_prism(P2, P3)

        handle = prism0
        if prism1:
            handle = handle.fuse(prism1)
        if prism2:
            handle = handle.fuse(prism2)

        valve = body.fuse(stem)
        valve = valve.fuse(handle)
        valve = valve.removeSplitter()
        fp.Shape = valve

        # ── ports ──────────────────────────────────────────────────────────────
        fp.Ports = [
            FreeCAD.Vector(0, 0, H / 2 - E),
            FreeCAD.Vector(0, 0, -H / 2 + E),
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


register_strategy(SocketThreadedValveStrategy())
