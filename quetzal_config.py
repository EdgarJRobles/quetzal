import os
import FreeCAD

__version__ = "1.1.0"

_dir = os.path.dirname(__file__)
ICONPATH = os.path.join(_dir, "iconz")
TRANSLATIONSPATH = os.path.join(_dir, "translationz")
UIPATH = os.path.join(_dir, "dialogz")

FREECADVERSION = float(FreeCAD.Version()[0] + "." + FreeCAD.Version()[1])


def get_icon_path(icon_name: str) -> str:
    """Returns the path to the SVG icon."""
    return os.path.join(ICONPATH, icon_name + ".svg")
