# SPDX-License-Identifier: LGPL-3.0-or-later

import FreeCAD

from quetzal.application.command_registry import CommandSpec
from quetzal.infrastructure.freecad.commands import register_spec

from . import cut_list_ui

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP


def create_cut_list():
    cut_list_ui.openCutListDialog()


register_spec(
    CommandSpec(
        name="Quetzal_CreateCutList",
        group="frame",
        handler=create_cut_list,
        menu_text=QT_TRANSLATE_NOOP("Quetzal_CreateCutList", "createCutList"),
        tooltip=QT_TRANSLATE_NOOP(
            "Quetzal_CreateCutList", "Create a new Cut List from Quetzal Beams"
        ),
        icon="Quetzal_CreateCutList",
    )
)
