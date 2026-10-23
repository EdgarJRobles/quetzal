# SPDX-License-Identifier: LGPL-3.0-or-later
"""Nominal pipe-size identities (DN / NPS).

ISO 6708 defines DN as a dimensionless designator; ASME B36.10M uses NPS.
The two systems are related by the table below but are *not* a unit
conversion, so they are modelled as a lookup rather than as a length unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional

from .errors import QuetzalError

DN_TO_NPS: Mapping[str, str] = MappingProxyType(
    {
        "DN6": "1/8",
        "DN8": "1/4",
        "DN10": "3/8",
        "DN15": "1/2",
        "DN20": "3/4",
        "DN25": "1",
        "DN32": "1-1/4",
        "DN40": "1-1/2",
        "DN50": "2",
        "DN65": "2-1/2",
        "DN80": "3",
        "DN90": "3-1/2",
        "DN100": "4",
        "DN125": "5",
        "DN150": "6",
        "DN200": "8",
        "DN250": "10",
        "DN300": "12",
        "DN350": "14",
        "DN400": "16",
        "DN450": "18",
        "DN500": "20",
        "DN550": "22",
        "DN600": "24",
        "DN650": "26",
        "DN700": "28",
        "DN750": "30",
        "DN800": "32",
        "DN850": "34",
        "DN900": "36",
        "DN1000": "40",
        "DN1050": "42",
        "DN1200": "48",
    }
)

NPS_TO_DN: Mapping[str, str] = MappingProxyType({nps: dn for dn, nps in DN_TO_NPS.items()})

DN_SYSTEM = "DN"
NPS_SYSTEM = "NPS"


@dataclass(frozen=True)
class NominalSize:
    """A nominal size identified by its DN label (the canonical key)."""

    dn: str
    nps: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "dn", self.dn.strip().upper())
        nps = self.nps or DN_TO_NPS.get(self.dn)
        if nps is not None:
            object.__setattr__(self, "nps", str(nps).strip())

    def display(self, system: str = DN_SYSTEM) -> str:
        if system.upper() == NPS_SYSTEM:
            return f"NPS {self.nps}" if self.nps else self.dn
        return self.dn

    def __str__(self) -> str:
        return self.dn


def normalize_system(system: "str | int") -> str:
    """Accept ``0/1`` or ``DN/NPS`` and return a canonical system name."""

    if isinstance(system, int):
        return NPS_SYSTEM if system == 1 else DN_SYSTEM
    value = str(system).strip().upper()
    if value in ("1", "NPS", "IN", "IMPERIAL"):
        return NPS_SYSTEM
    return DN_SYSTEM


def dn_to_nps(dn: str) -> Optional[str]:
    return DN_TO_NPS.get(str(dn).strip().upper())


def nps_to_dn(nps: str) -> Optional[str]:
    value = str(nps).strip().upper().replace("NPS", "").strip().strip('"')
    return NPS_TO_DN.get(value)


def parse(value: str) -> Optional[NominalSize]:
    """Parse ``DN50``, ``NPS 2``, ``2`` or ``2"`` into a :class:`NominalSize`."""

    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    if text.startswith("DN"):
        dn = text.replace(" ", "")
        if dn in DN_TO_NPS:
            return NominalSize(dn)
        return None
    if text.startswith("NPS"):
        return from_nps(text[3:].strip())
    return from_nps(text)


def from_dn(dn: str) -> NominalSize:
    key = str(dn).strip().upper()
    if key not in DN_TO_NPS:
        raise QuetzalError(f"Unknown DN nominal size: {dn!r}")
    return NominalSize(key)


def from_nps(nps: str) -> Optional[NominalSize]:
    dn = nps_to_dn(nps)
    return NominalSize(dn, str(nps).strip()) if dn else None


def display(value: str, system: "str | int" = DN_SYSTEM) -> str:
    size = parse(value)
    if size is None:
        return str(value)
    return size.display(normalize_system(system))


def canonical(value: str) -> str:
    """Return the canonical DN label for a known DN/NPS value (or the input)."""

    size = parse(value)
    return size.dn if size is not None else str(value)


def all_sizes() -> tuple[NominalSize, ...]:
    return tuple(NominalSize(dn, nps) for dn, nps in DN_TO_NPS.items())
