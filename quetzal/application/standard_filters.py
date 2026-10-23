# SPDX-License-Identifier: LGPL-3.0-or-later
"""Filter catalogue ratings by institution and international standard.

The dialog forms should not list every CSV blindly: a pipe form should show
the schedules of ASME B36.10M/B36.19M, and a frame form should show the section
series of EN 10365/ASTM A6/ASTM A615, not vendor/generic rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..domain.catalog import CatalogRepository
from ..domain.standards import StandardsCatalog, StandardsRepository


@dataclass(frozen=True)
class StandardGroup:
    institution: str
    standard: str
    ratings: Tuple[str, ...]


class StandardFilterService:
    def __init__(
        self,
        catalog: CatalogRepository,
        standards: "StandardsRepository | StandardsCatalog",
    ) -> None:
        self._catalog = catalog
        self._standards = standards

    def _catalog_data(self) -> StandardsCatalog:
        loader = getattr(self._standards, "load", None)
        return loader() if loader is not None else self._standards

    def mappings(
        self,
        family: str,
        institution: Optional[str] = None,
        standard: Optional[str] = None,
        pattern: Optional[str] = None,
        include_generic: bool = True,
    ) -> Tuple[Tuple[str, str, str], ...]:
        """Return ``(institution, standard, rating)`` for catalogue series."""

        catalog = self._catalog_data()
        regex = re.compile(pattern) if pattern else None
        result = []
        for rating in self._catalog.ratings(family):
            if regex is not None and regex.search(rating) is None:
                continue
            series = catalog.series(family, rating)
            if series.classification != "mapped" and not include_generic:
                continue
            if institution and series.institution != institution:
                continue
            if standard and series.standard != standard:
                continue
            result.append((series.institution, series.standard, rating))
        return tuple(result)

    def institutions(
        self,
        family: str,
        pattern: Optional[str] = None,
        include_generic: bool = True,
    ) -> Tuple[str, ...]:
        values = list(
            dict.fromkeys(
                item[0]
                for item in self.mappings(family, pattern=pattern, include_generic=include_generic)
            )
        )
        return tuple(sorted(values, key=lambda code: (code == "QUETZAL", code)))

    def standards(
        self,
        family: str,
        institution: Optional[str] = None,
        pattern: Optional[str] = None,
        include_generic: bool = True,
    ) -> Tuple[str, ...]:
        values = list(
            dict.fromkeys(
                item[1]
                for item in self.mappings(
                    family,
                    institution=institution,
                    pattern=pattern,
                    include_generic=include_generic,
                )
            )
        )
        return tuple(sorted(values, key=lambda code: (code == "QUETZAL-GENERIC", code)))

    def ratings(
        self,
        family: str,
        institution: Optional[str] = None,
        standard: Optional[str] = None,
        pattern: Optional[str] = None,
        include_generic: bool = True,
    ) -> Tuple[str, ...]:
        return tuple(
            item[2]
            for item in self.mappings(
                family,
                institution=institution,
                standard=standard,
                pattern=pattern,
                include_generic=include_generic,
            )
        )

    def groups(
        self,
        family: str,
        institution: Optional[str] = None,
        pattern: Optional[str] = None,
        include_generic: bool = True,
    ) -> Tuple[StandardGroup, ...]:
        grouped: Dict[Tuple[str, str], list] = {}
        for inst, std, rating in self.mappings(family, institution=institution, pattern=pattern):
            grouped.setdefault((inst, std), []).append(rating)
        return tuple(
            StandardGroup(inst, std, tuple(ratings)) for (inst, std), ratings in grouped.items()
        )
