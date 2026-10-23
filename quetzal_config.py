# SPDX-License-Identifier: LGPL-3.0-or-later

import os

import FreeCAD
import FreeCADGui

__version__ = "1.8.11"

_dir = os.path.dirname(__file__)
ICONPATH = os.path.join(_dir, "iconz")
TRANSLATIONSPATH = os.path.join(_dir, "translationz")
UIPATH = os.path.join(_dir, "dialogz")

FREECADVERSION = float(FreeCAD.Version()[0] + "." + FreeCAD.Version()[1])


def get_icon_path(icon_name: str) -> str:
    """Returns the path to the SVG icon."""
    return os.path.join(ICONPATH, icon_name + ".svg")


# helper -------------------------------------------------------------------
# FreeCAD TemplatePyMod module
# (c) 2007 Juergen Riegel LGPL


def addCommand(name, cmdObject):
    """Register a command and record its metadata in the shared registry.

    The source is passed to FreeCADGui.addCommand so the macro recorder keeps
    producing a readable Python snippet.  Existing command classes keep their
    GetResources/Activated implementation.
    """
    from quetzal.application.command_registry import REGISTRY
    from quetzal.application.macro_source import command_source
    from quetzal.ui.layout import group_of

    source = command_source(cmdObject.Activated)
    FreeCADGui.addCommand(name, cmdObject, source)
    try:
        REGISTRY.add_legacy(name, cmdObject, source, group_of(name))
    except Exception as exc:
        FreeCAD.Console.PrintWarning(f"Quetzal: could not record command {name}: {exc}\n")
