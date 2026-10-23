# SPDX-License-Identifier: LGPL-3.0-or-later
"""Extract a command handler body for FreeCAD's macro recorder.

The legacy helper used ``inspect.getsourcelines(...)[1][pos]`` and broke when
the first body line was blank.  This version dedents the body and degrades to
an empty string for pyc-only installations or dynamic callables.
"""

from __future__ import annotations

import inspect
import textwrap
from typing import Callable


def command_source(func: Callable[..., object]) -> str:
    try:
        lines = inspect.getsourcelines(func)[0]
    except (OSError, TypeError):
        return ""
    for index, line in enumerate(lines):
        if line.lstrip().startswith(("def ", "async def ")):
            return textwrap.dedent("".join(lines[index + 1 :]))
    return ""
