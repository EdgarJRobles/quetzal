import os

import FreeCAD
import FreeCADGui
from PySide.QtCore import QT_TRANSLATE_NOOP

from . import RESOURCE_PATH, cut_list_ui


class cutListCommand:
    toolbarName = "Cut List"
    commandName = "createCutList"

    def GetResources(self):
        Icon = os.path.join(RESOURCE_PATH, "cut_list_icon.svg")
        return {
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_CreateCutList", "createCutList"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_CreateCutList", "Create a new Cut List from Dodo Beams"
            ),
            "Pixmap": Icon,
        }

    def Activated(self):
        cut_list_ui.openCutListDialog()

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return FreeCAD.ActiveDocument is not None


FreeCADGui.addCommand("Quetzal_CreateCutList", cutListCommand())
