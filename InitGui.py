# SPDX-License-Identifier: LGPL-3.0-or-later

import importlib
import os
import sys

import FreeCAD
import FreeCADGui
from FreeCADGui import ActiveDocument, Workbench

from quetzal.ui import layout as quetzal_layout


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

        self.utilsList = list(quetzal_layout.GROUPS["utils"])
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)
        Log("Loading Utils: done\n")

        import CFrame  # noqa: F401
        from cut_list.cut_list_commands import cutListCommand  # noqa: F401

        self.frameList = list(quetzal_layout.GROUPS["frame"])
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Frame tools"), self.frameList)
        Log("Loading Frame tools: done\n")

        import CPipe  # noqa: F401

        # Register Quetzal preference page (Edit > Preferences > Quetzal)
        try:
            import quetzal_units
            FreeCADGui.addPreferencePage(
                quetzal_units.QuetzalPreferencePage, "Quetzal")
        except Exception as e:
            FreeCAD.Console.PrintWarning(
                "Quetzal: could not register preference page: " + str(e) + "\n")

        self.pypeList = list(quetzal_layout.GROUPS["pipe"])
        import dodoPM  # noqa: F401  (pie menu side effects)

        import DraftTools
        import draftutils.init_tools as it

        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Draft snap"),
                           it.get_draft_snap_commands())
        self.qm = list(quetzal_layout.GROUPS["qm"])
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench", "Pipe tools"), self.pypeList)
        Log("Loading Pipe tools: done\n")

        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Frame tools"), self.frameList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Pipe tools"), self.pypeList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "Utils"), self.utilsList)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench", "QM Menus"), self.qm)
        quetzal_layout.validate_registry()

    def ContextMenu(self, recipient):
        QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
        for surface in quetzal_layout.CONTEXT_MENUS:
            self.appendContextMenu(
                QT_TRANSLATE_NOOP("Workbench", surface.label),
                list(quetzal_layout.GROUPS[surface.group]),
            )

    def setWatchers(self):
        class QuetzalWatcher:
            def __init__(self, commands, title, predicate):
                self.commands = list(commands)
                self.title = FreeCAD.Qt.QT_TRANSLATE_NOOP("Quetzal", title)
                self._predicate = predicate

            def shouldShow(self):
                try:
                    return bool(self._predicate())
                except Exception:
                    return False

        watchers = []
        for rule in quetzal_layout.WATCHERS:
            module_name, function_name = rule.predicate.split(":", 1)
            predicate = getattr(importlib.import_module(module_name), function_name)
            watchers.append(QuetzalWatcher(rule.commands, rule.title, predicate))

        self.NoObjects = list(quetzal_layout.WATCHERS[0].commands)
        self.WireObjects = list(quetzal_layout.WATCHERS[1].commands)
        self.TubeObjects = list(quetzal_layout.WATCHERS[2].commands)

        # Activated() is called on every workbench switch; clear the previous
        # watchers first so they do not accumulate.
        clear = getattr(FreeCADGui.Control, "clearTaskWatcher", None)
        if clear is not None:
            try:
                clear()
            except Exception:
                pass
        FreeCADGui.Control.addTaskWatcher(watchers)

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
        if hasattr(FreeCAD, "__activePypeLine__"):
            del FreeCAD.__activePypeLine__
            Msg("__activePypeLine__ variable deleted\n")
        if hasattr(FreeCAD, "__activeFrameLine__"):
            del FreeCAD.__activeFrameLine__
            Msg("__activeFrameLine__ variable deleted\n")
        # mw=FreeCADGui.getMainWindow()
        # mw.removeAction(FreeCAD.__dodoPMact__)
        # Msg("dodoPM shortcut removed\n")
        # del FreeCAD.__dodoPMact__
        # Msg("__dodoPMact__ variable deleted\n")
        # Msg("dodo deactivated()\n")


FreeCADGui.addWorkbench(QuetzalWorkbench)
