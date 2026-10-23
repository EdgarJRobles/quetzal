# SPDX-License-Identifier: LGPL-3.0-or-later
"""Default standards filter used by the dialogs."""

from __future__ import annotations

from functools import lru_cache

from ..application.standard_filters import StandardFilterService
from .catalog import default_catalog_repository
from .standards import default_standards_repository


@lru_cache(maxsize=1)
def default_standard_filter_service() -> StandardFilterService:
    return StandardFilterService(default_catalog_repository(), default_standards_repository())
