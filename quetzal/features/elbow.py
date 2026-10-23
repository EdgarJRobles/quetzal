# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative property schema for the Elbow proxy."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..infrastructure.freecad.properties import PropertySpec, define_properties

ELBOW_PROPERTIES: Tuple[PropertySpec, ...] = (
    PropertySpec("App::PropertyLength", "OD", "Elbow", "Outside diameter"),
    PropertySpec("App::PropertyLength", "thk", "Elbow", "Wall thickness"),
    PropertySpec("App::PropertyLength", "ID", "Elbow", "Inside diameter"),
    PropertySpec("App::PropertyAngle", "BendAngle", "Elbow", "Bend Angle"),
    PropertySpec("App::PropertyLength", "BendRadius", "Elbow", "Bend Radius"),
    PropertySpec("App::PropertyString", "Profile", "Elbow", "Section dim."),
)


def define_elbow_properties(obj: Any, values: Mapping[str, Any]) -> None:
    define_properties(obj, ELBOW_PROPERTIES, values)
