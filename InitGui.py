# ****************************************************************************
# *                                                                          *
# *   Dodo Workbench:                                                        *
# *       substitute of flamingo for Py3 / Qt5                               *
# *   Copyright (c) 2019 Riccardo Treu LGPL                                  *
# *                                                                          *
# *   This program is free software; you can redistribute it and/or modify   *
# *   it under the terms of the GNU Lesser General Public License (LGPL)     *
# *   as published by the Free Software Foundation; either version 2 of      *
# *   the License, or (at your option) any later version.                    *
# *   for detail see the LICENCE text file.                                  *
# *                                                                          *
# *   This program is distributed in the hope that it will be useful,        *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of         *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
# *   GNU Library General Public License for more details.                   *
# *                                                                          *
# *   You should have received a copy of the GNU Library General Public      *
# *   License along with this program; if not, write to the Free Software    *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307   *
# *   USA                                                                    *
# *                                                                          *
# ****************************************************************************

import os
import sys

import FreeCAD
import FreeCADGui
from FreeCADGui import Workbench


Log = FreeCAD.Console.PrintLog
Msg = FreeCAD.Console.PrintMessage


class QuetzalWorkbench(Workbench):
    def __init__(self):
        from quetzal_config import TRANSLATIONSPATH, ICONPATH

        # Add translations path
        FreeCADGui.addLanguagePath(TRANSLATIONSPATH)
        FreeCADGui.updateLocale()

        self.__class__.MenuText = FreeCAD.Qt.translate("Workbench", "Quetzal")
        self.__class__.ToolTip = FreeCAD.Qt.translate(
            "Workbench",
            "Quetzal is the fork of Dodo workbench for FreeCAD. "
            "Extending Dodo workbench support and adding translation support. ",
        )
        self.__class__.Icon = os.path.join(ICONPATH, "dodo.svg")

    try:
        import DraftSnap
    except Exception:
        import draftguitools.gui_snapper as DraftSnap

    if not hasattr(FreeCADGui, "Snapper"):
        FreeCADGui.Snapper = DraftSnap.Snapper()

    v = sys.version_info[0]
    if v < 3:
        FreeCAD.Console.PrintWarning(
            "Quetzal is written for Py3 and Qt5\n You may experience mis-behaviuors\n"
        )

    def Initialize(self):
        """
        This function is called at the first activation of the workbench,
        here is the place to import all the commands.
        """
        QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
        import CUtils

        self.utilsList = [
            "Quetzal_SelectSolids",
            "Quetzal_QueryModel",
            "Quetzal_MoveWorkPlane",
            "Quetzal_OffsetWorkPlane",
            "Quetzal_RotateWorkPlane",
            "Quetzal_HackedL",
            "Quetzal_MoveHandle",
            "Quetzal_DpCalc",
        ]
        self.appendToolbar("Utils", self.utilsList)
        Log("Loading Utils: done\n")
        import CFrame
        from cut_list.cut_list_commands import cutListCommand

        self.frameList = [
            "Quetzal_FrameIt",
            "Quetzal_FrameBranchManager",
            "Quetzal_InsertSection",
            "Quetzal_SpinSect",
            "Quetzal_ReverseBeam",
            "Quetzal_ShiftBeam",
            "Quetzal_PivotBeam",
            "Quetzal_LevelBeam",
            "Quetzal_AlignEdge",
            "Quetzal_RotJoin",
            "Quetzal_AlignFlange",
            "Quetzal_StretchBeam",
            "Quetzal_Extend",
            "Quetzal_AdjustFrameAngle",
            "Quetzal_InsertPath",
            "Quetzal_CreateCutList",
        ]
        self.appendToolbar("frameTools", self.frameList)
        Log("Loading Frame tools: done\n")
        import CPipe

        self.pypeList = [
            "Quetzal_InsertPipe",
            "Quetzal_InsertElbow",
            "Quetzal_InsertReduct",
            "Quetzal_InsertCap",
            "Quetzal_InsertValve",
            "Quetzal_InsertFlange",
            "Quetzal_InsertUbolt",
            "Quetzal_InsertPypeLine",
            "Quetzal_InsertBranch",
            "Quetzal_InsertTank",
            "Quetzal_InsertRoute",
            "Quetzal_BreakPipe",
            "Quetzal_MateEdges",
            "Quetzal_Flat",
            "Quetzal_Extend2intersection",
            "Quetzal_Extend1intersection",
            "Quetzal_MakeHeader",
            "Quetzal_Laydown",
            "Quetzal_Raiseup",
            "Quetzal_Attach2tube",
            "Quetzal_Point2point",
            "Quetzal_InsertAnyz",
        ]  # ,"joinPype"]
        from dodoPM import toolList

        self.qm = toolList  # ["pipeQM","elbowQM","reductQM"]
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "pypetools"), self.pypeList)
        Log("Loading Pipe tools: done\n")
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Frame tools"), self.frameList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Pype tools"), self.pypeList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "QM Menus"), self.qm)

    def ContextMenu(self, recipient):
        QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
        self.appendContextMenu(QT_TRANSLATE_NOOP("Workbench", "Frames"), self.frameList)
        self.appendContextMenu(QT_TRANSLATE_NOOP("Workbench", "Pypes"), self.pypeList)
        self.appendContextMenu(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)

    def Activated(self):
        # if hasattr(FreeCADGui,"draftToolBar"):	#patch
        # FreeCADGui.draftToolBar.Activated()		#patch
        # if hasattr(FreeCADGui,"Snapper"):			#patch
        # FreeCADGui.Snapper.show()				#patchm
        FreeCAD.__activePypeLine__ = None
        FreeCAD.__activeFrameLine__ = None
        Msg("Created variables in FreeCAD module:\n")
        Msg("__activePypeLine__\n")
        Msg("__activeFrameLine__\n")
        try:
            Msg("__dodoPMact__ \n")
            FreeCAD.Console.PrintMessage(
                FreeCAD.__dodoPMact__.objectName()
                + " 's shortcut = "
                + FreeCAD.__dodoPMact__.shortcuts()[0].toString()
                + "\n\t****\n"
            )
        except:
            FreeCAD.Console.PrintError("dodoPM not loaded \n")

    def Deactivated(self):
        del FreeCAD.__activePypeLine__
        Msg("__activePypeLine__ variable deleted\n")
        del FreeCAD.__activeFrameLine__
        Msg("__activeFrameLine__ variable deleted\n")
        # mw=FreeCADGui.getMainWindow()
        # mw.removeAction(FreeCAD.__dodoPMact__)
        # Msg("dodoPM shortcut removed\n")
        # del FreeCAD.__dodoPMact__
        # Msg("__dodoPMact__ variable deleted\n")
        # Msg("dodo deactivated()\n")


FreeCADGui.addWorkbench(QuetzalWorkbench)
