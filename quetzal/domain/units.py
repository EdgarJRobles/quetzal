# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit-safe values for the Quetzal domain.

Catalogue files are not all expressed in the same unit: most dimensions are in
millimetres, structural sections may be documented in inches, masses in
kilograms or pounds, angles in degrees and pressures in bar or psi.  This
module gives every dimension a unit and every conversion a single canonical
target (mm, kg, bar, degree).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .errors import UnitConversionError


@dataclass(frozen=True)
class Unit:
    """A unit of measure with its factor to the canonical unit of its kind."""

    code: str
    symbol: str
    dimension: str
    factor: float
    aliases: Tuple[str, ...] = ()

    def convert_to(self, value: float, target: "Unit") -> float:
        require_same_dimension(self, target)
        return float(value) * self.factor / target.factor


LENGTH = "length"
MASS = "mass"
PRESSURE = "pressure"
ANGLE = "angle"
NOMINAL = "nominal"
DIMENSIONLESS = "dimensionless"
TEXT = "text"
TORQUE = "torque"
FLOW = "flow"

MM = Unit("mm", "mm", LENGTH, 1.0, ("millimeter", "millimetre", "millimeters"))
CM = Unit("cm", "cm", LENGTH, 10.0, ("centimeter", "centimetre"))
M = Unit("m", "m", LENGTH, 1000.0, ("meter", "metre", "meters"))
IN = Unit("in", "in", LENGTH, 25.4, ("inch", "inches", '"'))
FT = Unit("ft", "ft", LENGTH, 304.8, ("foot", "feet"))

KG = Unit("kg", "kg", MASS, 1.0, ("kilogram", "kilograms"))
LB = Unit("lb", "lb", MASS, 0.45359237, ("pound", "pounds", "lbm"))

BAR = Unit("bar", "bar", PRESSURE, 1.0, ("bars",))
PSI = Unit("psi", "psi", PRESSURE, 0.0689475729, ("pound per square inch",))
MPA = Unit("MPa", "MPa", PRESSURE, 10.0, ("megapascal",))
KPA = Unit("kPa", "kPa", PRESSURE, 0.01, ("kilopascal",))

DEG = Unit("deg", "°", ANGLE, 1.0, ("degree", "degrees", "°"))
RAD = Unit("rad", "rad", ANGLE, 57.29577951308232, ("radian", "radians"))

NOMINAL_UNIT = Unit("nominal", "", NOMINAL, 1.0, ("dn", "nps", "size"))
DIMENSIONLESS_UNIT = Unit("1", "", DIMENSIONLESS, 1.0, ("dimensionless", "count", "ratio"))
TEXT_UNIT = Unit("text", "", TEXT, 1.0, ("string", "label"))
NM = Unit("Nm", "N·m", TORQUE, 1.0, ("newton meter", "newton metre", "n*m"))
KV = Unit("m3/h/bar", "m³/h/bar", FLOW, 1.0, ("kv", "flow coefficient"))

UNITS: Tuple[Unit, ...] = (
    MM,
    CM,
    M,
    IN,
    FT,
    KG,
    LB,
    BAR,
    PSI,
    MPA,
    KPA,
    DEG,
    RAD,
    NOMINAL_UNIT,
    DIMENSIONLESS_UNIT,
    TEXT_UNIT,
    NM,
    KV,
)

_UNITS_BY_ALIAS: Dict[str, Unit] = {}
for _unit in UNITS:
    _UNITS_BY_ALIAS[_unit.code.lower()] = _unit
    _UNITS_BY_ALIAS[_unit.symbol.lower()] = _unit
    for _alias in _unit.aliases:
        _UNITS_BY_ALIAS[_alias.lower()] = _unit


def parse_unit(value: str) -> Unit:
    """Resolve a unit code, symbol or alias (case-insensitive)."""

    if not value:
        raise UnitConversionError(f"Unknown unit: {value!r}")
    unit = _UNITS_BY_ALIAS.get(str(value).strip().lower())
    if unit is None:
        raise UnitConversionError(f"Unknown unit: {value!r}")
    return unit


def require_same_dimension(source: Unit, target: Unit) -> None:
    if source.dimension != target.dimension:
        raise UnitConversionError(
            f"Cannot convert {source.code!r} ({source.dimension}) "
            f"to {target.code!r} ({target.dimension})"
        )


def convert(value: float, source: Unit, target: Unit) -> float:
    """Convert ``value`` between two units of the same dimension."""

    return source.convert_to(value, target)


def canonical_unit(dimension: str) -> Unit:
    """Return the canonical unit used by :class:`Quantity` conversions."""

    mapping = {
        LENGTH: MM,
        MASS: KG,
        PRESSURE: BAR,
        ANGLE: DEG,
        NOMINAL: NOMINAL_UNIT,
        DIMENSIONLESS: DIMENSIONLESS_UNIT,
        TEXT: TEXT_UNIT,
        TORQUE: NM,
        FLOW: KV,
    }
    try:
        return mapping[dimension]
    except KeyError:
        raise UnitConversionError(f"Unknown dimension: {dimension!r}") from None


@dataclass(frozen=True)
class Quantity:
    """A numeric value paired with its unit."""

    value: float
    unit: Unit

    def to(self, target: Unit) -> "Quantity":
        require_same_dimension(self.unit, target)
        return Quantity(convert(self.value, self.unit, target), target)

    def canonical(self) -> "Quantity":
        return self.to(canonical_unit(self.unit.dimension))

    @property
    def canonical_value(self) -> float:
        return self.canonical().value

    def __str__(self) -> str:
        if not self.unit.symbol:
            return f"{self.value:g}"
        return f"{self.value:g} {self.unit.symbol}"


def quantity(value: float, unit: "str | Unit") -> Quantity:
    """Convenience factory accepting a unit or a unit code."""

    resolved = unit if isinstance(unit, Unit) else parse_unit(unit)
    return Quantity(float(value), resolved)


def convert_to_mm(value: float, source: "str | Unit") -> float:
    unit = source if isinstance(source, Unit) else parse_unit(source)
    return convert(value, unit, MM)


def convert_to_kg(value: float, source: "str | Unit") -> float:
    unit = source if isinstance(source, Unit) else parse_unit(source)
    return convert(value, unit, KG)


def convert_to_bar(value: float, source: "str | Unit") -> float:
    unit = source if isinstance(source, Unit) else parse_unit(source)
    return convert(value, unit, BAR)


def format_quantity(value: float, unit: "str | Unit", precision: int = 4) -> str:
    resolved = unit if isinstance(unit, Unit) else parse_unit(unit)
    number = f"{float(value):.{precision}g}"
    return f"{number} {resolved.symbol}".rstrip()


def optional_unit(value: Optional[str], default: Unit = MM) -> Unit:
    """Parse an optional metadata unit, falling back to ``default``."""

    if value is None or value == "":
        return default
    return parse_unit(value)
