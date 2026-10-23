# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the standards metadata and unit-aware catalogue rows."""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

from quetzal.domain.errors import StandardsError
from quetzal.domain.standards import StandardsCatalog, UnknownCatalogueFamily
from quetzal.domain.units import IN, MM, canonical_unit

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "standards" / "catalog.json"
TABLEZ = ROOT / "tablez"


@pytest.fixture(scope="module")
def catalog() -> StandardsCatalog:
    return StandardsCatalog.from_json(CATALOG_PATH)


def test_bundled_catalog_loads(catalog):
    assert len(catalog.institutions) >= 8
    assert len(catalog.standards) >= 20
    assert len(catalog.families) >= 15
    assert catalog.institution("ASME").name.startswith("American Society")
    assert catalog.standard("ASME B16.5").institution == "ASME"


def test_known_family_classification(catalog):
    pipe = catalog.series_for_file("Pipe_SCH-40.csv")
    assert pipe.standard == "ASME B36.10M"
    assert pipe.classification == "mapped"

    stainless = catalog.series_for_file("Pipe_SCH-10S.csv")
    assert stainless.standard == "ASME B36.19M"

    flange = catalog.series_for_file("Flange_ASME-WN-RF-150lb.csv")
    assert flange.standard == "ASME B16.5"
    assert flange.pressure_class == "150lb"
    assert flange.connection == "WN"
    assert flange.face == "RF"

    din = catalog.series_for_file("Flange_DIN-PN16.csv")
    assert din.standard == "DIN 2543"

    pn = catalog.series_for_file("Flange_PN16-WN.csv")
    assert pn.standard == "EN 1092-1"
    assert pn.connection == "WN"

    valve = catalog.series_for_file("Valve_Ball_150lbRF.csv")
    assert valve.standard == "ASME B16.34"

    section = catalog.series_for_file("Section_HEA.csv")
    assert section.standard == "EN 10365"

    gasket = catalog.series_for_file("Gasket_150lb.csv")
    assert gasket.standard == "ASME B16.20"

    generic = catalog.series_for_file("roughness.csv")
    assert generic.classification == "generic"
    assert generic.file == "roughness.csv"


def test_every_bundled_catalogue_is_classified(catalog):
    files = sorted(path.name for path in TABLEZ.glob("*.csv"))
    assert len(files) > 200
    assert catalog.validate_files(files) == []


def test_every_csv_column_has_a_dimension(catalog):
    unmapped = {}
    for path in sorted(TABLEZ.glob("*.csv")):
        family_name = path.stem.split("_")[0]
        family = catalog.family(family_name)
        if family.headerless_columns:
            headers = family.headerless_columns
        else:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                headers = next(csv.reader(handle, delimiter=";"))
        missing = [header for header in headers if header and family.dimension(header) is None]
        if missing:
            unmapped[path.name] = missing
    assert not unmapped, f"unmapped CSV columns: {unmapped}"


def test_dimension_units_and_normalisation(catalog):
    od = catalog.dimension("Pipe", "OD")
    assert od.unit is MM
    assert od.normalize("60.325") == pytest.approx(60.325)
    assert od.normalize("2.375", IN) == pytest.approx(60.325)

    angle = catalog.dimension("Elbow", "BendAngle")
    assert angle.unit.symbol == "°"

    mass = catalog.dimension("Flange", "kg")
    assert mass.unit.dimension == "mass"

    nominal = catalog.dimension("Pipe", "PSize")
    assert nominal.unit.dimension == "nominal"
    assert nominal.normalize("NPS 2") == "DN50"

    count = catalog.dimension("Flange", "n")
    assert count.unit.dimension == "dimensionless"

    normalized = catalog.normalize_row(
        "Pipe_SCH-STD.csv", {"PSize": "NPS 2", "OD": "2.375", "thk": "0.154"}
    )
    assert normalized["PSize"] == "DN50"
    assert normalized["OD"] == pytest.approx(2.375)  # CSV is declared in mm
    assert canonical_unit("length") is MM


def test_unknown_family_and_duplicate_validation(catalog):
    with pytest.raises(UnknownCatalogueFamily):
        catalog.series_for_file("Nope_123.csv")

    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    data["standards"].append(copy.deepcopy(data["standards"][0]))
    with pytest.raises(StandardsError):
        StandardsCatalog.from_dict(data)


def test_adding_a_standard_is_metadata_only(catalog):
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    data["institutions"].append({"code": "TEST", "name": "Test Institute", "region": "INT"})
    data["standards"].append(
        {
            "code": "TEST 1",
            "institution": "TEST",
            "title": "Test standard",
            "scope": "test",
        }
    )
    data["families"]["Test"] = {
        "prefix": "Test",
        "description": "Test family",
        "dimensions": ["PSize", "OD"],
        "rules": [{"match": "^T-", "standard": "TEST 1"}],
    }
    extended = StandardsCatalog.from_dict(data)
    series = extended.series_for_file("Test_T-100.csv")
    assert series.standard == "TEST 1"
    assert series.institution == "TEST"
    assert extended.dimension("Test", "OD").unit is MM
