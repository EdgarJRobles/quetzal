# SPDX-License-Identifier: LGPL-3.0-or-later
"""Part primitives for Flange, copied from the legacy operation order.

Operation order is a compatibility contract: the WN builder fillets
``Edges[2]`` and the LJ builder fillets ``Edges[7 + 3n]``. Reordering the
booleans changes those indices and therefore the resulting solid.
"""

from __future__ import annotations

from typing import Any

import FreeCAD
import Part

from ...domain.flange import FlangeSpec

_ORIGIN = (0.0, 0.0, 0.0)


def origin() -> Any:
    return FreeCAD.Vector(*_ORIGIN)


def z_axis() -> Any:
    return FreeCAD.Vector(0, 0, 1)


def body(spec: FlangeSpec) -> Any:
    """Disc + bore + bolt holes + extrusion (legacy execute B0)."""

    base = Part.Face(Part.Wire(Part.makeCircle(spec.D / 2)))
    if spec.d > 0:
        base = base.cut(Part.Face(Part.Wire(Part.makeCircle(spec.d / 2))))
    if spec.n > 0:
        hole = Part.Face(
            Part.Wire(
                Part.makeCircle(
                    spec.f / 2,
                    FreeCAD.Vector(spec.df / 2, 0, 0),
                    z_axis(),
                )
            )
        )
        hole.rotate(origin(), z_axis(), spec.bolt_hole_phase)
        for _ in range(spec.n):
            base = base.cut(hole)
            hole.rotate(origin(), z_axis(), 360.0 / spec.n)
    return base.extrude(FreeCAD.Vector(0, 0, spec.t))


def add_hub_and_raised_face(shape: Any, spec: FlangeSpec) -> Any:
    """Hub and ring raised face shared by SO/WN/SW/LJ (legacy execute B2)."""

    if spec.has_hub:
        neck = Part.makeCylinder(spec.ODp / 2, spec.T1, origin(), z_axis()).cut(
            Part.makeCylinder(spec.d / 2, spec.T1, origin(), z_axis())
        )
        shape = shape.fuse(neck)
    if spec.has_raised_face:
        raised = Part.makeCylinder(spec.drf / 2, spec.trf, origin(), z_axis() * -1).cut(
            Part.makeCylinder(spec.d / 2, spec.trf, origin(), z_axis() * -1)
        )
        shape = shape.fuse(raised)
    return shape


def add_solid_raised_face(shape: Any, spec: FlangeSpec) -> Any:
    """Blind-flange raised face: solid cylinder, no bore (legacy B6)."""

    if spec.has_solid_raised_face:
        shape = shape.fuse(Part.makeCylinder(spec.drf / 2, spec.trf, origin(), z_axis() * -1))
    return shape


def add_weld_neck(shape: Any, spec: FlangeSpec) -> Any:
    """Weld-neck cone, splitter and edge-2 fillet (legacy execute B3)."""

    if not spec.has_weld_neck:
        return shape
    try:
        cone = Part.makeCone(
            spec.dwn / 2,
            spec.ODp / 2,
            spec.twn,
            z_axis() * float(spec.t),
        ).cut(Part.makeCylinder(spec.d / 2, spec.twn, z_axis() * float(spec.t)))
        shape = shape.fuse(cone)
        shape = shape.removeSplitter()
        shape = shape.makeFillet(spec.R, [shape.Edges[2]])
    except Exception:
        # Preserve the legacy best-effort behaviour (and partial progress).
        pass
    return shape


def add_lap_joint(shape: Any, spec: FlangeSpec) -> Any:
    """Lap-joint splitter and fillet selected from the bolt count (legacy B4)."""

    shape = shape.removeSplitter()
    index = spec.lj_fillet_edge
    edge = shape.Edges[index] if index is not None else []
    return shape.makeFillet(spec.R, edge)


def add_socket(shape: Any, spec: FlangeSpec) -> Any:
    """Socket-weld pocket (legacy execute B5)."""

    if spec.has_socket:
        shape = shape.cut(
            Part.makeCylinder(
                spec.B2 / 2,
                spec.Y,
                z_axis() * float(spec.T1 - spec.trf),
                z_axis() * -1,
            )
        )
        shape = shape.removeSplitter()
    return shape


def configure_view(fp: Any) -> None:
    """Display-only tessellation setting; safe in console mode."""

    if FreeCAD.GuiUp and getattr(fp, "ViewObject", None) is not None:
        fp.ViewObject.Deviation = 0.10
