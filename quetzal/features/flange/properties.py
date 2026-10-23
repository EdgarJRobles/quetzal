# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative Flange property schema (order and groups are a contract)."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ...infrastructure.freecad.properties import PropertySpec, define_properties

FLANGE_PROPERTIES: Tuple[PropertySpec, ...] = (
    PropertySpec("App::PropertyString", "FClass", "Flange", "Flange pressure class"),
    PropertySpec("App::PropertyString", "FlangeType", "Flange", "Type of flange"),
    PropertySpec("App::PropertyLength", "D", "Flange", "Flange diameter"),
    PropertySpec("App::PropertyLength", "d", "Flange", "Bore diameter"),
    PropertySpec("App::PropertyLength", "df", "Flange", "Bolts distance"),
    PropertySpec("App::PropertyLength", "f", "Flange", "Bolts hole diameter"),
    PropertySpec("App::PropertyLength", "t", "Flange", "Thickness of flange"),
    PropertySpec("App::PropertyInteger", "n", "Flange", "Nr. of bolts"),
    PropertySpec("App::PropertyLength", "trf", "Flange2", "Thickness of raised face"),
    PropertySpec("App::PropertyLength", "drf", "Flange2", "Diameter of raised face"),
    PropertySpec("App::PropertyLength", "twn", "Flange2", "Length of welding neck"),
    PropertySpec("App::PropertyLength", "dwn", "Flange2", "Diameter of welding neck"),
    PropertySpec("App::PropertyLength", "ODp", "Flange2", "Outside diameter of pipe"),
    PropertySpec("App::PropertyLength", "R", "Flange", "Flange fillet radius"),
    PropertySpec("App::PropertyLength", "T1", "Flange", "Flange neck length"),
    PropertySpec("App::PropertyLength", "B2", "Flange Socket welding", "Socket diameter"),
    PropertySpec("App::PropertyLength", "Y", "Flange Socket welding", "Socket depth"),
)


def define_flange_properties(obj: Any, values: Mapping[str, Any]) -> None:
    define_properties(obj, FLANGE_PROPERTIES, values)
