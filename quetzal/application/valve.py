# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD-free Valve build context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ValveContext:
    feature: Any
    height: float
    conn: Optional[str]
    rating: str

    @classmethod
    def from_feature(cls, fp: Any) -> "ValveContext":
        return cls(
            feature=fp,
            height=float(fp.Height),
            conn=getattr(fp, "Conn", None),
            rating=(getattr(fp, "PRating", "") or "").lower(),
        )
