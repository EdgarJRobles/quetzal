# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy: flanged."""

from __future__ import annotations

import FreeCAD
import Part

from ...domain.pipe_sizes import PIPE_OUTSIDE_DIAMETERS_MM as pipe_OD
from ..geometry import FeatureGeometry
from ...application.valve import ValveContext
from .strategy import register_strategy


class FlangedValveStrategy:
    key = "flanged"

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        fp = ctx.feature
        H = ctx.height
        """Build a Trunnion Ball valve body with raised-face flanges.

        Geometry (all dimensions in mm, local Z is the flow axis):

          - Two raised-face blind flanges (BL style):
              bottom flange face at z = -H/2  (raised face projects toward -Z)
              top    flange face at z = +H/2  (raised face projects toward +Z)

          - Connecting (outer) cylinder:
              diameter = flgDrf (same diameter as raised face)
              from z = -H/2+flgTrf to z = +H/2-flgTrf

          - Center body cylinder:
              diameter = connecting_cylinderOD  (same outer shell)
              from z = -H/2 + flange_t*3  to  z = +H/2 - flange_t*3
              (height = H - 6*flange_t)

          - Handle stem + paddle attached at the outer equator of the center body.

        Ports are at (0,0,-H/2) and (0,0,+H/2).
        """
        import math

        flgD = float(fp.FlgD)  # flange outer diameter
        flgt = float(fp.Flgt)  # flange thickness (t in the table)
        flgDrf = float(fp.FlgDrf)  # raised-face diameter
        flgTrf = float(fp.FlgTrf)  # raised-face thickness
        flgDf = float(fp.FlgDf)  # bolt-circle diameter
        flgF = float(fp.FlgF)  # bolt-hole diameter
        flgN = int(fp.FlgN)  # number of bolt holes

        # Pipe OD for the nominal size from the module-level dictionary
        pipe_od = pipe_OD.get(fp.PSize, float(fp.ODBody))

        # Connecting cylinder OD (average of pipe OD and flange OD)
        conn_cyl_OD = flgDrf

        # Center body height = H - 6 * flange_t
        body_h = H - 6.0 * flgt
        if body_h < 1.0:
            body_h = 1.0  # safety floor

        # ── build one blind flange (BL style) ──────────────────────────────
        # The Flange.execute() path for "BL" builds from z=0 upward for
        # thickness (t ), with raised face going downward (toward -Z).
        # Here we replicate that geometry directly as Part solids so we can
        # position each flange independently.

        def make_bl_flange(z_face, face_up):
            """Return a solid blind flange positioned so that its mating
            face (raised-face surface) lies at z = z_face.
            face_up=True  -> flange body extends in +Z, raised face in -Z
            face_up=False -> flange body extends in -Z, raised face in +Z
            """
            sign = 1.0 if face_up else -1.0

            # Annular disc (flange body, no bore for BL)
            base = Part.Face(Part.Wire(Part.makeCircle(flgD / 2)))
            # Cut bolt holes, rotated to match standard Flange class offset
            if flgN > 0:
                hole = Part.Face(
                    Part.Wire(
                        Part.makeCircle(
                            flgF / 2,
                            FreeCAD.Vector(flgDf / 2, 0, 0),
                            FreeCAD.Vector(0, 0, 1),
                        )
                    )
                )
                hole.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 360.0 / flgN / 2)
                for i in range(flgN):
                    base = base.cut(hole)
                    hole.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 360.0 / flgN)

            # Extrude disc body away from the face
            body_thickness = flgt
            flange = base.extrude(FreeCAD.Vector(0, 0, sign * body_thickness))

            # Raised face (solid disc, no bore for BL) toward the mating side
            if flgTrf > 0 and flgDrf > 0:
                rf = Part.makeCylinder(
                    flgDrf / 2,
                    flgTrf,
                    FreeCAD.Vector(0, 0, 0),
                    FreeCAD.Vector(0, 0, -sign),
                )
                flange = flange.fuse(rf)

            # Translate so the mating face lands at z_face
            flange.translate(FreeCAD.Vector(0, 0, z_face + flgTrf * sign))
            return flange

        flange_bot = make_bl_flange(-H / 2.0, face_up=True)  # mating face at -H/2
        flange_top = make_bl_flange(H / 2.0, face_up=False)  # mating face at +H/2

        # ── connecting (outer) cylinder ────────────────────────────────────
        conn_cyl = Part.makeCylinder(
            conn_cyl_OD / 2.0,
            H,
            FreeCAD.Vector(0, 0, -(H / 2.0)),
            FreeCAD.Vector(0, 0, 1),
        )

        # ── center body cylinder (diameter = flgD) ────────────────────────
        body_z0 = -H / 2.0 + flgt * 3.0
        center_body = Part.makeCylinder(
            flgD / 2.0,
            body_h,
            FreeCAD.Vector(0, 0, body_z0),
            FreeCAD.Vector(0, 0, 1),
        )

        # bore hole along Z axis (diameter = 95% of pipe_OD, length = 2 mm longer than valve to ensure clean cut)
        bore_r = pipe_od * 0.95 / 2.0
        bore = Part.makeCylinder(
            bore_r,
            H + 2.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - 1.0),
            FreeCAD.Vector(0, 0, 1),
        )

        # ── fuse main shapes
        valve = flange_bot.fuse(flange_top)
        valve = valve.fuse(conn_cyl)
        valve = valve.fuse(center_body)

        # ── actuator (handle or gearbox) ──────────────────────────────────
        actuator = getattr(fp, "Actuator", "Handle")

        if actuator == "Gearbox":
            # -- Gearbox cylinder ---------------------------------------
            # Rises from (0,0,0) in the +Y direction, diameter = pipe_od
            gearbox_h = pipe_od + 100.0
            gearbox = Part.makeCylinder(
                pipe_od / 2.0,
                gearbox_h,
                FreeCAD.Vector(0, 0, 0),
                FreeCAD.Vector(0, 1, 0),
            )

            # -- Handwheel axle -----------------------------------------
            # Cylinder based at (0, pipe_od+100, -pipe_od/2)
            # diameter = min(25.4, pipe_od), length = pipe_od/2, direction +X
            axle_r = min(25.4, pipe_od) / 2.0
            axle_len = pipe_od / 2
            axle_base = FreeCAD.Vector(0, pipe_od + 100.0, -pipe_od / 2.0)
            axle = Part.makeCylinder(
                axle_r,
                axle_len,
                axle_base,
                FreeCAD.Vector(1, 0, 0),
            )

            # -- Four spokes around the axle ----------------------------
            # Spokes originate at the far end of the axle:
            #   spoke_origin = axle_base + (pipe_od, 0, 0)
            # They are extruded at 60 deg from the X axis in the four
            # +/-Y and +/-Z quadrants, each of length spoke_len, radius 10 mm.
            spoke_len = (pipe_od + 75.0) / math.cos(math.radians(30.0))
            spoke_r = 10.0
            spoke_origin = FreeCAD.Vector(
                axle_base.x + axle_len,
                axle_base.y,
                axle_base.z,
            )
            # The four spoke directions are at 60 deg from X toward +Y, -Y, +Z, -Z
            spoke_angle = 60  # degrees
            cos60 = math.cos(math.radians(spoke_angle))
            sin60 = math.sin(math.radians(spoke_angle))
            spoke_dirs = [
                FreeCAD.Vector(cos60, sin60, 0),  # +Y quadrant
                FreeCAD.Vector(cos60, -sin60, 0),  # -Y quadrant
                FreeCAD.Vector(cos60, 0, sin60),  # +Z quadrant
                FreeCAD.Vector(cos60, 0, -sin60),  # -Z quadrant
            ]
            spokes = None
            for sd in spoke_dirs:
                spoke = Part.makeCylinder(
                    spoke_r,
                    spoke_len,
                    spoke_origin,
                    sd,
                )
                spokes = spoke if spokes is None else spokes.fuse(spoke)

            # -- Handwheel torus ----------------------------------------
            # Center of the torus is at:
            #   x = spoke_origin.x + (pipe_od + 75) * sin(30 deg)
            #   y = spoke_origin.y, z = spoke_origin.z
            # Torus axis = X axis (same as axle)
            # Radius1 = pipe_od + 75, Radius2 = 12
            torus_cx = spoke_origin.x + spoke_len * math.sin(math.radians(90 - spoke_angle))
            torus_center = FreeCAD.Vector(torus_cx, spoke_origin.y, spoke_origin.z)
            torus = Part.makeTorus(
                pipe_od + 75.0,
                12.0,
                torus_center,
                FreeCAD.Vector(1, 0, 0),
            )

            valve = valve.fuse(gearbox)
            valve = valve.fuse(axle)
            if spokes is not None:
                valve = valve.fuse(spokes)
            valve = valve.fuse(torus)
            valve = valve.cut(bore)
            valve = valve.removeSplitter()
            fp.Shape = valve

        else:
            # -- Handle (stem + paddle) ---------------------------------
            # Stem extends the lesser of 25 mm or the pipe outer diameter above the valve body
            stem_y0 = 0
            stem_height = min(25.0, pipe_od) + flgD / 2.0
            stem = Part.makeCylinder(
                5.0,
                stem_height,
                FreeCAD.Vector(0, stem_y0, 0),
                FreeCAD.Vector(0, 1, 0),
            )

            hw = min(25.0, pipe_od) / 2.0
            ht = 1.5
            paddle_base_y = stem_y0 + stem_height - 5.0
            py0 = paddle_base_y
            py1 = paddle_base_y + 15.0
            pz_end = max(50.0, H)

            P0 = FreeCAD.Vector(0, py0, -15.0)
            P1 = FreeCAD.Vector(0, py0, 15.0)
            P2 = FreeCAD.Vector(0, py1, 30.0)
            P3 = FreeCAD.Vector(0, py1, pz_end)

            def _seg_prism(start, end):
                """Rectangular prism from start to end with cross-section 2*hw x 2*ht."""
                seg = end - start
                length = seg.Length
                if length < 1e-6:
                    return None
                d = FreeCAD.Vector(seg).normalize()
                up = FreeCAD.Vector(0, 0, 1)
                if abs(d.dot(up)) > 0.99:
                    up = FreeCAD.Vector(0, 1, 0)
                ax1 = d.cross(up).normalize()
                ax2 = d.cross(ax1).normalize()
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

            valve = valve.fuse(stem)
            valve = valve.fuse(handle)
            valve = valve.cut(bore)
            valve = valve.removeSplitter()
            fp.Shape = valve

        # ── ports at flange faces ─────────────────────────────────────────
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


register_strategy(FlangedValveStrategy())
