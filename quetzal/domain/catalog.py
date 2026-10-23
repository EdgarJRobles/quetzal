# SPDX-License-Identifier: LGPL-3.0-or-later
"""Catalogue access without importing FreeCAD or any UI toolkit.

Historically every module opened CSV files in ``tablez/`` with its own
``csv.DictReader`` call.  That duplicated path handling, encoding rules and
caching, and made the data source impossible to replace in tests.

This module introduces a single repository abstraction:

* :class:`CatalogTable` is an immutable table of string rows.
* :class:`CatalogRepository` is the protocol consumers depend on.
* :class:`CsvCatalogRepository` is the production adapter.
* :class:`InMemoryCatalogRepository` is a lightweight fake for tests.

Consumers can now depend on the protocol (Dependency Inversion Principle)
instead of reaching into the filesystem themselves.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Dict, Iterator, List, Mapping, Optional, Protocol, Sequence, Tuple

from .errors import CatalogNotFoundError, QuetzalError

Row = Mapping[str, str]

_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class CatalogTable:
    """Immutable collection of CSV rows.

    ``rows`` keep the original column order and values as strings, exactly as
    ``csv.DictReader`` returns them.  This keeps the behaviour of the legacy
    ``readTable()`` helper unchanged while adding validated lookups.
    """

    name: str
    columns: Tuple[str, ...]
    rows: Tuple[Row, ...]

    @classmethod
    def from_rows(cls, name: str, rows: Sequence[Mapping[str, str]]) -> "CatalogTable":
        materialized: List[Row] = []
        columns: List[str] = []
        for row in rows:
            clean = MappingProxyType(dict(row))
            materialized.append(clean)
            for key in clean:
                if key not in columns:
                    columns.append(key)
        return cls(name=name, columns=tuple(columns), rows=tuple(materialized))

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[Row]:
        return iter(self.rows)

    def __getitem__(self, index: int) -> Row:
        return self.rows[index]

    def find(self, **criteria: str) -> Tuple[Row, ...]:
        """Return every row whose fields equal the given values.

        Values are compared after stripping surrounding whitespace so the
        result does not depend on incidental spaces in the source CSV.
        """

        matches = []
        for row in self.rows:
            if all(
                row.get(key, "").strip() == str(value).strip() for key, value in criteria.items()
            ):
                matches.append(row)
        return tuple(matches)

    def first(self, **criteria: str) -> Optional[Row]:
        matches = self.find(**criteria)
        return matches[0] if matches else None

    def to_dicts(self) -> List[Dict[str, str]]:
        """Return mutable copies of the rows (legacy compatibility helper)."""

        return [dict(row) for row in self.rows]


class CatalogRepository(Protocol):
    """Port used by the application/UI layer to read catalogue data."""

    def get_table(self, family: str, rating: str) -> CatalogTable:
        """Return the table for ``<family>_<rating>.csv``."""

    def read_file(self, filename: str) -> CatalogTable:
        """Return an arbitrary catalogue file inside the configured directory."""

    def ratings(self, family: str) -> Tuple[str, ...]:
        """Return every rating available for ``family``."""

    def families(self) -> Tuple[str, ...]:
        """Return every catalogue family available."""


class CsvCatalogRepository:
    """Read semicolon-separated catalogue files from a directory.

    The repository caches parsed tables in memory because the CSVs are read
    on every dialog repaint; the cache is scoped to the instance so tests can
    build isolated repositories.
    """

    def __init__(
        self,
        base_dir: "str | Path",
        delimiter: str = ";",
        encoding: str = "utf-8-sig",
    ) -> None:
        self._base_dir = Path(base_dir)
        self._delimiter = delimiter
        self._encoding = encoding
        self._cache: Dict[str, CatalogTable] = {}

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def _resolve(self, filename: str) -> Path:
        if not filename or filename in (".", ".."):
            raise QuetzalError(f"Invalid catalogue filename: {filename!r}")
        if "/" in filename or "\\" in filename:
            raise QuetzalError(f"Catalogue filenames must not contain paths: {filename!r}")
        if not _SAFE_FILENAME.match(filename):
            raise QuetzalError(f"Unsafe catalogue filename: {filename!r}")
        if not filename.lower().endswith(".csv"):
            raise QuetzalError(f"Catalogue file must end with .csv: {filename!r}")
        return self._base_dir / filename

    def read_file(
        self,
        filename: str,
        fieldnames: Optional[Sequence[str]] = None,
    ) -> CatalogTable:
        cached = self._cache.get(filename)
        if cached is not None and fieldnames is None:
            return cached

        path = self._resolve(filename)
        if not path.is_file():
            family, _, rating = filename.partition("_")
            if rating.endswith(".csv"):
                rating = rating[: -len(".csv")]
            raise CatalogNotFoundError(family, rating, str(path))

        with path.open("r", encoding=self._encoding, newline="") as handle:
            if fieldnames is None:
                reader = csv.DictReader(handle, delimiter=self._delimiter)
            else:
                reader = csv.DictReader(
                    handle, fieldnames=list(fieldnames), delimiter=self._delimiter
                )
            table = CatalogTable.from_rows(filename, list(reader))

        if fieldnames is None:
            self._cache[filename] = table
        return table

    def get_table(self, family: str, rating: str) -> CatalogTable:
        return self.read_file(f"{family}_{rating}.csv")

    def _filenames(self) -> Tuple[str, ...]:
        if not self._base_dir.is_dir():
            return ()
        return tuple(sorted(entry.name for entry in self._base_dir.iterdir() if entry.is_file()))

    def ratings(self, family: str) -> Tuple[str, ...]:
        prefix = f"{family}_"
        suffix = ".csv"
        result = []
        for filename in self._filenames():
            if filename.startswith(prefix) and filename.endswith(suffix):
                result.append(filename[len(prefix) : -len(suffix)])
        return tuple(result)

    def families(self) -> Tuple[str, ...]:
        families = {
            filename.split("_", 1)[0]
            for filename in self._filenames()
            if filename.endswith(".csv") and "_" in filename
        }
        return tuple(sorted(families))


class InMemoryCatalogRepository:
    """Test double for :class:`CatalogRepository`."""

    def __init__(
        self, tables: Optional[Mapping[Tuple[str, str], Sequence[Mapping[str, str]]]] = None
    ):
        self._tables: Dict[Tuple[str, str], CatalogTable] = {}
        for (family, rating), rows in (tables or {}).items():
            self._tables[(family, rating)] = CatalogTable.from_rows(f"{family}_{rating}.csv", rows)

    def add(self, family: str, rating: str, rows: Sequence[Mapping[str, str]]) -> None:
        self._tables[(family, rating)] = CatalogTable.from_rows(f"{family}_{rating}.csv", rows)

    def get_table(self, family: str, rating: str) -> CatalogTable:
        try:
            return self._tables[(family, rating)]
        except KeyError:
            raise CatalogNotFoundError(family, rating, "<memory>") from None

    def read_file(self, filename: str) -> CatalogTable:
        for (family, rating), table in self._tables.items():
            if f"{family}_{rating}.csv" == filename:
                return table
        raise CatalogNotFoundError(filename, "", "<memory>")

    def ratings(self, family: str) -> Tuple[str, ...]:
        return tuple(sorted(rating for fam, rating in self._tables if fam == family))

    def families(self) -> Tuple[str, ...]:
        return tuple(sorted({family for family, _ in self._tables}))
