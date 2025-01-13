# (c) 2019 R. T. LGPL: part of dodo w.b. for FreeCAD

__title__ = "pypeTools toolbar"
__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"

# import FreeCAD modules
import FreeCAD
import FreeCADGui

from quetzal_config import addCommand, get_icon_path

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate


def updatesPL(dialogqm):
    if FreeCAD.activeDocument():
        pypelines = [
            o.Label
            for o in FreeCAD.activeDocument().Objects
            if hasattr(o, "PType") and o.PType == "PypeLine"
        ]
    else:
        pypelines = []
    if pypelines:  # updates pypelines in combo
        dialogqm.QM.comboPL.clear()
        dialogqm.QM.comboPL.addItems(pypelines)


# ---------------------------------------------------------------------------
# The command classes
# ---------------------------------------------------------------------------


class insertPipe:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipForm = pForms.insertPipeForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("pipe"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertPipe", "Insert a tube"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertPipe", "Insert a tube"),
        }


class insertElbow:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        elbForm = pForms.insertElbowForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("elbow"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertElbow", "Insert a curve"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertElbow", "Insert a curve"),
        }


class insertReduct:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipeFormObj = pForms.insertReductForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("reduct"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertReduct", "Insert a reduction"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertReduct", "Insert a reduction"),
        }


class insertCap:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipeFormObj = pForms.insertCapForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("cap"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertCap", "Insert a cap"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertCap", "Insert a cap"),
        }


class insertFlange:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipeFormObj = pForms.insertFlangeForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("flange"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertFlange", "Insert a flange"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertFlange", "Insert a flange"),
        }


class insertUbolt:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipeFormObj = pForms.insertUboltForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("clamp"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertUbolt", "Insert a U-bolt"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertUbolt", "Insert a U-bolt"),
        }


class insertPypeLine:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipeFormObj = pForms.insertPypeLineForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("pypeline"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertPypeLine", "PypeLine Manager"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertPypeLine", "Open PypeLine Manager"),
        }


class insertBranch:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        # pCmd.makeBranch()
        pipeFormObj = pForms.insertBranchForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("branch"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertBranch", "Insert a branch"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertBranch", "Insert a PypeBranch"),
        }


class breakPipe:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        pipeFormObj = pForms.breakForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("break"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_BreakPipe", "Break the pipe"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_BreakPipe", "Break one pipe at point and insert gap"
            ),
        }


class mateEdges:
    def Activated(self):
        import pCmd

        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Mate"))
        pCmd.alignTheTube()
        FreeCAD.activeDocument().commitTransaction()
        FreeCAD.activeDocument().recompute()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("mate"),
            "Accel": "M,E",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_MateEdges", "Mate pipes edges"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_MateEdges", "Mate two terminations through their edges"
            ),
        }


class flat:
    def Activated(self):
        import pCmd

        pCmd.flatten()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("flat"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_Flat", "Fit one elbow"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_Flat", "Place the elbow between two pipes or beams"
            ),
        }


class extend2intersection:
    def Activated(self):
        import pCmd

        FreeCAD.activeDocument().openTransaction(
            translate("Transaction", "Extend pipes to intersection")
        )
        pCmd.extendTheTubes2intersection()
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("intersect"),
            "MenuText": QT_TRANSLATE_NOOP(
                "Quetzal_Extend2intersection", "Extends pipes to intersection"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_Extend2intersection", "Extends pipes to intersection"
            ),
        }


class extend1intersection:
    def Activated(self):
        import pCmd

        FreeCAD.activeDocument().openTransaction(
            translate("Transaction", "Extend pipe to intersection")
        )
        pCmd.extendTheTubes2intersection(both=False)
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("intersect1"),
            "MenuText": QT_TRANSLATE_NOOP(
                "Quetzal_Extend1intersection", "Extends pipe to intersection"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_Extend1intersection", "Extends pipe to intersection"
            ),
        }


class laydown:
    def Activated(self):
        import pCmd
        import fCmd
        from Part import Plane

        refFace = [f for f in fCmd.faces() if isinstance(f.Surface, Plane)][0]
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Lay-down the pipe"))
        for b in fCmd.beams():
            if pCmd.isPipe(b):
                pCmd.laydownTheTube(b, refFace)
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("laydown"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_Laydown", "Lay-down the pipe"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_Laydown", "Lay-down the pipe on the support plane"
            ),
        }


class raiseup:
    def Activated(self):
        import pCmd
        import fCmd
        from Part import Plane

        selex = FreeCADGui.Selection.getSelectionEx()
        for sx in selex:
            sxFaces = [f for f in fCmd.faces([sx]) if isinstance(f.Surface, Plane)]
            if len(sxFaces) > 0:
                refFace = sxFaces[0]
                support = sx.Object
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Raise-up the support"))
        for b in fCmd.beams():
            if pCmd.isPipe(b):
                pCmd.laydownTheTube(b, refFace, support)
                break
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("raiseup"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_Raiseup", "Raise-up the support"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_Raiseup", "Raise the support to the pipe"),
        }


class joinPype:
    """ """

    def Activated(self):
        import FreeCADGui
        import pForms  # pObservers

        # s=pObservers.joinObserver()
        FreeCADGui.Control.showDialog(pForms.joinForm())  # .Selection.addObserver(s)

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("join"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_JoinPype", "Join pypes"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_JoinPype", "Select the part-pype and the port"),
        }


class insertValve:
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def Activated(self):
        import pForms

        # pipeFormObj=pForms.insertValveForm()
        # FreeCADGui.Control.showDialog(pForms.insertValveForm())
        pipeFormObj = pForms.insertValveForm()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("valve"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertValve", "Insert a valve"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertValve", "Insert a valve"),
        }


class attach2tube:
    def Activated(self):
        import pCmd

        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Attach to tube"))
        pCmd.attachToTube()
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("attach"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_Attach2tube", "Attach  to tube"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_Attach2tube", "Attach one pype to the nearest port of selected pipe"
            ),
        }


class point2point:
    def Activated(self):
        import pForms

        form = pForms.point2pointPipe()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("point2point"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_Point2point", "draw a tube point-to-point"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_Point2point", "Click on subsequent points."),
        }


class insertAnyz:
    """
    Dialog to insert any object saved as .STEP, .IGES or .BREP in folder ../Mod/dodo/shapez or subfolders.
    """

    def Activated(self):
        import anyShapez

        FreeCADGui.Control.showDialog(anyShapez.shapezDialog())

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("insertAnyZhape"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertAnyz", "Insert any shape"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertAnyz", "Insert a STEP, IGES or BREP"),
        }


class insertTank:
    def Activated(self):
        import FreeCADGui
        import pForms

        FreeCADGui.Control.showDialog(pForms.insertTankForm())

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("tank"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertTank", "Insert a tank"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertTank", "Create tank and nozzles"),
        }


class insertRoute:
    def Activated(self):
        import FreeCADGui
        import pForms

        FreeCADGui.Control.showDialog(pForms.insertRouteForm())

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("route"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertRoute", "Insert a pipe route"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_InsertRoute", "Create a sketch attached to a circular edge"
            ),
        }


class makeHeader:
    def Activated(self):
        import pCmd

        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Connect to header"))
        pCmd.header()
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("header"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_MakeHeader", "Connect to header"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "Quetzal_MakeHeader",
                "Connect branches to one header pipe\nBranches and header's axes must be ortho",
            ),
        }


# ---------------------------------------------------------------------------
# Adds the commands to the FreeCAD command manager
# ---------------------------------------------------------------------------
addCommand("Quetzal_InsertPipe", insertPipe())
addCommand("Quetzal_InsertElbow", insertElbow())
addCommand("Quetzal_InsertReduct", insertReduct())
addCommand("Quetzal_InsertCap", insertCap())
addCommand("Quetzal_InsertValve", insertValve())
addCommand("Quetzal_InsertFlange", insertFlange())
addCommand("Quetzal_InsertUbolt", insertUbolt())
addCommand("Quetzal_InsertPypeLine", insertPypeLine())
addCommand("Quetzal_InsertBranch", insertBranch())
addCommand("Quetzal_InsertTank", insertTank())
addCommand("Quetzal_InsertRoute", insertRoute())
addCommand("Quetzal_BreakPipe", breakPipe())
addCommand("Quetzal_MateEdges", mateEdges())
addCommand("Quetzal_JoinPype", joinPype())
addCommand("Quetzal_Attach2tube", attach2tube())
addCommand("Quetzal_Flat", flat())
addCommand("Quetzal_Extend2intersection", extend2intersection())
addCommand("Quetzal_Extend1intersection", extend1intersection())
addCommand("Quetzal_Laydown", laydown())
addCommand("Quetzal_Raiseup", raiseup())
addCommand("Quetzal_Point2point", point2point())
addCommand("Quetzal_InsertAnyz", insertAnyz())
addCommand("Quetzal_MakeHeader", makeHeader())


### QkMenus ###
class pipeQM:
    def Activated(self):
        import dodoPM

        # dodoPM.pqm.updatePL()
        dodoPM.pqm.show()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("pipe"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_PipeQM", "QM for pipes"),
        }


addCommand("Quetzal_PipeQM", pipeQM())


class elbowQM:
    def Activated(self):
        import dodoPM

        dodoPM.eqm.show()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("elbow"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_ElbowQM", "QM for elbows"),
        }


addCommand("Quetzal_ElbowQM", elbowQM())


class flangeQM:
    def Activated(self):
        import dodoPM

        dodoPM.fqm.show()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("flange"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_FlangeQM", "QM for flanges"),
        }


addCommand("Quetzal_FlangeQM", flangeQM())


class valveQM:
    def Activated(self):
        import dodoPM

        dodoPM.vqm.show()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("valve"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_ValveQM", "QM for valves"),
        }


addCommand("Quetzal_ValveQM", valveQM())


class capQM:
    def Activated(self):
        import dodoPM

        dodoPM.cqm.show()

    def GetResources(self):
        return {
            "Pixmap": get_icon_path("cap"),
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_CapQM", "QM for caps"),
        }


addCommand("Quetzal_CapQM", capQM())
