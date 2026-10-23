# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pytest configuration: make the addon root importable from any cwd."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
