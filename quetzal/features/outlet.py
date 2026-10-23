# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative property schema for the Outlet proxy."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..infrastructure.freecad.properties import PropertySpec, define_properties

OUTLET_PROPERTIES: Tuple[PropertySpec, ...] = (
    PropertySpec("App::PropertyLength", "OD", "Outlet", "Outside diameter at pipe end"),
    PropertySpec("App::PropertyLength", "thk", "Outlet", "Wall thickness at pipe end"),
    PropertySpec(
        "App::PropertyLength",
        "A",
        "Outlet",
        "Height above run-pipe surface (along fitting axis)",
    ),
    PropertySpec("App::PropertyLength", "B", "Outlet", "Outer diameter at base attachment"),
    PropertySpec(
        "App::PropertyLength",
        "E",
        "Outlet",
        "Socket depth  bore steps from ID to OD at this height (SocketWeld only)",
    ),
    PropertySpec(
        "App::PropertyLength",
        "CarrierOD",
        "Outlet",
        "Outer diameter of the carrier (run) pipe.  When non-zero the base of "
        "the fitting is shaped to lie flush against the carrier pipe surface "
        "rather than being cut flat.",
    ),
    PropertySpec(
        "App::PropertyString",
        "EndType",
        "Outlet",
        "ButtWeld (tapered body) or SocketWeld (cylindrical body)",
    ),
    PropertySpec(
        "App::PropertyInteger",
        "Angle",
        "Outlet",
        "Branch angle: 0 = straight, 45 = lateral",
    ),
    PropertySpec("App::PropertyString", "Profile", "Outlet", "Section dimensions"),
)


def define_outlet_properties(obj: Any, values: Mapping[str, Any]) -> None:
    define_properties(obj, OUTLET_PROPERTIES, values)
