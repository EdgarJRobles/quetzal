# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the section/BIM presenter."""

from __future__ import annotations

from pathlib import Path

from quetzal.application.catalog_presenter import CatalogPresenter
from quetzal.application.section_catalog import SectionCatalogPresenter
from quetzal.application.standard_filters import StandardFilterService
from quetzal.domain.catalog import CsvCatalogRepository
from quetzal.domain.standards import StandardsCatalog

ROOT = Path(__file__).resolve().parents[2]
PRESETS = [
    [0, "HEA", "HEA200", "H", 190, 200, 6.5, 10],
    [1, "SHS", "SHS100x100x5", "R", 5, 100, 100, 5],
]


def presenter():
    catalog = CsvCatalogRepository(ROOT / "tablez")
    filtering = StandardFilterService(
        catalog, StandardsCatalog.from_json(ROOT / "standards" / "catalog.json")
    )
    return SectionCatalogPresenter(CatalogPresenter(catalog, filtering), lambda: PRESETS)


def test_ratings_include_csv_and_bim():
    ratings = presenter().ratings(include_bim=True)
    assert "HEA" in ratings and "RH" in ratings and "SHS" in ratings
    assert "SHS" not in presenter().ratings(include_bim=False)


def test_sizes_merge_csv_and_bim_without_duplicates():
    sizes = presenter().sizes("HEA", include_bim=True)
    labels = [size.label for size in sizes]
    assert labels.count("HEA200") == 1
    assert all(size.source == "csv" for size in sizes)
    shs = presenter().sizes("SHS", include_bim=True)
    assert shs and shs[0].source == "bim"


def test_sizes_can_be_csv_only():
    sizes = presenter().sizes("HEA", include_bim=False)
    assert sizes
    assert all(size.source == "csv" for size in sizes)
