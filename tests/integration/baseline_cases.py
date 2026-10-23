# SPDX-License-Identifier: LGPL-3.0-or-later
"""Deterministic feature snapshots used to protect geometry during refactors.

The JSON files under ``baselines/`` were captured before splitting Valve and
Flange into strategies/builders.  Each case pins volume, area, bounding box,
ports, directions and the serialized property values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

BASELINE_DIR = Path(__file__).resolve().parent / "baselines"

_IGNORED_PROPERTIES = {
    "Shape",
    "Proxy",
    "Label",
    "Label2",
    "ExpressionEngine",
    "Visibility",
    "ShapeMaterial",
    "Placement",
    "Ports",
    "PortDirections",
    "_ElementMapVersion",
}

VALVE_CASES: Dict[str, Dict[str, Any]] = {
    "legacy_ball": dict(DN="DN50", VType="ball", ODBody=72, ID=50, H=40, Kv=150),
    "legacy_globe": dict(DN="DN50", VType="globe", ODBody=72, ID=50, H=40, Kv=150),
    "knife_gate": dict(DN="DN50", VType="KnifeGate_Handwheel", ODBody=102, ID=50, H=48, Kv=287),
    "pinch": dict(DN="DN50", VType="Pinch_Manual", ODBody=165, ID=50, H=195, Kv=0),
    "socket_weld": dict(
        DN="DN50",
        VType="ball",
        ODBody=72,
        ID=50,
        H=40,
        Kv=150,
        OD=60.32,
        E=8.0,
        Conn="SW",
    ),
    "threaded": dict(
        DN="DN50",
        VType="ball",
        ODBody=72,
        ID=50,
        H=40,
        Kv=150,
        OD=60.32,
        E=8.0,
        Conn="TH",
    ),
    "flanged_ball": dict(
        DN="DN50",
        VType="Ball_LongPatternRF",
        ODBody=72,
        ID=50,
        H=203,
        Kv=10000,
        Conn="150lb",
        flgD=152.4,
        flgt=19.05,
        flgdrf=91.95,
        flgtrf=1.6,
        flgdf=120.65,
        flgf=19.05,
        flgn=4,
        actuator="Handle",
        bottomH=49,
        topH=108,
    ),
    "flanged_swing": dict(
        DN="DN50",
        VType="Check_Swing_FullPortRF",
        ODBody=72,
        ID=50,
        H=203,
        Kv=0,
        Conn="150lb",
        flgD=152.4,
        flgt=19.05,
        flgdrf=91.95,
        flgtrf=1.6,
        flgdf=120.65,
        flgf=19.05,
        flgn=4,
        actuator="Handle",
        bottomH=49,
        topH=108,
    ),
}

# rating, positional propList, FClass
FLANGE_CASES = {
    "SO_150lb": (
        "No rating",
        [
            "DN50",
            "SO",
            152.40,
            61.98,
            120.65,
            19.05,
            19.05,
            4,
            1.60,
            91.95,
            0,
            0,
            77.72,
            0,
            25.40,
            0,
            0,
        ],
        "150lb",
    ),
    "WN_150lb": (
        "SCH-STD",
        [
            "DN50",
            "WN",
            152.40,
            52.5018,
            120.65,
            19.05,
            19.05,
            4,
            1.60,
            91.95,
            35.56,
            77.72,
            60.45,
            7.87,
            63.50,
            0,
            0,
        ],
        "150lb",
    ),
    "SW_150lb": (
        "No rating",
        [
            "DN50",
            "SW",
            152.40,
            52.58,
            120.65,
            19.05,
            19.05,
            4,
            1.60,
            91.95,
            0,
            0,
            77.72,
            0,
            25.40,
            61.98,
            17.53,
        ],
        "150lb",
    ),
    "LJ_150lb": (
        "No rating",
        [
            "DN50",
            "LJ",
            152.40,
            62.48,
            120.65,
            19.05,
            19.05,
            4,
            0,
            0,
            0,
            0,
            77.72,
            7.87,
            25.40,
            0,
            0,
        ],
        "150lb",
    ),
    "BL_150lb": (
        "No rating",
        ["DN50", "BL", 152.4, 0, 120.65, 19.05, 19.05, 4, 1.60, 91.95, 0, 0, 0, 0, 0, 0, 0],
        "150lb",
    ),
    "SO_DIN_PN16": (
        "No rating",
        ["DN50", "SO", 165, 61.5, 125, 18, 20, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "PN16",
    ),
}


def snapshot(obj: Any) -> Dict[str, Any]:
    shape = obj.Shape
    box = shape.BoundBox
    return {
        "volume": round(shape.Volume, 6),
        "area": round(shape.Area, 6),
        "bbox": [
            round(value, 6)
            for value in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)
        ],
        "ports": [[round(coord, 6) for coord in port] for port in obj.Ports],
        "dirs": [[round(coord, 6) for coord in direction] for direction in obj.PortDirections],
        "valid": shape.isValid(),
        "props": {
            prop: str(getattr(obj, prop))
            for prop in obj.PropertiesList
            if prop not in _IGNORED_PROPERTIES
        },
    }


def load_baseline(name: str) -> Dict[str, Any]:
    with (BASELINE_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_close(path: str, actual: float, expected: float) -> None:
    tolerance = max(1e-3, abs(expected) * 1e-7)
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{path}: expected {expected}, got {actual} (tol {tolerance})")


def assert_matches(name: str, actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
    if "error" in expected:
        raise AssertionError(f"{name}: baseline recorded an error: {expected['error']}")
    assert actual["valid"] == expected["valid"], f"{name}: validity changed"
    for field in ("volume", "area"):
        _assert_close(f"{name}.{field}", actual[field], expected[field])
    for index, value in enumerate(expected["bbox"]):
        _assert_close(f"{name}.bbox[{index}]", actual["bbox"][index], value)
    assert actual["ports"] == expected["ports"], f"{name}: ports changed"
    assert actual["dirs"] == expected["dirs"], f"{name}: port directions changed"
    assert actual["props"] == expected["props"], f"{name}: properties changed"
