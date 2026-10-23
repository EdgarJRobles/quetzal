# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pure tests for Flange rules extracted from the legacy geometry."""

from __future__ import annotations

import pytest

from quetzal.domain.flange import (
    HUB_TYPES,
    LJ_FILLET_EDGE,
    FlangeSpec as Spec,
)


def spec(**overrides):
    values = dict(
        flange_type="SO",
        D=152.4,
        d=61.98,
        df=120.65,
        f=19.05,
        t=19.05,
        n=4,
        trf=1.6,
        drf=91.95,
        ODp=77.72,
        R=0.0,
        T1=25.4,
    )
    values.update(overrides)
    return Spec(**values)


def test_port_offsets_match_legacy_table():
    assert spec(flange_type="SO").port_offsets() == ((0, 0, -1.6), (0, 0, 1.6))
    assert spec(flange_type="WN", T1=63.5).port_offsets() == ((0, 0, -1.6), (0, 0, 63.5))
    sw_ports = spec(flange_type="SW", T1=25.4, Y=17.53).port_offsets()
    assert sw_ports[0] == (0, 0, -1.6)
    assert sw_ports[1] == pytest.approx((0, 0, 6.27))
    assert spec(flange_type="BL", t=19.05).port_offsets() == ((0, 0, -1.6), (0, 0, 19.05))
    assert spec(flange_type="LJ", trf=0).port_offsets() == ((0, 0, 0), (0, 0, 0))
    assert spec(flange_type="S.O.", trf=0).port_offsets() == ((0, 0, 0), (0, 0, 0))
    assert spec().port_directions() == ((0, 0, -1), (0, 0, 1))


def test_insertion_offsets_match_make_flange():
    assert spec(flange_type="SO").insertion_offset == pytest.approx(-1.6)
    assert spec(flange_type="WN", T1=63.5).insertion_offset == pytest.approx(-61.9)
    assert spec(flange_type="SW", T1=25.4, Y=17.53).insertion_offset == pytest.approx(-6.27)
    assert spec(flange_type="LJ").insertion_offset == pytest.approx(0.0)
    assert spec(flange_type="BL").insertion_offset == pytest.approx(0.0)
    assert spec(flange_type="XX").insertion_offset == pytest.approx(0.0)


def test_hub_predicate_matches_legacy():
    assert spec().has_hub is True
    assert spec(ODp=0).has_hub is False
    assert spec(ODp=61.98).has_hub is False  # ODp > d is required
    assert spec(T1=0).has_hub is False
    assert spec(flange_type="BL").has_hub is False
    assert spec(flange_type="XX").has_hub is False
    assert set(HUB_TYPES) == {"SO", "WN", "SW", "LJ"}


def test_raised_face_predicates_preserve_legacy_quirks():
    assert spec(trf=1.6, drf=91.95).has_raised_face is True
    assert spec(trf=0, drf=91.95).has_raised_face is False
    assert spec(trf=1.6, drf=0).has_raised_face is True  # legacy quirk
    assert spec(trf=1.6, drf=152.4).has_raised_face is False
    assert spec(flange_type="BL", trf=1.6, drf=91.95).has_solid_raised_face is True
    assert spec(flange_type="BL", trf=0).has_solid_raised_face is False


def test_socket_and_weld_neck_predicates():
    assert spec(B2=61.98).has_socket is True
    assert spec(B2=0).has_socket is False
    assert spec(flange_type="WN", dwn=77.72, twn=35.56, ODp=60.45).has_weld_neck is True
    assert spec(flange_type="WN", dwn=0).has_weld_neck is False
    assert spec(flange_type="WN", twn=0).has_weld_neck is False
    assert spec(flange_type="WN", ODp=0).has_weld_neck is False


def test_lj_fillet_edge_and_bolt_phase():
    assert LJ_FILLET_EDGE == {4: 19, 8: 31, 12: 43, 16: 55, 20: 67}
    for n, edge in LJ_FILLET_EDGE.items():
        assert edge == 7 + 3 * n
        assert spec(n=n).lj_fillet_edge == edge
    assert spec(n=6).lj_fillet_edge is None
    assert spec(n=4).bolt_hole_phase == pytest.approx(45.0)
    assert spec(n=8).bolt_hole_phase == pytest.approx(22.5)
    assert spec(n=0).bolt_hole_phase == 0.0
