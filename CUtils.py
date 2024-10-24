# (c) 2019 R. T. LGPL: part of dodo w.b. for FreeCAD

__license__ = "LGPL 3"

# import FreeCAD modules
import FreeCAD
import FreeCADGui
import inspect
import os

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP

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


# ---------------------------------------------------------------------------
# The command classes
# ---------------------------------------------------------------------------


class queryModel:
    def Activated(self):
        import FreeCAD, FreeCADGui, uForms

        form = uForms.QueryForm(FreeCADGui.Selection)

    def GetResources(self):
        return {
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "query.svg"
            ),
            "Accel": "Q,M",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_QueryModel", "query the model"),
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
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "grid.svg"
            ),
            "Accel": "A,W",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_MoveWorkPlane", "align Workplane"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_MoveWorkPlane",
                "Moves and rotates the drafting workplane with points, edges and faces",
            ),
        }


class rotateWorkPlane:
    def Activated(self):
        import FreeCAD, FreeCADGui, uForms

        form = uForms.rotWPForm()

    def GetResources(self):
        return {
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "rotWP.svg"
            ),
            "Accel": "R,W",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_RotateWorkPlane", "rotate Workplane"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_RotateWorkPlane", "Spin the Draft working plane about one of its axes"
            ),
        }


class offsetWorkPlane:
    def Activated(self):
        if hasattr(FreeCAD, "DraftWorkingPlane") and hasattr(FreeCADGui, "Snapper"):
            import uCmd

            s = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft").GetInt(
                "gridSize"
            )
            sc = [float(x * s) for x in [1, 1, 0.2]]
            arrow = uCmd.arrow(
                FreeCAD.DraftWorkingPlane.getPlacement(), scale=sc, offset=s
            )
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
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "offsetWP.svg"
            ),
            "Accel": "O,W",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_OffsetWorkPlane", "offset Workplane"),
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
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "hackedL.svg"
            ),
            "Accel": "H,L",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_HackedL", "draw a DWire"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_HackedL",
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
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "moveHandle.svg"
            ),
            "Accel": "M,H",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_MoveHandle", "Move objects"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_MoveHandle", "Move quickly objects inside viewport"),
        }


class dpCalc:
    def Activated(self):
        import uForms

        FreeCADGui.Control.showDialog(uForms.dpCalcDialog())

    def GetResources(self):
        return {
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "delta.svg"
            ),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_DpCalc", "Pressure loss calculator"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_DpCalc",
                'Calculate pressure loss in "pypes" using ChEDL libraries.\n See __doc__ of the module for further information.',
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
            "Pixmap": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "iconz", "solids.svg"
            ),
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
addCommand("Quetzal_HackedL", hackedL())
addCommand("Quetzal_MoveHandle", moveHandle())
addCommand("Quetzal_DpCalc", dpCalc())
addCommand("Quetzal_SelectSolids", selectSolids())
