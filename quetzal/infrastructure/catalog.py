# SPDX-License-Identifier: LGPL-3.0-or-later
"""Production catalogue repository rooted at ``<addon>/tablez``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..domain.catalog import CatalogRepository, CsvCatalogRepository


def tablez_dir() -> Path:
    """Absolute path to the bundled ``tablez`` directory."""

    return Path(__file__).resolve().parent.parent.parent / "tablez"


@lru_cache(maxsize=1)
def default_catalog_repository() -> CatalogRepository:
    """Return the process-wide CSV repository.

    The repository caches parsed tables, so a single instance avoids re-reading
    the same CSV every time a dialog is repainted.
    """

    return CsvCatalogRepository(tablez_dir())
