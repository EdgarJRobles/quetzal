# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD adapter for declarative :class:`CommandSpec` objects."""

from __future__ import annotations

from typing import Any

import FreeCAD
import FreeCADGui

from ...application.command_registry import REGISTRY, CommandSpec
from ...application.macro_source import command_source


def document_open() -> bool:
    return FreeCAD.ActiveDocument is not None


class GuiCommand:
    """Thin FreeCAD command object backed by a CommandSpec."""

    __slots__ = ("spec",)

    def __init__(self, spec: CommandSpec) -> None:
        self.spec = spec

    def GetResources(self) -> dict:
        resources = {
            "Pixmap": self.spec.icon_name,
            "MenuText": self.spec.menu_text,
        }
        if self.spec.tooltip is not None:
            resources["ToolTip"] = self.spec.tooltip
        if self.spec.accel is not None:
            resources["Accel"] = self.spec.accel
        return resources

    def IsActive(self) -> bool:
        predicate = self.spec.is_active or document_open
        try:
            return bool(predicate())
        except Exception:
            return False

    def Activated(self) -> Any:
        if self.spec.handler is None:
            raise RuntimeError(f"Command {self.spec.name!r} has no handler")
        return self.spec.handler()


def register_spec(spec: CommandSpec, replace: bool = False) -> CommandSpec:
    """Register a declarative command with FreeCAD and the metadata registry."""

    REGISTRY.add(spec, replace=replace)
    source = spec.macro_source or command_source(spec.handler or (lambda: None))
    FreeCADGui.addCommand(spec.name, GuiCommand(spec), source)
    return spec
