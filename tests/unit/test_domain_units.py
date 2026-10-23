# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the unit-of-measure value objects."""

from __future__ import annotations

import pytest

from quetzal.domain.errors import UnitConversionError
from quetzal.domain.units import (
    BAR,
    DEG,
    FT,
    IN,
    KG,
    LB,
    M,
    MM,
    MPA,
    PSI,
    Quantity,
    convert,
    convert_to_bar,
    convert_to_kg,
    convert_to_mm,
    format_quantity,
    parse_unit,
    quantity,
)


def test_length_conversions():
    assert convert_to_mm(1, IN) == pytest.approx(25.4)
    assert convert_to_mm(1, FT) == pytest.approx(304.8)
    assert convert_to_mm(1, M) == pytest.approx(1000.0)
    assert convert(25.4, MM, IN) == pytest.approx(1.0)


def test_mass_and_pressure_conversions():
    assert convert_to_kg(1, LB) == pytest.approx(0.45359237)
    assert convert_to_bar(1, PSI) == pytest.approx(0.0689475729)
    assert convert_to_bar(1, MPA) == pytest.approx(10.0)


def test_angle_and_quantity_roundtrip():
    q = quantity(180, DEG)
    assert q.canonical_value == pytest.approx(180.0)
    assert q.to(DEG).value == pytest.approx(180.0)
    assert str(Quantity(2.0, IN)) == "2 in"


def test_dimension_mismatch_is_rejected():
    with pytest.raises(UnitConversionError):
        convert(1, MM, KG)
    with pytest.raises(UnitConversionError):
        Quantity(1, BAR).to(MM)


def test_unknown_unit_and_formatting():
    with pytest.raises(UnitConversionError):
        parse_unit("furlong")
    assert format_quantity(60.325, MM) == "60.33 mm"
    assert format_quantity(2.0, IN) == "2 in"


def test_parse_aliases():
    assert parse_unit("inch") is IN
    assert parse_unit("°") is DEG
    assert parse_unit("pound") is LB
    assert parse_unit("dimensionless").dimension == "dimensionless"
