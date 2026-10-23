# SPDX-License-Identifier: LGPL-3.0-or-later
"""Nominal pipe size helpers.

The outside-diameter table used to be copy-pasted in ``pFeatures.py`` and
``pForms.py``.  Keeping a single immutable mapping here removes the risk of
the two copies drifting apart and gives callers one predictable API.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Optional

PIPE_OUTSIDE_DIAMETERS_MM: Mapping[str, float] = MappingProxyType(
    {
        "DN6": 10.29,
        "DN8": 13.72,
        "DN10": 17.14,
        "DN15": 21.34,
        "DN20": 26.67,
        "DN25": 33.4,
        "DN32": 42.16,
        "DN40": 48.26,
        "DN50": 60.32,
        "DN65": 73.02,
        "DN80": 88.9,
        "DN90": 101.6,
        "DN100": 114.3,
        "DN125": 141.3,
        "DN150": 168.27,
        "DN200": 219.07,
        "DN250": 273.05,
        "DN300": 323.85,
        "DN350": 355.6,
        "DN400": 406.4,
        "DN450": 457.2,
        "DN500": 508.0,
        "DN550": 558.8,
        "DN600": 609.6,
    }
)

_MISSING = object()


def normalize_size(size: str) -> str:
    """Normalise a nominal size label for lookups (``" dn50 "`` -> ``"DN50"``)."""

    return str(size).strip().upper()


def outside_diameter(size: str, default: object = _MISSING) -> Optional[float]:
    """Return the nominal outside diameter in millimetres for ``size``.

    Raises ``KeyError`` when the size is unknown unless a ``default`` is
    supplied, mirroring ``dict.get`` semantics but with an explicit opt-in.
    """

    key = normalize_size(size)
    value = PIPE_OUTSIDE_DIAMETERS_MM.get(key)
    if value is not None:
        return value
    if default is not _MISSING:
        return default  # type: ignore[return-value]
    raise KeyError(f"Unknown nominal pipe size: {size!r}")
