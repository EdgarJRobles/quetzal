# SPDX-License-Identifier: LGPL-3.0-or-later
"""UI-facing catalogue rows, independent from Qt and FreeCAD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from ..domain.catalog import CatalogRepository
from .standard_filters import StandardFilterService


@dataclass(frozen=True)
class RatingOption:
    code: str
    institution: str
    standard: str


@dataclass(frozen=True)
class SizeOption:
    psize: str
    od: Optional[float]
    thk: Optional[float]
    row: Mapping[str, Any]

    @property
    def label(self) -> str:
        parts = [self.psize]
        if self.od is not None:
            parts.append(f"{self.od:g}")
        if self.thk is not None:
            parts.append(f"x{self.thk:g}")
        return " ".join(parts)


class CatalogPresenter:
    def __init__(
        self,
        catalog: CatalogRepository,
        filters: StandardFilterService,
    ) -> None:
        self._catalog = catalog
        self._filters = filters

    def ratings(
        self,
        family: str,
        institution: Optional[str] = None,
        standard: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> Tuple[RatingOption, ...]:
        result = []
        for inst, std, rating in self._filters.mappings(
            family, institution=institution, standard=standard, pattern=pattern
        ):
            result.append(RatingOption(rating, inst, std))
        return tuple(result)

    def sizes(self, family: str, rating: str) -> Tuple[SizeOption, ...]:
        table = self._catalog.get_table(family, rating)
        size_key = next((key for key in ("PSize", "SSize") if key in table.columns), "PSize")
        result = []
        for row in table:
            od = _number(row.get("OD"))
            thk = _number(row.get("thk"))
            result.append(SizeOption(str(row.get(size_key, "")), od, thk, row))
        return tuple(result)


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
