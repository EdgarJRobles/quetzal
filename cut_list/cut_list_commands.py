import os

import FreeCAD
import FreeCADGui

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP

from . import RESOURCE_PATH, cut_list_ui


class cutListCommand:
    toolbarName = "Cut List"
    commandName = "createCutList"

    def GetResources(self):
        return {
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_CreateCutList", "createCutList"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_CreateCutList", "Create a new Cut List from Quetzal Beams"
            ),
            "Pixmap": "Quetzal_CreateCutList",
        }

    def Activated(self):
        cut_list_ui.openCutListDialog()

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return FreeCAD.ActiveDocument is not None


FreeCADGui.addCommand("Quetzal_CreateCutList", cutListCommand())
