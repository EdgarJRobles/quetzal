# SPDX-License-Identifier: LGPL-3.0-or-later
"""Compatibility bridge between WorkbenchState and legacy FreeCAD attributes."""

from __future__ import annotations

from typing import Optional

import FreeCAD

from ...application.workbench_state import default_workbench_state


def get_active_pype_line() -> Optional[str]:
    state = default_workbench_state().active_pype_line
    if state is not None:
        return state
    return getattr(FreeCAD, "__activePypeLine__", None)


def set_active_pype_line(value: Optional[str]) -> None:
    default_workbench_state().set_active_pype_line(value)
    FreeCAD.__activePypeLine__ = value


def get_active_frame_line() -> Optional[str]:
    state = default_workbench_state().active_frame_line
    if state is not None:
        return state
    return getattr(FreeCAD, "__activeFrameLine__", None)


def set_active_frame_line(value: Optional[str]) -> None:
    default_workbench_state().set_active_frame_line(value)
    FreeCAD.__activeFrameLine__ = value


def clear_workbench_state() -> None:
    default_workbench_state().clear()
    FreeCAD.__activePypeLine__ = None
    FreeCAD.__activeFrameLine__ = None
