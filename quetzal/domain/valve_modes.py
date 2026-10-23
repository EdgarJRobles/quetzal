# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pure Valve mode resolution (no FreeCAD imports).

Property registration and geometry selection are deliberately separated:

* properties depend only on ``Conn`` (``property_mode``);
* geometry depends on ``Conn`` + ``PRating`` (``geometry_mode``).

Keeping these predicates here makes every precedence rule unit-testable.
"""

from __future__ import annotations

from typing import Optional

FLANGE_CONNS = ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb")
SWING_CHECK_MARKERS = ("check_swing", "swing_check")
KNIFE_MARKERS = ("knife",)
PINCH_MARKERS = ("pinch",)

GENERIC = "generic"
FLANGED = "flanged"
SW_TH = "sw_th"
SWING_CHECK = "swing_check"
KNIFE_GATE = "knife_gate"
PINCH = "pinch"

PROPERTY_MODES = (GENERIC, FLANGED, SW_TH)
GEOMETRY_MODES = (GENERIC, FLANGED, SW_TH, SWING_CHECK, KNIFE_GATE, PINCH)


def is_flanged_conn(conn: Optional[str]) -> bool:
    return conn is not None and conn.strip() in FLANGE_CONNS


def property_mode(conn: Optional[str]) -> str:
    if is_flanged_conn(conn):
        return FLANGED
    if conn is not None:
        return SW_TH
    return GENERIC


def geometry_mode(conn: Optional[str], rating: str) -> str:
    text = (rating or "").lower()
    if is_flanged_conn(conn):
        if any(marker in text for marker in SWING_CHECK_MARKERS):
            return SWING_CHECK
        return FLANGED
    if conn is not None:
        return SW_TH
    if any(marker in text for marker in KNIFE_MARKERS):
        return KNIFE_GATE
    if any(marker in text for marker in PINCH_MARKERS):
        return PINCH
    return GENERIC
