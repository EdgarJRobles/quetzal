# SPDX-License-Identifier: LGPL-3.0-or-later
"""Reusable parameters and templates for a pipe line (PypeLine2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class PypeLineSpec:
    """The parameters shared by every pipe and bend in a line."""

    dn: str
    rating: str
    od: float
    thk: float
    bend_radius: float

    def __post_init__(self) -> None:
        if not str(self.dn).strip():
            raise ValueError("PypeLineSpec needs a nominal size")
        if not str(self.rating).strip():
            raise ValueError("PypeLineSpec needs a rating")
        for name in ("od", "thk", "bend_radius"):
            value = float(getattr(self, name))
            if value <= 0:
                raise ValueError(f"PypeLineSpec.{name} must be positive")

    @classmethod
    def from_line(cls, line: Any) -> "PypeLineSpec":
        return cls(
            dn=str(line.PSize),
            rating=str(line.PRating),
            od=float(line.OD),
            thk=float(line.thk),
            bend_radius=float(line.BendRadius),
        )

    def with_bend_radius(self, bend_radius: float) -> "PypeLineSpec":
        return PypeLineSpec(self.dn, self.rating, self.od, self.thk, float(bend_radius))


@dataclass(frozen=True)
class PypeLineTemplate:
    name: str
    rating: str
    bend_factor: float = 0.75
    description: str = ""

    def bend_radius_for(self, od: float) -> float:
        return float(od) * self.bend_factor


TEMPLATES: Tuple[PypeLineTemplate, ...] = (
    PypeLineTemplate(
        "Carbon steel (SCH-STD)",
        "SCH-STD",
        description="ASME B36.10M carbon steel line",
    ),
    PypeLineTemplate(
        "Stainless steel (SCH-10S)",
        "SCH-10S",
        description="ASME B36.19M stainless line",
    ),
    PypeLineTemplate(
        "Custom",
        "",
        description="Use the rating/size selected in the form",
    ),
)
