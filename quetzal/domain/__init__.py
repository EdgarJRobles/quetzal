# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pure domain layer: no FreeCAD, no Qt, no filesystem side effects."""

from .catalog import (
    CatalogNotFoundError,
    CatalogRepository,
    CatalogTable,
    CsvCatalogRepository,
    InMemoryCatalogRepository,
)
from .errors import QuetzalError
from .pipe_sizes import (
    PIPE_OUTSIDE_DIAMETERS_MM,
    normalize_size,
    outside_diameter,
)
from .ports import Port, Vec3, nearest_port_index

__all__ = [
    "CatalogNotFoundError",
    "CatalogRepository",
    "CatalogTable",
    "CsvCatalogRepository",
    "InMemoryCatalogRepository",
    "PIPE_OUTSIDE_DIAMETERS_MM",
    "Port",
    "QuetzalError",
    "Vec3",
    "nearest_port_index",
    "normalize_size",
    "outside_diameter",
]
