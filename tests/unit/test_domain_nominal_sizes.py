# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for DN/NPS nominal-size identities."""

from __future__ import annotations

import pytest

from quetzal.domain import nominal_sizes
from quetzal.domain.nominal_sizes import NominalSize


def test_known_pairs():
    assert nominal_sizes.dn_to_nps("DN50") == "2"
    assert nominal_sizes.nps_to_dn("2") == "DN50"
    assert nominal_sizes.nps_to_dn('NPS 2"') == "DN50"


def test_parse_and_display():
    assert nominal_sizes.parse("DN100") == NominalSize("DN100", "4")
    assert nominal_sizes.parse("NPS 4") == NominalSize("DN100", "4")
    assert nominal_sizes.parse("4") == NominalSize("DN100", "4")
    assert nominal_sizes.parse("unknown") is None
    assert nominal_sizes.display("DN50", 1) == "NPS 2"
    assert nominal_sizes.display("NPS 2", 0) == "DN50"
    assert nominal_sizes.display("XX", 1) == "XX"


def test_unknown_dn_raises():
    with pytest.raises(Exception):
        nominal_sizes.from_dn("DN9999")


def test_all_sizes_are_consistent():
    for size in nominal_sizes.all_sizes():
        assert nominal_sizes.nps_to_dn(size.nps) == size.dn
        assert nominal_sizes.dn_to_nps(size.dn) == size.nps
