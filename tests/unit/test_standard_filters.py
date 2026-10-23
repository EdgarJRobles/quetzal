# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for institution/standard rating filters."""

from __future__ import annotations

from pathlib import Path

from quetzal.application.standard_filters import (
    StandardFilterService,
    institution_label,
    standard_label,
)
from quetzal.domain.catalog import CsvCatalogRepository
from quetzal.domain.standards import StandardsCatalog

ROOT = Path(__file__).resolve().parents[2]


def service():
    return StandardFilterService(
        CsvCatalogRepository(ROOT / "tablez"),
        StandardsCatalog.from_json(ROOT / "standards" / "catalog.json"),
    )


def test_pipe_schedules_are_limited_to_asme_standards():
    filters = service()
    assert filters.institutions("Pipe") == ("ASME", "ASTM", "QUETZAL")
    assert set(filters.standards("Pipe")) == {
        "ASME B36.10M",
        "ASME B36.19M",
        "ASTM A615",
        "QUETZAL-GENERIC",
    }
    assert len(filters.ratings("Pipe")) == 24
    assert "ConduitEMT-LIGHT" in filters.ratings("Pipe")
    assert "REBARS" in filters.ratings("Pipe")
    carbon = filters.ratings("Pipe", "ASME", "ASME B36.10M", pattern=r"^SCH-")
    assert "SCH-40" in carbon
    assert "SCH-10S" not in carbon
    stainless = filters.ratings("Pipe", "ASME", "ASME B36.19M", pattern=r"^SCH-")
    assert stainless == ("SCH-10S", "SCH-40S", "SCH-5S", "SCH-80S")
    assert "REBARS" not in filters.ratings("Pipe", pattern=r"^SCH-")
    assert "ConduitPVC" not in filters.ratings("Pipe", pattern=r"^SCH-")


def test_section_series_are_limited_to_international_standards():
    filters = service()
    assert set(filters.institutions("Section")) == {"ASTM", "EN", "QUETZAL"}
    assert set(filters.standards("Section")) == {"ASTM A615", "EN 10365", "QUETZAL-GENERIC"}
    en = filters.ratings("Section", "EN", "EN 10365")
    assert en == ("HEA", "IPE", "UPN")
    astm = filters.ratings("Section", "ASTM", "ASTM A615")
    assert astm == ("REBARS",)
    assert "RH" in filters.ratings("Section")
    assert "TSLOT" in filters.ratings("Section")


def test_groups_preserve_institution_and_standard():
    groups = service().groups("Pipe", pattern=r"^SCH-")
    assert [(g.institution, g.standard) for g in groups] == [
        ("ASME", "ASME B36.10M"),
        ("ASME", "ASME B36.19M"),
    ]
    assert "SCH-40" in groups[0].ratings


def test_ui_labels_for_generic_catalogues():
    assert institution_label("ASME") == "ASME"
    assert institution_label("QUETZAL") == "Quetzal / generic"
    assert standard_label("ASME B36.10M") == "ASME B36.10M"
    assert standard_label("QUETZAL-GENERIC") == "Generic / vendor"
