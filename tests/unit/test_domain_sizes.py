# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for nominal pipe sizes and ports."""

from __future__ import annotations

import pytest

from quetzal.domain.pipe_sizes import (
    PIPE_OUTSIDE_DIAMETERS_MM,
    normalize_size,
    outside_diameter,
)
from quetzal.domain.ports import Port, Vec3, nearest_port_index


def test_size_lookup_is_normalized():
    assert normalize_size(" dn100 ") == "DN100"
    assert outside_diameter("dn100") == 114.3
    assert outside_diameter("DN50") == 60.32


def test_size_default_and_error():
    assert outside_diameter("DN999", 0.0) == 0.0
    with pytest.raises(KeyError):
        outside_diameter("DN999")


def test_size_table_is_immutable():
    with pytest.raises(TypeError):
        PIPE_OUTSIDE_DIAMETERS_MM["DN50"] = 1.0  # type: ignore[index]


def test_vec3_math():
    a = Vec3(1, 2, 3)
    b = Vec3(2, 0, 0)
    assert (a + b).as_tuple() == (3, 2, 3)
    assert (a - b).as_tuple() == (-1, 2, 3)
    assert a.dot(b) == 2
    assert Vec3(3, 4, 0).length == 5
    assert Vec3(3, 4, 0).normalized().as_tuple() == pytest.approx((0.6, 0.8, 0.0))
    assert Vec3().normalized().as_tuple() == (0.0, 0.0, 0.0)


def test_nearest_port():
    ports = [
        Port(Vec3(0, 0, 0)),
        Port(Vec3(0, 0, 100)),
        Port(Vec3(0, 0, 200)),
    ]
    assert nearest_port_index(ports, Vec3(0, 0, 90)) == 1
    assert nearest_port_index(ports, Vec3(0, 0, 190)) == 2
    assert nearest_port_index([], Vec3()) == -1
