# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative property schema for the Tee proxy."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..infrastructure.freecad.properties import PropertySpec, define_properties

TEE_PROPERTIES: Tuple[PropertySpec, ...] = (
    PropertySpec("App::PropertyString", "PSizeBranch", "Tee", "Nominal diameter of branch end"),
    PropertySpec("App::PropertyLength", "OD", "Tee", "Run diameter"),
    PropertySpec("App::PropertyLength", "OD2", "Tee", "Branch diameter"),
    PropertySpec("App::PropertyLength", "thk", "Tee", "Run Wall thickness"),
    PropertySpec("App::PropertyLength", "thk2", "Tee", "Branch Wall thickness"),
    PropertySpec("App::PropertyLength", "C", "Tee", "Run half length"),
    PropertySpec("App::PropertyLength", "M", "Tee", "Branch length"),
    PropertySpec("App::PropertyLength", "offset", "Tee", "Straight tee offset length"),
    PropertySpec("App::PropertyString", "Profile", "Tee", "Run and Branch Size"),
)


def define_tee_properties(obj: Any, values: Mapping[str, Any]) -> None:
    define_properties(obj, TEE_PROPERTIES, values)
