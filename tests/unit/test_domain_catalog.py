# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the pure domain catalogue layer."""

from __future__ import annotations

import pytest

from quetzal.domain.catalog import (
    CatalogNotFoundError,
    CatalogTable,
    CsvCatalogRepository,
    InMemoryCatalogRepository,
)
from quetzal.domain.errors import QuetzalError


def write_csv(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)


@pytest.fixture()
def tablez(tmp_path):
    write_csv(
        tmp_path / "Pipe_SCH-40.csv",
        "PSize;OD;thk\nDN50;60.32;3.91\nDN100;114.3;6.02\n",
    )
    write_csv(
        tmp_path / "Pipe_SCH-STD.csv",
        "\ufeffPSize;OD;thk\nDN50;60.32;3.91\n",
        encoding="utf-8",
    )
    write_csv(tmp_path / "Elbow_SCH-40.csv", "PSize;OD;BendAngle\nDN50;60.32;90\n")
    write_csv(tmp_path / "Valve_Ball_150lbRF.csv", "DN;OD\nDN50;60.32\n")
    return tmp_path


def test_get_table_reads_semicolon_rows(tablez):
    repo = CsvCatalogRepository(tablez)
    table = repo.get_table("Pipe", "SCH-40")
    assert table.name == "Pipe_SCH-40.csv"
    assert len(table) == 2
    assert table[0]["OD"] == "60.32"
    assert table.columns == ("PSize", "OD", "thk")


def test_repository_caches_tables(tablez):
    repo = CsvCatalogRepository(tablez)
    assert repo.get_table("Pipe", "SCH-40") is repo.get_table("Pipe", "SCH-40")


def test_bom_is_stripped(tablez):
    repo = CsvCatalogRepository(tablez)
    table = repo.get_table("Pipe", "SCH-STD")
    assert table[0]["PSize"] == "DN50"


def test_missing_table_raises_domain_error(tablez):
    repo = CsvCatalogRepository(tablez)
    with pytest.raises(CatalogNotFoundError) as exc:
        repo.get_table("Pipe", "NOPE")
    assert exc.value.family == "Pipe"
    assert exc.value.rating == "NOPE"


def test_ratings_and_families(tablez):
    repo = CsvCatalogRepository(tablez)
    assert repo.ratings("Pipe") == ("SCH-40", "SCH-STD")
    assert set(repo.families()) == {"Pipe", "Elbow", "Valve"}


def test_path_traversal_is_rejected(tablez):
    repo = CsvCatalogRepository(tablez)
    with pytest.raises(QuetzalError):
        repo.read_file("../secret.csv")
    with pytest.raises(QuetzalError):
        repo.read_file("sub/dir.csv")
    with pytest.raises(QuetzalError):
        repo.read_file("Pipe_SCH-40.txt")


def test_table_find_and_first():
    table = CatalogTable.from_rows(
        "x.csv",
        [
            {"PSize": "DN50", "OD": "60.32"},
            {"PSize": "DN100", "OD": "114.3"},
        ],
    )
    assert table.first(PSize="DN50")["OD"] == "60.32"
    assert table.first(PSize=" DN100 ")["OD"] == "114.3"
    assert table.first(PSize="DN999") is None
    assert len(table.find(OD="60.32")) == 1


def test_in_memory_repository():
    repo = InMemoryCatalogRepository()
    repo.add("Pipe", "SCH-40", [{"PSize": "DN50", "OD": "60.32"}])
    assert repo.get_table("Pipe", "SCH-40")[0]["PSize"] == "DN50"
    assert repo.ratings("Pipe") == ("SCH-40",)
    assert repo.families() == ("Pipe",)
    with pytest.raises(CatalogNotFoundError):
        repo.get_table("Pipe", "NOPE")
