# SPDX-License-Identifier: LGPL-3.0-or-later
"""GUI commands: Quetzal_CreateIso, Quetzal_IsoFromPCF, Quetzal_UpdateIso."""

import os

import FreeCAD
import FreeCADGui
from PySide import QtGui

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate

_PARAMS = "User parameter:BaseApp/Preferences/Mod/Quetzal"


def _show(pages):
    if not pages:
        msg = translate("Quetzal_CreateIso",
                        "No Quetzal piping found to draw. Select pipes and fittings, a pypeline "
                        "group or a part container, or clear the selection to draw the whole "
                        "document.")
        FreeCAD.Console.PrintWarning("Isometric: " + msg + "\n")
        QtGui.QMessageBox.information(FreeCADGui.getMainWindow(),
                                      translate("Quetzal_CreateIso", "Create isometric"), msg)
        return
    pages[0].ViewObject.doubleClicked()  # one window only, on the first page
    FreeCAD.Console.PrintMessage(
        translate("Quetzal_CreateIso", "Isometric: {0} page(s) created").format(len(pages)) + "\n")


def _camera_rotation(doc):
    """Iso rotation matching the document's 3D view camera, or None without one.

    Uses the active view if it is a 3D view, else the document's first 3D view
    (a TechDraw page may be the active window)."""
    gdoc = FreeCADGui.getDocument(doc.Name)
    views = [gdoc.ActiveView] + list(gdoc.mdiViewsOfType("Gui::View3DInventor"))
    for view in views:
        if hasattr(view, "getCameraOrientation"):
            from iso import iso_layout

            cam = view.getCameraOrientation()
            look = cam.multVec(FreeCAD.Vector(0, 0, -1))
            up = cam.multVec(FreeCAD.Vector(0, 1, 0))
            return iso_layout.rotation_for_camera(tuple(look), tuple(up))
    return None


class CreateIso:
    def GetResources(self):
        return {
            "Pixmap": "Quetzal_CreateIso",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_CreateIso", "Create isometric"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_CreateIso",
                "Create a not-to-scale piping isometric (TechDraw page) of the selection, "
                "drawn as one line (e.g. a spool plus loose valves, gaskets and bolts), or "
                "one per pypeline in the whole document if nothing is selected. The iso "
                "faces the same way as the 3D view",
            ),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        from iso import iso_page

        doc = FreeCAD.ActiveDocument
        selection = FreeCADGui.Selection.getSelection() or None
        options = iso_page.default_options()
        options.rotation = _camera_rotation(doc)
        doc.openTransaction(translate("Transaction", "Create isometric"))
        try:
            pages = iso_page.pages_from_objects(doc, selection, options)
        finally:
            doc.commitTransaction()
        _show(pages)


class IsoFromPCF:
    def GetResources(self):
        return {
            "Pixmap": "Quetzal_IsoFromPCF",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_IsoFromPCF", "Isometric from PCF"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_IsoFromPCF",
                "Draw the isometric of a Piping Component File (.pcf) from any program",
            ),
        }

    def IsActive(self):
        return True

    def Activated(self):
        start = FreeCAD.ParamGet(_PARAMS).GetString("PcfLastDir", os.path.expanduser("~"))
        path, _f = QtGui.QFileDialog.getOpenFileName(
            FreeCADGui.getMainWindow(), translate("Quetzal_IsoFromPCF", "Isometric from PCF"),
            start, "Piping Component File (*.pcf *.PCF)")
        if not path:
            return
        FreeCAD.ParamGet(_PARAMS).SetString("PcfLastDir", os.path.dirname(path))
        from iso import iso_page

        doc = FreeCAD.ActiveDocument or FreeCAD.newDocument(
            os.path.splitext(os.path.basename(path))[0] + "_iso")
        _show(iso_page.pages_from_pcf(doc, path))


class UpdateIso:
    def GetResources(self):
        return {
            "Pixmap": "Quetzal_UpdateIso",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_UpdateIso", "Update isometric"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_UpdateIso",
                "Regenerate the selected isometric pages (or all of them) from the current "
                "model or PCF file. Edit IsoRotation / IsoCompression on the view first to "
                "change the layout",
            ),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        from iso import iso_page

        doc = FreeCAD.ActiveDocument
        views = iso_page.iso_views(FreeCADGui.Selection.getSelection()) or iso_page.iso_views(doc.Objects)
        doc.openTransaction(translate("Transaction", "Update isometric"))
        try:
            for view in views:
                iso_page.update(view)
        finally:
            doc.commitTransaction()


FreeCADGui.addCommand("Quetzal_CreateIso", CreateIso())
FreeCADGui.addCommand("Quetzal_IsoFromPCF", IsoFromPCF())
FreeCADGui.addCommand("Quetzal_UpdateIso", UpdateIso())
