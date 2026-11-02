# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD implementation of the PypeLineService port."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from . import pype_line_tools


class FreeCADPypeLineService:
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
