# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the preview variant contract."""

from __future__ import annotations


class FakeForm:
    def preview_variant(self) -> str:
        return "BA90"


def test_preview_variant_provider_contract():
    form = FakeForm()
    assert form.preview_variant() == "BA90"
