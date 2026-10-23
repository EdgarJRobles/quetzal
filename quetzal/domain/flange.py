# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pure Flange rules: predicates, bolt phase, ports and insertion offsets.

The Part construction order remains in the feature builders, but every
non-geometric decision lives here so it can be tested without FreeCAD.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# Frozen legacy mapping: the WN/LJ fillet addresses edges by index.
LJ_FILLET_EDGE = {4: 19, 8: 31, 12: 43, 16: 55, 20: 67}

HUB_TYPES = ("SW", "WN", "LJ", "SO")


@dataclass(frozen=True)
class FlangeSpec:
    """Immutable view of the 17 dimensional Flange properties."""

    flange_type: str
    D: float
    d: float
    df: float
    f: float
    t: float
    n: int
    trf: float = 0.0
    drf: float = 0.0
    twn: float = 0.0
    dwn: float = 0.0
    ODp: float = 0.0
    R: float = 0.0
    T1: float = 0.0
    B2: float = 0.0
    Y: float = 0.0

    @property
    def has_hub(self) -> bool:
        return self.flange_type in HUB_TYPES and self.ODp > 0 and self.T1 > 0 and self.ODp > self.d

    @property
    def has_raised_face(self) -> bool:
        # The legacy condition intentionally omits drf > 0; preserving it
        # keeps old documents and the existing behaviour identical.
        return self.trf > 0 and self.drf < self.D

    @property
    def has_solid_raised_face(self) -> bool:
        return self.trf > 0 and self.drf > 0 and self.drf < self.D

    @property
    def has_socket(self) -> bool:
        return self.B2 > 0

    @property
    def has_weld_neck(self) -> bool:
        return self.dwn > 0 and self.twn > 0 and self.ODp > 0

    @property
    def bolt_hole_phase(self) -> float:
        return 360.0 / self.n / 2.0 if self.n > 0 else 0.0

    @property
    def lj_fillet_edge(self) -> Optional[int]:
        return LJ_FILLET_EDGE.get(self.n)

    def port_offsets(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        if self.flange_type == "WN":
            return ((0.0, 0.0, -self.trf), (0.0, 0.0, self.T1))
        if self.flange_type == "SW":
            return (
                (0.0, 0.0, -self.trf),
                (0.0, 0.0, self.T1 - self.Y - self.trf),
            )
        if self.flange_type == "BL":
            return ((0.0, 0.0, -self.trf), (0.0, 0.0, self.t))
        if self.flange_type == "SO":
            return ((0.0, 0.0, -self.trf), (0.0, 0.0, self.trf))
        return ((0.0, 0.0, 0.0), (0.0, 0.0, self.trf))

    def port_directions(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        return ((0.0, 0.0, -1.0), (0.0, 0.0, 1.0))

    @property
    def insertion_offset(self) -> float:
        """Z offset applied by ``pCmd.makeFlange`` when no trimming is used."""

        if self.flange_type == "WN":
            return -self.T1 + self.trf
        if self.flange_type == "SW":
            return -self.T1 + self.Y + self.trf
        if self.flange_type == "SO":
            return -self.trf
        return 0.0
