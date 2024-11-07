import inspect
import os

import FreeCAD
import FreeCADGui

__version__ = "1.1.0"

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
    (list, num) = inspect.getsourcelines(cmdObject.Activated)
    pos = 0
    # check for indentation
    while list[1][pos] == " " or list[1][pos] == "\t":
        pos += 1
    source = ""
    for i in range(len(list) - 1):
        source += list[i + 1][pos:]
    FreeCADGui.addCommand(name, cmdObject, source)
    # FreeCAD.Console.PrintMessage("Quetzal " + name + "source: <<< " + source + " >>>\n")
