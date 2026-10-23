# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pure tests for Valve property/geometry mode resolution."""

from __future__ import annotations

import pytest

from quetzal.application.valve import ValveContext
from quetzal.domain.valve_modes import (
    FLANGED,
    GENERIC,
    KNIFE_GATE,
    PINCH,
    SW_TH,
    SWING_CHECK,
    geometry_mode,
    property_mode,
)


@pytest.mark.parametrize(
    "conn, expected",
    [
        (None, GENERIC),
        ("", SW_TH),
        ("SW", SW_TH),
        ("TH", SW_TH),
        ("150lb", FLANGED),
        (" 150lb ", FLANGED),
        ("2500lb", FLANGED),
        ("150LB", SW_TH),  # the legacy comparison is case-sensitive
    ],
)
def test_property_mode(conn, expected):
    assert property_mode(conn) == expected


@pytest.mark.parametrize(
    "conn, rating, expected",
    [
        (None, "ball", GENERIC),
        (None, "KnifeGate_Handwheel", KNIFE_GATE),
        (None, "Pinch_Manual", PINCH),
        (None, "Check_Swing_FullPortRF", GENERIC),  # swing only applies to flanged
        ("SW", "Check_Swing_FullPortRF", SW_TH),
        ("150lb", "Ball_LongPatternRF", FLANGED),
        ("150lb", "Check_Swing_FullPortRF", SWING_CHECK),
        ("150lb", "check_swing_body", SWING_CHECK),
        ("2500lb", "Plug_150lbRF", FLANGED),
    ],
)
def test_geometry_mode(conn, rating, expected):
    assert geometry_mode(conn, rating) == expected


def test_context_reads_legacy_feature_attributes():
    class Feature:
        Height = 203
        Conn = "150lb"
        PRating = "Check_Swing_FullPortRF"

    context = ValveContext.from_feature(Feature())
    assert context.height == pytest.approx(203.0)
    assert context.conn == "150lb"
    assert context.rating == "check_swing_fullportrf"
