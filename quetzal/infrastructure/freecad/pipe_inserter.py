# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD adapter for PipeInsertRequest."""

from __future__ import annotations

from typing import Any

from ...application.insertion_requests import PipeInsertRequest
from .workbench_state import get_active_pype_line


class FreeCADPipeInserter:
    def insert_pipe(self, request: PipeInsertRequest) -> Any:
        import pCmd

        pypeline = request.pypeline if request.pypeline is not None else get_active_pype_line()
        created = pCmd.doPipes(
            request.rating,
            [request.psize, request.od, request.thk, request.height],
            pypeline,
        )
        if not created:
            raise RuntimeError("Pipe insertion did not create an object")
        return created[-1]
