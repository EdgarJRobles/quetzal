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
        self.__class__.Icon = os.path.join(ICONPATH, "quetzal.svg")
        FreeCADGui.addIconPath(ICONPATH)

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
        import CUtils  # noqa: F401

        self.utilsList = [
            "Quetzal_SelectSolids",
            "Quetzal_QueryModel",
            "Quetzal_MoveWorkPlane",
            "Quetzal_OffsetWorkPlane",
            "Quetzal_RotateWorkPlane",
            "Quetzal_HackedLine",
            "Quetzal_MoveHandle",
            "Quetzal_PressureLossCalculator",
        ]
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)
        Log("Loading Utils: done\n")

        import CFrame  # noqa: F401
        from cut_list.cut_list_commands import cutListCommand  # noqa: F401

        self.frameList = [
            "Quetzal_FrameIt",
            "Quetzal_FrameBranchManager",
            "Quetzal_InsertSection",
            "Quetzal_SpinSection",
            "Quetzal_ReverseBeam",
            "Quetzal_ShiftBeam",
            "Quetzal_PivotBeam",
            "Quetzal_LevelBeam",
            "Quetzal_AlignEdge",
            "Quetzal_RotateJoin",
            "Quetzal_AlignFlange",
            "Quetzal_StretchBeam",
            "Quetzal_ExtendBeam",
            "Quetzal_AdjustFrameAngle",
            "Quetzal_InsertPath",
            "Quetzal_CreateCutList",
        ]
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Frame tools"), self.frameList)
        Log("Loading Frame tools: done\n")

        import CPipe  # noqa: F401

        self.pypeList = [
            "Quetzal_InsertPipe",
            "Quetzal_InsertElbow",
            "Quetzal_InsertTerminalAdapter",
            "Quetzal_InsertReduct",
            "Quetzal_InsertCap",
            "Quetzal_InsertValve",
            "Quetzal_InsertFlange",
            "Quetzal_InsertUBolt",
            "Quetzal_InsertPypeLine",
            "Quetzal_InsertBranch",
            "Quetzal_InsertTank",
            "Quetzal_InsertRoute",
            "Quetzal_BreakPipe",
            "Quetzal_MateEdges",
            "Quetzal_Flat",
            "Quetzal_ExtendIntersection2",
            "Quetzal_ExtendIntersection1",
            "Quetzal_MakeHeader",
            "Quetzal_Laydown",
            "Quetzal_Raiseup",
            "Quetzal_Attach2Tube",
            "Quetzal_Point2Point",
            "Quetzal_InsertAnyShape",
        ]
        from dodoPM import toolList

        import DraftTools
        import draftutils.init_tools as it

        it.init_toolbar(self,
                        QT_TRANSLATE_NOOP("Workbench", "Draft snap"),
                        it.get_draft_snap_commands())
        self.qm = toolList  # ["pipeQM","elbowQM","reductQM"]
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Pipe tools"), self.pypeList)
        Log("Loading Pipe tools: done\n")

        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Frame tools"), self.frameList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Pipe tools"), self.pypeList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "QM Menus"), self.qm)

    def ContextMenu(self, recipient):
        QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
        self.appendContextMenu(QT_TRANSLATE_NOOP("Workbench", "Frames"), self.frameList)
        self.appendContextMenu(QT_TRANSLATE_NOOP("Workbench", "Pipes"), self.pypeList)
        self.appendContextMenu(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)

    def setWatchers(self):
        class QuetzalCreateWatcher:
            def __init__(self):
                QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
                self.commands = ["Quetzal_InsertPypeLine",
                                 "Quetzal_Point2Point",
                                 "Quetzal_InsertFlange",
                                 "Quetzal_FrameBranchManager",
                                 "Quetzal_FrameIt"
                                 ]
                self.title = QT_TRANSLATE_NOOP("Quetzal","Create objects")
            def shouldShow(self):
                return (FreeCAD.ActiveDocument is not None)
        FreeCADGui.Control.addTaskWatcher([QuetzalCreateWatcher()])

    def Activated(self):
        # if hasattr(FreeCADGui, "draftToolBar"):  # patch
        #     FreeCADGui.draftToolBar.Activated()  # patch
        # if hasattr(FreeCADGui, "Snapper"):  # patch
        #     FreeCADGui.Snapper.show()  # patchm
        self.setWatchers()
        FreeCAD.__activePypeLine__ = None
        FreeCAD.__activeFrameLine__ = None
        Msg("Created variables in FreeCAD module:\n")
        Msg("__activePypeLine__\n")
        Msg("__activeFrameLine__\n")
        try:
            Msg("__dodoPMact__ \n")
            Msg(
                f"{FreeCAD.__dodoPMact__.objectName()} 's shortcut = "
                f"{FreeCAD.__dodoPMact__.shortcuts()[0].toString()}\n\t****\n"
            )
        except Exception as e:
            FreeCAD.Console.PrintError(f"dodoPM not loaded:\n{e}\n")

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
