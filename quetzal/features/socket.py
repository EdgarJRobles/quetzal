# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative property schemas for the socket-weld/threaded fittings."""

from __future__ import annotations

from typing import Any, Mapping

from ..infrastructure.freecad.properties import PropertySpec, define_properties

SOCKET_SPECS = {
    "SocketEll": (
        PropertySpec("App::PropertyLength", "OD", "SocketEll", "Pipe OD"),
        PropertySpec("App::PropertyAngle", "BendAngle", "SocketEll", "Bend Angle"),
        PropertySpec("App::PropertyLength", "A", "SocketEll", "Center to outer edge"),
        PropertySpec("App::PropertyLength", "C", "SocketEll", "Wall thickness in socket"),
        PropertySpec("App::PropertyLength", "D", "SocketEll", "Bore internal diameter"),
        PropertySpec("App::PropertyLength", "E", "SocketEll", "Center to base of socket"),
        PropertySpec("App::PropertyLength", "G", "SocketEll", "Inner body wall thickness"),
        PropertySpec(
            "App::PropertyString",
            "Conn",
            "SocketEll",
            "Connection type (SW=Socket Weld, TH=Threaded)",
        ),
    ),
    "SocketTee": (
        PropertySpec(
            "App::PropertyString", "PSizeBranch", "SocketTee", "Nominal diameter of branch"
        ),
        PropertySpec("App::PropertyLength", "OD", "SocketTee", "Run pipe OD"),
        PropertySpec("App::PropertyLength", "OD2", "SocketTee", "Branch pipe OD"),
        PropertySpec("App::PropertyLength", "A", "SocketTee", "Centre to outer face of socket"),
        PropertySpec("App::PropertyLength", "C", "SocketTee", "Socket boss wall thickness"),
        PropertySpec("App::PropertyLength", "D", "SocketTee", "Bore internal diameter"),
        PropertySpec("App::PropertyLength", "E", "SocketTee", "Centre to base of socket"),
        PropertySpec("App::PropertyLength", "G", "SocketTee", "Inner body wall thickness"),
        PropertySpec(
            "App::PropertyString",
            "Conn",
            "SocketTee",
            "Connection type (SW=Socket Weld, TH=Threaded)",
        ),
    ),
    "SocketCap": (
        PropertySpec("App::PropertyLength", "OD", "SocketCap", "Pipe OD"),
        PropertySpec("App::PropertyLength", "A", "SocketCap", "Cap height"),
        PropertySpec("App::PropertyLength", "C", "SocketCap", "Wall thickness in socket"),
        PropertySpec("App::PropertyLength", "E", "SocketCap", "Socket depth"),
        PropertySpec(
            "App::PropertyString",
            "Conn",
            "SocketCap",
            "Connection type (SW=Socket Weld, TH=Threaded)",
        ),
    ),
    "SocketCoupling": (
        PropertySpec(
            "App::PropertyString", "PSize2", "SocketCoupling", "Nominal diameter of port 1"
        ),
        PropertySpec("App::PropertyLength", "OD", "SocketCoupling", "Port 0 pipe OD"),
        PropertySpec("App::PropertyLength", "OD2", "SocketCoupling", "Port 1 pipe OD"),
        PropertySpec(
            "App::PropertyLength", "A", "SocketCoupling", "Half-length (center to outer edge)"
        ),
        PropertySpec("App::PropertyLength", "C", "SocketCoupling", "Socket boss wall thickness"),
        PropertySpec("App::PropertyLength", "D", "SocketCoupling", "Bore diameter at centre"),
        PropertySpec("App::PropertyLength", "E", "SocketCoupling", "Socket depth"),
        PropertySpec(
            "App::PropertyString",
            "Conn",
            "SocketCoupling",
            "Connection type (SW=Socket Weld, TH=Threaded)",
        ),
    ),
    "SocketUnion": (
        PropertySpec("App::PropertyLength", "OD", "SocketUnion", "Pipe OD"),
        PropertySpec(
            "App::PropertyLength", "A", "SocketUnion", "Half-length (centre to outer edge)"
        ),
        PropertySpec("App::PropertyLength", "C", "SocketUnion", "Socket boss wall thickness"),
        PropertySpec("App::PropertyLength", "D", "SocketUnion", "Bore diameter"),
        PropertySpec("App::PropertyLength", "E", "SocketUnion", "Socket depth"),
        PropertySpec(
            "App::PropertyString",
            "Conn",
            "SocketUnion",
            "Connection type (SW=Socket Weld, TH=Threaded)",
        ),
    ),
}


def define_socket_properties(obj: Any, kind: str, values: Mapping[str, Any]) -> None:
    define_properties(obj, SOCKET_SPECS[kind], values)
