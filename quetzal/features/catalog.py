# SPDX-License-Identifier: LGPL-3.0-or-later
"""Registry populated with the features migrated from ``pFeatures``."""

from __future__ import annotations

from ..application.feature_registry import FeatureRegistry
from .cap import CAP_FEATURE
from .gasket import GASKET_FEATURE
from .pipe import PIPE_FEATURE
from .terminal_adapter import TERMINAL_ADAPTER_FEATURE

FEATURES = FeatureRegistry()

for _definition in (PIPE_FEATURE, CAP_FEATURE, TERMINAL_ADAPTER_FEATURE, GASKET_FEATURE):
    FEATURES.register(_definition)

__all__ = ["FEATURES"]
