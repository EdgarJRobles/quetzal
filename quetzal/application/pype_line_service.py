# SPDX-License-Identifier: LGPL-3.0-or-later
"""Port for pipe-line batch operations used by the manager UI."""

from __future__ import annotations

from typing import Any, Iterable, Protocol, Sequence

from .pype_line_spec import PypeLineSpec


class PypeLineService(Protocol):
    def spec(self, line: Any) -> PypeLineSpec:
        """Read the line parameters."""

    def pieces(self, line: Any) -> Sequence[Any]:
        """Return the line's pipes, bends and branch children."""

    def apply(self, line: Any, spec: PypeLineSpec, update_children: bool = True) -> int:
        """Apply the spec and return the number of updated pieces."""

    def clone(self, source: Any, label: str) -> Any:
        """Create a new line with the same parameters/path."""

    def assign(self, line: Any, objects: Iterable[Any]) -> int:
        """Move objects into the line group."""

    def select(self, line: Any) -> int:
        """Select the line pieces and return their count."""
