# SPDX-License-Identifier: LGPL-3.0-or-later
"""Contract for forms that need more than one preview cache key."""

from __future__ import annotations

from typing import Protocol


class PreviewVariantProvider(Protocol):
    def preview_variant(self) -> str:
        """Return a stable variant suffix for the current form state."""
