# SPDX-License-Identifier: LGPL-3.0-or-later
"""Feature proxies and the registry that exposes them to generic factories."""

from .base import PypeFeature
from .cap import Cap
from .catalog import FEATURES
from .gasket import Gasket
from .pipe import Pipe
from .terminal_adapter import TerminalAdapter

__all__ = ["Cap", "FEATURES", "Gasket", "Pipe", "PypeFeature", "TerminalAdapter"]
