# SPDX-License-Identifier: LGPL-3.0-or-later
"""GUI commands: Quetzal_ImportPCF and Quetzal_ExportPCF."""

import os

import FreeCAD
import FreeCADGui
from PySide import QtGui

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate

_FILTER = "Piping Component File (*.pcf *.PCF)"
_PARAMS = "User parameter:BaseApp/Preferences/Mod/Quetzal"


def _last_dir():
    return FreeCAD.ParamGet(_PARAMS).GetString("PcfLastDir", os.path.expanduser("~"))


def _remember_dir(path):
    FreeCAD.ParamGet(_PARAMS).SetString("PcfLastDir", os.path.dirname(path))


class ImportPCF:
    def GetResources(self):
        return {
            "Pixmap": "Quetzal_ImportPCF",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_ImportPCF", "Import PCF"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_ImportPCF",
                "Import a Piping Component File (.pcf) into the active document "
                "as Quetzal pipes and fittings",
            ),
        }

    def IsActive(self):
        return True

    def Activated(self):
        filename, _f = QtGui.QFileDialog.getOpenFileName(
            FreeCADGui.getMainWindow(), translate("Quetzal_ImportPCF", "Import PCF"),
            _last_dir(), _FILTER)
        if not filename:
            return
        _remember_dir(filename)
        from pcf import pcf_import

        if FreeCAD.ActiveDocument is None:
            pcf_import.open(filename)
        else:
            pcf_import.insert(filename, FreeCAD.ActiveDocument.Name)
        FreeCADGui.SendMsgToActiveView("ViewFit")


class ExportPCF:
    def GetResources(self):
        return {
            "Pixmap": "Quetzal_ExportPCF",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_ExportPCF", "Export PCF"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_ExportPCF",
                "Export the selected pipes, fittings and pypelines (or the whole "
                "document if nothing is selected) to Piping Component Files (.pcf), "
                "one per pypeline",
            ),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        objects = FreeCADGui.Selection.getSelection() or FreeCAD.ActiveDocument.Objects
        default = os.path.join(_last_dir(), FreeCAD.ActiveDocument.Label + ".pcf")
        filename, _f = QtGui.QFileDialog.getSaveFileName(
            FreeCADGui.getMainWindow(), translate("Quetzal_ExportPCF", "Export PCF"),
            default, _FILTER)
        if not filename:
            return
        _remember_dir(filename)
        from pcf import pcf_export

        pcf_export.export(objects, filename)


FreeCADGui.addCommand("Quetzal_ImportPCF", ImportPCF())
FreeCADGui.addCommand("Quetzal_ExportPCF", ExportPCF())
