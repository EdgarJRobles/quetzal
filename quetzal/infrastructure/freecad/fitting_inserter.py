# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD adapter for FittingInsertRequest."""

from __future__ import annotations

from typing import Any

from ...application.insertion_requests import FittingInsertRequest
from .workbench_state import get_active_pype_line


class FreeCADFittingInserter:
    def insert(self, request: FittingInsertRequest) -> Any:
        import pCmd

        pypeline = request.pypeline or get_active_pype_line()
        options = dict(request.options)
        kind = request.kind

        if kind == "socket_elbow":
            created = pCmd.doSocketElbow(request.rating, list(request.props), pypeline, **options)
        elif kind == "elbow":
            created = pCmd.doElbow(request.rating, list(request.props), pypeline, **options)
        elif kind == "socket_tee":
            created = pCmd.doSocketTee(
                request.rating,
                list(request.props),
                pypeline,
                options.pop("insert_on_branch"),
                **options,
            )
        elif kind == "tee":
            created = pCmd.doTees(
                request.rating,
                list(request.props),
                pypeline,
                options.pop("insert_on_branch"),
                **options,
            )
        elif kind == "flange":
            created = pCmd.doFlanges(
                request.rating,
                list(request.props),
                pypeline=pypeline,
                **options,
            )
        elif kind == "socket_cap":
            created = pCmd.doSocketCap(list(request.props), pypeline)
        elif kind == "cap":
            created = pCmd.doCaps(request.rating, list(request.props), pypeline)
        elif kind == "valve":
            created = pCmd.doValves(
                list(request.props),
                pypeline,
                options.pop("pos", 0),
                flgPropList=options.pop("flgPropList", None),
                actuator=options.pop("actuator", "Handle"),
            )
        elif kind == "gasket":
            created = pCmd.doGaskets(list(request.props), pypeline=pypeline)
        elif kind == "bolts":
            created = pCmd.doBolts_Nuts(list(request.props), pypeline=pypeline)
        else:
            raise ValueError(f"Unsupported fitting kind: {kind!r}")

        if not created:
            raise RuntimeError(f"{kind} insertion did not create an object")
        return created[-1]
