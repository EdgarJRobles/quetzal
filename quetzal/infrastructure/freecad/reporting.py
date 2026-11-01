# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD console implementation of the user reporter port."""

from __future__ import annotations

import FreeCAD


class FreeCADReporter:
    def info(self, message: str) -> None:
        FreeCAD.Console.PrintMessage(str(message) + "\n")

    def warning(self, message: str) -> None:
        FreeCAD.Console.PrintWarning(str(message) + "\n")

    def error(self, message: str) -> None:
        FreeCAD.Console.PrintError(str(message) + "\n")
