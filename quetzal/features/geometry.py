# SPDX-License-Identifier: LGPL-3.0-or-later
"""Geometry value objects returned by feature shape builders.

Splitting shape construction from property bookkeeping means a new variant of
a fitting only needs a new builder; it does not need to reimplement the
``execute`` lifecycle or port registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class FeatureGeometry:
    shape: Any
    ports: Tuple[Any, ...]
    directions: Tuple[Any, ...]
