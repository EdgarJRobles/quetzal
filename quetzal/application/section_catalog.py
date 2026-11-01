# SPDX-License-Identifier: LGPL-3.0-or-later
"""Section/frame catalogue rows: local CSV plus optional BIM presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Tuple

from ..domain.catalog import CatalogNotFoundError
from .catalog_presenter import CatalogPresenter


@dataclass(frozen=True)
class SectionSize:
    label: str
    rating: str
    row: Any
    source: str  # "csv" | "bim"


class SectionCatalogPresenter:
    def __init__(
        self,
        catalog: CatalogPresenter,
        presets_provider: Optional[Callable[[], Sequence[Any]]] = None,
    ) -> None:
        self._catalog = catalog
        self._presets_provider = presets_provider

    def _presets(self) -> Sequence[Any]:
        if self._presets_provider is None:
            return ()
        return self._presets_provider()

    def ratings(self, include_bim: bool = True) -> Tuple[str, ...]:
        ratings = [option.code for option in self._catalog.ratings("Section")]
        if include_bim:
            for preset in self._presets():
                rating = str(preset[1])
                if rating not in ratings:
                    ratings.append(rating)
        return tuple(ratings)

    def sizes(self, rating: str, include_bim: bool = True) -> Tuple[SectionSize, ...]:
        result = []
        seen = set()
        try:
            csv_sizes = self._catalog.sizes("Section", rating)
        except CatalogNotFoundError:
            csv_sizes = ()
        for option in csv_sizes:
            label = str(option.row.get("SSize", option.label))
            if label in seen:
                continue
            seen.add(label)
            result.append(SectionSize(label, rating, dict(option.row), "csv"))
        if include_bim:
            for preset in self._presets():
                if str(preset[1]) != rating:
                    continue
                label = str(preset[2])
                if label in seen:
                    continue
                seen.add(label)
                result.append(SectionSize(label, rating, preset, "bim"))
        return tuple(result)
