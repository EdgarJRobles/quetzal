# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for declarative form validation."""

from __future__ import annotations

from quetzal.application.validation import FieldRule, FormValidator


def validator():
    return FormValidator(
        (
            FieldRule("length", "Length", required=True, kind="number", minimum=1, maximum=10000),
            FieldRule("angle", "Angle", kind="number", minimum=0, maximum=180),
            FieldRule("standard", "Standard", required=True, choices=("ASME", "EN")),
            FieldRule("note", "Note", validator=lambda value: "bad" if "x" in value else None),
        )
    )


def test_valid_values_pass():
    result = validator().validate({"length": "200", "angle": "90", "standard": "ASME", "note": ""})
    assert result.ok
    assert result.first_message == ""


def test_required_and_numeric_errors():
    result = validator().validate({"length": "", "angle": "abc", "standard": ""})
    messages = [issue.message for issue in result.issues]
    assert "Length is required" in messages
    assert "Angle must be a number" in messages
    assert "Standard is required" in messages


def test_bounds_and_choices():
    result = validator().validate({"length": "0", "angle": "270", "standard": "DIN"})
    messages = [issue.message for issue in result.issues]
    assert any("at least 1" in message for message in messages)
    assert any("at most 180" in message for message in messages)
    assert any("must be one of" in message for message in messages)


def test_custom_validator():
    result = validator().validate(
        {"length": "200", "angle": "90", "standard": "EN", "note": "bad-x"}
    )
    assert [issue.message for issue in result.issues] == ["bad"]
