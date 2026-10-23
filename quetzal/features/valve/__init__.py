# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve geometry strategies (the public Valve facade stays in pFeatures)."""

from ...application.valve import ValveContext
from ...domain.valve_modes import (
    FLANGE_CONNS,
    GENERIC,
    GEOMETRY_MODES,
    KNIFE_GATE,
    PINCH,
    PROPERTY_MODES,
    SW_TH,
    SWING_CHECK,
    geometry_mode,
    property_mode,
)
from .generic import GenericValveStrategy
from .flanged import FlangedValveStrategy
from .knife_gate import KnifeGateValveStrategy
from .pinch import PinchValveStrategy
from .strategy import REGISTRY as VALVE_STRATEGIES
from .strategy import register_strategy, strategy_for
from .sw_th import SocketThreadedValveStrategy
from .swing_check import SwingCheckValveStrategy

__all__ = [
    "FLANGE_CONNS",
    "GENERIC",
    "GEOMETRY_MODES",
    "KNIFE_GATE",
    "GenericValveStrategy",
    "FlangedValveStrategy",
    "KnifeGateValveStrategy",
    "PINCH",
    "PROPERTY_MODES",
    "PinchValveStrategy",
    "SW_TH",
    "SWING_CHECK",
    "SocketThreadedValveStrategy",
    "SwingCheckValveStrategy",
    "VALVE_STRATEGIES",
    "ValveContext",
    "geometry_mode",
    "property_mode",
    "register_strategy",
    "strategy_for",
]
