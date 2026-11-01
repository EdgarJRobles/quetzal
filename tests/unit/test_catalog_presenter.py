# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the UI-facing catalogue presenter."""

from __future__ import annotations

from pathlib import Path

from quetzal.application.catalog_presenter import CatalogPresenter
from quetzal.application.standard_filters import StandardFilterService
from quetzal.domain.catalog import CsvCatalogRepository
from quetzal.domain.standards import StandardsCatalog

ROOT = Path(__file__).resolve().parents[2]


def presenter():
    catalog = CsvCatalogRepository(ROOT / "tablez")
    filters = StandardFilterService(
        catalog, StandardsCatalog.from_json(ROOT / "standards" / "catalog.json")
    )
    return CatalogPresenter(catalog, filters)


def test_rating_options_keep_institution_and_standard():
    options = presenter().ratings("Pipe")
    assert len(options) == 24
    schedule = next(option for option in options if option.code == "SCH-40")
    assert (schedule.institution, schedule.standard) == ("ASME", "ASME B36.10M")
    conduit = next(option for option in options if option.code == "ConduitEMT-LIGHT")
    assert conduit.standard == "QUETZAL-GENERIC"


def test_size_options_are_plain_data():
    sizes = presenter().sizes("Pipe", "SCH-40")
    dn50 = next(option for option in sizes if option.psize == "DN50")
    assert dn50.od is not None and dn50.od > 0
    assert dn50.thk is not None and dn50.thk > 0
    assert "DN50" in dn50.label
    assert dn50.row["PSize"] == "DN50"


def test_section_sizes_are_available_for_all_families():
    sizes = presenter().sizes("Section", "RH")
    assert sizes
    assert all(option.psize for option in sizes)
