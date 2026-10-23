# SPDX-License-Identifier: LGPL-3.0-or-later
"""Valve strategy protocol and registry."""

from __future__ import annotations

from typing import Dict, Protocol

from ..geometry import FeatureGeometry
from ...application.valve import ValveContext


class ValveStrategy(Protocol):
    key: str

    def build(self, ctx: ValveContext) -> FeatureGeometry:
        """Return the shape, ports and directions for ``ctx``."""


REGISTRY: Dict[str, ValveStrategy] = {}


def register_strategy(strategy: ValveStrategy, replace: bool = False) -> ValveStrategy:
    if strategy.key in REGISTRY and not replace:
        raise ValueError(f"Valve strategy {strategy.key!r} is already registered")
    REGISTRY[strategy.key] = strategy
    return strategy


def strategy_for(mode: str) -> ValveStrategy:
    try:
        return REGISTRY[mode]
    except KeyError:
        raise KeyError(f"Unknown Valve strategy {mode!r}; known: {sorted(REGISTRY)}") from None
