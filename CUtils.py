# (c) 2019 R. T. LGPL: part of dodo w.b. for FreeCAD

__license__ = "LGPL 3"

# import FreeCAD modules

import FreeCAD
import FreeCADGui

from quetzal_config import addCommand

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP


# ---------------------------------------------------------------------------
# The command classes
# ---------------------------------------------------------------------------


class queryModel:
    def Activated(self):
        import uForms

        form = uForms.QueryForm(FreeCADGui.Selection)

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_QueryModel",
            "Accel": "Q,M",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_QueryModel", "Query the model"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_QueryModel", "Click objects to print infos"),
        }


class moveWorkPlane:
    """
    Tool to set the DraftWorkingPlane according existing geometry of
    the model.
    The normal of plane is set:
    * 1st according the selected face,
    * then according the plane defined by a curved edge,
    * at last according the plane defined by two straight edges.
    The origin is set:
    * 1st according the selected vertex,
    * then according the center of curvature of a curved edge,
    * at last according the intersection of two straight edges.
    """

    def Activated(self):
        import uCmd

        uCmd.setWP()

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_MoveWorkPlane",
            "Accel": "A,W",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_MoveWorkPlane", "Align workplane"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_MoveWorkPlane",
                "Moves and rotates the drafting workplane with points, edges and faces",
            ),
        }


class rotateWorkPlane:
    def Activated(self):
        import uForms

        form = uForms.rotWPForm()

    def GetResources(self):
        return {
            "Accel": "R,W",
            "Pixmap": "Quetzal_RotateWorkPlane",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_RotateWorkPlane", "Rotate workplane"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_RotateWorkPlane", "Spin the Draft working plane about one of its axes"
            ),
        }


class offsetWorkPlane:
    def Activated(self):
        if hasattr(FreeCAD, "DraftWorkingPlane") and hasattr(FreeCADGui, "Snapper"):
            import uCmd

            s = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft").GetInt("gridSize")
            sc = [float(x * s) for x in [1, 1, 0.2]]
            arrow = uCmd.arrow(FreeCAD.DraftWorkingPlane.getPlacement(), scale=sc, offset=s)
            from PySide.QtGui import QInputDialog as qid

            translate = FreeCAD.Qt.translate

            offset = qid.getInt(
                None,
                translate("Quetzal_OffsetWorkPlane", "Offset Work Plane"),
                translate("Quetzal_OffsetWorkPlane", "Offset: "),
            )
            if offset[1] > 0:
                uCmd.offsetWP(offset[0])
            # FreeCADGui.ActiveDocument.ActiveView.getSceneGraph().removeChild(arrow.node)
            arrow.closeArrow()

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_OffsetWorkPlane",
            "Accel": "O,W",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_OffsetWorkPlane", "Offset workplane"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_OffsetWorkPlane", "Shifts the WP along its normal."
            ),
        }


class hackedL:
    def Activated(self):
        import uCmd

        form = uCmd.hackedLine()

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_HackedLine",
            "Accel": "H,L",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_HackedLine", "Draw a Draft wire"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_HackedLine",
                "WP is re-positioned at each point. Possible to spin and offset it.",
            ),
        }


class moveHandle:
    def Activated(self):
        import uCmd

        FreeCADGui.Control.showDialog(uCmd.handleDialog())
        # form = uCmd.handleDialog()

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_MoveHandle",
            "Accel": "M,H",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_MoveHandle", "Move objects"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_MoveHandle", "Move quickly objects inside viewport"
            ),
        }


class dpCalc:
    def Activated(self):
        import uForms

        FreeCADGui.Control.showDialog(uForms.dpCalcDialog())

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_PressureLossCalculator",
            "MenuText": QT_TRANSLATE_NOOP(
                "Quetzal_PressureLossCalculator", "Pressure loss calculator"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_PressureLossCalculator",
                "Calculate pressure loss in 'pypes' using ChEDL libraries.\n"
                "See __doc__ of the module for further information.",
            ),
        }


class selectSolids:
    def Activated(self):
        from fCmd import getSolids

        if FreeCADGui.Selection.getSelection():
            allDoc = False
        else:
            allDoc = True
        getSolids(allDoc)

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_SelectSolids",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_SelectSolids", "Select solids"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_SelectSolids",
                "Grab all solids or those partially selected\n to export in .step format",
            ),
        }


# ---------------------------------------------------------------------------
# Adds the commands to the FreeCAD command manager
# ---------------------------------------------------------------------------
addCommand("Quetzal_QueryModel", queryModel())
addCommand("Quetzal_MoveWorkPlane", moveWorkPlane())
addCommand("Quetzal_RotateWorkPlane", rotateWorkPlane())
addCommand("Quetzal_OffsetWorkPlane", offsetWorkPlane())
addCommand("Quetzal_HackedLine", hackedL())
addCommand("Quetzal_MoveHandle", moveHandle())
addCommand("Quetzal_PressureLossCalculator", dpCalc())
addCommand("Quetzal_SelectSolids", selectSolids())
