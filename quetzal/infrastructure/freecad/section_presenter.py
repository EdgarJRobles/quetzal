# SPDX-License-Identifier: LGPL-3.0-or-later
"""Default SectionCatalogPresenter backed by ArchProfile presets."""

from __future__ import annotations

from functools import lru_cache

from ...application.catalog_presenter import CatalogPresenter
from ...application.section_catalog import SectionCatalogPresenter
from ..catalog import default_catalog_repository
from ..standard_filters import default_standard_filter_service


@lru_cache(maxsize=1)
def default_section_presenter() -> SectionCatalogPresenter:
    def presets():
        import ArchProfile

        return ArchProfile.readPresets()

    catalog = default_catalog_repository()
    return SectionCatalogPresenter(
        CatalogPresenter(catalog, default_standard_filter_service()),
        presets,
    )
