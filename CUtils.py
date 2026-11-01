# SPDX-License-Identifier: LGPL-3.0-or-later

__license__ = "LGPL 3"

import FreeCAD
import FreeCADGui

from quetzal.application.command_registry import CommandSpec
from quetzal.infrastructure.freecad.commands import register_spec

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP


def query_model():
    import uForms

    uForms.QueryForm(FreeCADGui.Selection)


def move_work_plane():
    import uCmd

    uCmd.setWP()


def rotate_work_plane():
    import uForms

    uForms.rotWPForm()


def offset_work_plane():
    if not (hasattr(FreeCAD, "DraftWorkingPlane") and hasattr(FreeCADGui, "Snapper")):
        return
    import uCmd

    size = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft").GetInt("gridSize")
    scale = [float(value * size) for value in (1, 1, 0.2)]
    arrow = uCmd.arrow(FreeCAD.DraftWorkingPlane.getPlacement(), scale=scale, offset=size)
    from PySide.QtGui import QInputDialog

    translate = FreeCAD.Qt.translate
    value, accepted = QInputDialog.getInt(
        None,
        translate("Quetzal_OffsetWorkPlane", "Offset Work Plane"),
        translate("Quetzal_OffsetWorkPlane", "Offset: "),
    )
    if accepted and value > 0:
        uCmd.offsetWP(value)
    arrow.closeArrow()


def hacked_line():
    import uCmd

    uCmd.hackedLine()


def move_handle():
    import uCmd

    FreeCADGui.Control.showDialog(uCmd.handleDialog())


def pressure_loss_calculator():
    import uForms

    FreeCADGui.Control.showDialog(uForms.dpCalcDialog())


def select_solids():
    from fCmd import getSolids

    getSolids(not bool(FreeCADGui.Selection.getSelection()))


COMMANDS = (
    CommandSpec(
        name="Quetzal_QueryModel",
        group="utils",
        handler=query_model,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_QueryModel", "Query the model"),
        tooltip=QT_TRANSLATE_NOOP("Quetzal_QueryModel", "Click objects to print infos"),
        icon="Quetzal_QueryModel",
        accel="Q,M",
    ),
    CommandSpec(
        name="Quetzal_MoveWorkPlane",
        group="utils",
        handler=move_work_plane,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_MoveWorkPlane", "Align workplane"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_MoveWorkPlane",
            "Moves and rotates the drafting workplane with points, edges and faces",
        ),
        icon="Quetzal_MoveWorkPlane",
        accel="A,W",
    ),
    CommandSpec(
        name="Quetzal_RotateWorkPlane",
        group="utils",
        handler=rotate_work_plane,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_RotateWorkPlane", "Rotate workplane"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_RotateWorkPlane", "Spin the Draft working plane about one of its axes"
        ),
        icon="Quetzal_RotateWorkPlane",
        accel="R,W",
    ),
    CommandSpec(
        name="Quetzal_OffsetWorkPlane",
        group="utils",
        handler=offset_work_plane,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_OffsetWorkPlane", "Offset workplane"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_OffsetWorkPlane", "Shifts the WP along its normal."
        ),
        icon="Quetzal_OffsetWorkPlane",
        accel="O,W",
    ),
    CommandSpec(
        name="Quetzal_HackedLine",
        group="utils",
        handler=hacked_line,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_HackedLine", "Draw a Draft wire"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_HackedLine",
            "WP is re-positioned at each point. Possible to spin and offset it.",
        ),
        icon="Quetzal_HackedLine",
        accel="H,L",
    ),
    CommandSpec(
        name="Quetzal_MoveHandle",
        group="utils",
        handler=move_handle,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_MoveHandle", "Move objects"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_MoveHandle", "Move quickly objects inside viewport"
        ),
        icon="Quetzal_MoveHandle",
        accel="M,H",
    ),
    CommandSpec(
        name="Quetzal_PressureLossCalculator",
        group="utils",
        handler=pressure_loss_calculator,
        menu_text=QT_TRANSLATE_NOOP(
            "Quetzal_PressureLossCalculator", "Pressure loss calculator"
        ),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_PressureLossCalculator",
            "Calculate pressure loss in 'pypes' using ChEDL libraries.\n"
            "See __doc__ of the module for further information.",
        ),
        icon="Quetzal_PressureLossCalculator",
    ),
    CommandSpec(
        name="Quetzal_SelectSolids",
        group="utils",
        handler=select_solids,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_SelectSolids", "Select solids"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_SelectSolids",
            "Grab all solids or those partially selected\n to export in .step format",
        ),
        icon="Quetzal_SelectSolids",
    ),
)

for _spec in COMMANDS:
    register_spec(_spec)
