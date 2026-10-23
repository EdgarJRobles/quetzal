# SPDX-License-Identifier: LGPL-3.0-or-later
"""Production standards repository rooted at ``<addon>/standards``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..domain.standards import JsonStandardsRepository, StandardsRepository


def standards_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "standards"


@lru_cache(maxsize=1)
def default_standards_repository() -> StandardsRepository:
    return JsonStandardsRepository(standards_dir() / "catalog.json")
