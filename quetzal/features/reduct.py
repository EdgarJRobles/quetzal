# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative property schema for the Reduct proxy."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..infrastructure.freecad.properties import PropertySpec, define_properties

REDUCT_PROPERTIES: Tuple[PropertySpec, ...] = (
    PropertySpec("App::PropertyString", "PSize2", "Reduct", "Nominal diameter (minor end)"),
    PropertySpec("App::PropertyLength", "OD", "Reduct", "Major diameter"),
    PropertySpec("App::PropertyLength", "OD2", "Reduct", "Minor diameter"),
    PropertySpec("App::PropertyLength", "thk", "Reduct", "Wall thickness"),
    PropertySpec("App::PropertyLength", "thk2", "Reduct", "Wall thickness"),
    PropertySpec("App::PropertyBool", "calcH", "Reduct", "Make the length variable"),
    PropertySpec("App::PropertyLength", "Height", "Reduction", "Length of reduction"),
    PropertySpec("App::PropertyString", "Profile", "Reduct", "Section dim."),
    PropertySpec("App::PropertyBool", "conc", "Reduct", "Concentric or Eccentric"),
)


def define_reduct_properties(obj: Any, values: Mapping[str, Any]) -> None:
    define_properties(obj, REDUCT_PROPERTIES, values)
