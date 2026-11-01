# SPDX-License-Identifier: LGPL-3.0-or-later
"""Explicit workbench selection/state instead of attributes on FreeCAD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkbenchState:
    active_pype_line: Optional[str] = None
    active_frame_line: Optional[str] = None

    def set_active_pype_line(self, value: Optional[str]) -> None:
        self.active_pype_line = value

    def set_active_frame_line(self, value: Optional[str]) -> None:
        self.active_frame_line = value

    def clear(self) -> None:
        self.active_pype_line = None
        self.active_frame_line = None


_DEFAULT_STATE = WorkbenchState()


def default_workbench_state() -> WorkbenchState:
    """Process-wide state used by forms when no explicit state is injected."""

    return _DEFAULT_STATE
