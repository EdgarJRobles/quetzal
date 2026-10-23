# SPDX-License-Identifier: LGPL-3.0-or-later
"""Canonical preview keys and filenames (no filesystem, no GUI)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_INVALID = re.compile(r'[\\/:*?"<>|]')


def safe_component(text: str) -> str:
    cleaned = _INVALID.sub("_", str(text)).strip()
    return cleaned or "preview"


@dataclass(frozen=True)
class PreviewKey:
    family: str
    rating: str
    size: str
    secondary: str = ""
    variant: str = ""

    @property
    def legacy_stem(self) -> str:
        stem = f"{self.rating}{self.size}"
        if self.secondary:
            stem += f"x{self.secondary}"
        return stem

    @property
    def stem(self) -> str:
        if self.variant:
            return f"{self.legacy_stem}__{safe_component(self.variant)}"
        return self.legacy_stem

    @property
    def filename(self) -> str:
        return safe_component(self.stem) + ".png"
