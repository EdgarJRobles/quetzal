# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the reusable PypeLine parameters and templates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quetzal.application.pype_line_spec import PypeLineSpec, TEMPLATES


def test_spec_validates_required_positive_values():
    spec = PypeLineSpec("DN50", "SCH-STD", 60.32, 3.0, 45.24)
    assert spec.dn == "DN50"
    assert spec.bend_radius == pytest.approx(45.24)
    with pytest.raises(ValueError):
        PypeLineSpec("", "SCH-STD", 60.32, 3.0, 45.24)
    with pytest.raises(ValueError):
        PypeLineSpec("DN50", "SCH-STD", 0, 3.0, 45.24)


def test_spec_from_line_and_bend_override():
    line = SimpleNamespace(PSize="DN80", PRating="SCH-40", OD=88.9, thk=5.49, BendRadius=66.675)
    spec = PypeLineSpec.from_line(line)
    assert spec.dn == "DN80"
    assert spec.rating == "SCH-40"
    assert spec.with_bend_radius(100).bend_radius == pytest.approx(100)


def test_templates_cover_carbon_and_stainless():
    by_name = {template.name: template for template in TEMPLATES}
    carbon = by_name["Carbon steel (SCH-STD)"]
    stainless = by_name["Stainless steel (SCH-10S)"]
    assert carbon.rating == "SCH-STD"
    assert stainless.rating == "SCH-10S"
    assert carbon.bend_radius_for(60.32) == pytest.approx(45.24)
