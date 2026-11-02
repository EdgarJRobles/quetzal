# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD implementation of the PypeLineService port."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import FreeCAD

import pFeatures

from . import pype_line_tools


class FreeCADPypeLineService:
    def create(self, spec, label: str, color, append_to: Any = None) -> Any:
        if not FreeCAD.GuiUp and append_to is None:
            document = FreeCAD.ActiveDocument
            line = document.addObject("Part::FeaturePython", label)
            pFeatures.PypeLine2(
                line,
                spec.rating,
                spec.dn,
                spec.od,
                spec.thk,
                spec.bend_radius,
                label,
            )
            document.recompute()
            return line

        import pCmd

        if append_to is not None:
            existing = append_to
            view = getattr(existing, "ViewObject", None)
            append_color = getattr(view, "ShapeColor", color)
            return pCmd.makePypeLine2(
                DN=spec.dn,
                PRating=spec.rating,
                OD=spec.od,
                thk=spec.thk,
                BR=spec.bend_radius,
                pl=existing.Label,
                color=append_color,
            )
        return pCmd.makePypeLine2(
            DN=spec.dn,
            PRating=spec.rating,
            OD=spec.od,
            thk=spec.thk,
            BR=spec.bend_radius,
            lab=label,
            color=color,
        )

    def spec(self, line: Any):
        return pype_line_tools.spec_from_line(line)

    def pieces(self, line: Any) -> Sequence[Any]:
        return pype_line_tools.line_pieces(line)

    def apply(self, line: Any, spec, update_children: bool = True) -> int:
        return pype_line_tools.apply_spec(line, spec, update_children)

    def clone(self, source: Any, label: str) -> Any:
        return pype_line_tools.clone_line(source, label)

    def assign(self, line: Any, objects: Iterable[Any]) -> int:
        return pype_line_tools.assign_to_line(line, objects)

    def select(self, line: Any) -> int:
        return pype_line_tools.select_pieces(line)
