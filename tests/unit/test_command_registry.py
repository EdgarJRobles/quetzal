# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for command metadata, layout and macro source extraction."""

from __future__ import annotations

import inspect

import pytest

from quetzal.application.command_registry import (
    CommandRegistrationError,
    CommandRegistry,
    CommandSpec,
)
from quetzal.application.macro_source import command_source
from quetzal.ui import layout


def spec(name="Quetzal_Test", **overrides):
    values = dict(name=name, group="utils", menu_text="Test command")
    values.update(overrides)
    return CommandSpec(**values)


def test_command_spec_validation():
    with pytest.raises(CommandRegistrationError):
        spec("NotQuetzal")
    with pytest.raises(CommandRegistrationError):
        spec(menu_text="")
    with pytest.raises(CommandRegistrationError):
        spec(icon="icon.svg")
    with pytest.raises(CommandRegistrationError):
        spec(icon="dir/icon")

    assert spec(icon=None).icon_name == "Quetzal_Test"
    assert spec(icon="Quetzal_Icon").icon_name == "Quetzal_Icon"
    assert spec(context="Ctx").context_name == "Ctx"


def test_registry_add_get_and_duplicate():
    registry = CommandRegistry()
    registry.add(spec())
    assert registry.get("Quetzal_Test").menu_text == "Test command"
    assert len(registry) == 1
    with pytest.raises(CommandRegistrationError):
        registry.add(spec())
    registry.add(spec(menu_text="Replaced"), replace=True)
    assert registry.get("Quetzal_Test").menu_text == "Replaced"


def test_layout_has_the_expected_order_and_counts():
    assert len(layout.GROUPS["utils"]) == 8
    assert len(layout.GROUPS["frame"]) == 16
    assert len(layout.GROUPS["pipe"]) == 30
    assert len(layout.GROUPS["qm"]) == 6
    assert sum(len(names) for names in layout.GROUPS.values()) == 60
    assert layout.GROUPS["utils"][0] == "Quetzal_SelectSolids"
    assert layout.GROUPS["frame"][-1] == "Quetzal_CreateCutList"
    assert layout.GROUPS["pipe"][0] == "Quetzal_InsertPipe"
    assert layout.GROUPS["pipe"][-1] == "Quetzal_InsertBeam"
    assert layout.GROUPS["qm"] == (
        "Quetzal_PipeQM",
        "Quetzal_ElbowQM",
        "Quetzal_FlangeQM",
        "Quetzal_ValveQM",
        "Quetzal_CapQM",
        "Quetzal_TeeQM",
    )
    assert "Quetzal_JoinPype" in layout.LEGACY_ONLY
    assert [surface.label for surface in layout.CONTEXT_MENUS] == ["Frames", "Pipes", "Utils"]


def test_registry_layout_validation():
    registry = CommandRegistry()
    for name in (name for names in layout.GROUPS.values() for name in names):
        registry.add(spec(name, group=layout.group_of(name)))
    registry.add(spec("Quetzal_JoinPype", group="legacy"))
    registry.validate_layout(layout.GROUPS, layout.LEGACY_ONLY)


def test_registry_layout_rejects_duplicates_and_orphans():
    registry = CommandRegistry()
    for name in (name for names in layout.GROUPS.values() for name in names):
        registry.add(spec(name))
    registry.add(spec("Quetzal_JoinPype", group="legacy"))
    with pytest.raises(CommandRegistrationError):
        registry.validate_layout(
            {"utils": ("Quetzal_SelectSolids", "Quetzal_SelectSolids")},
            layout.LEGACY_ONLY,
        )
    with pytest.raises(CommandRegistrationError):
        registry.validate_layout({"utils": ("Quetzal_Missing",)}, layout.LEGACY_ONLY)


def test_macro_source_extracts_body():
    def handler():
        value = 42
        return value

    source = command_source(handler)
    assert "value = 42" in source
    assert "def handler" not in source
    assert source.startswith("value")


def test_macro_source_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(inspect, "getsourcelines", lambda func: (_ for _ in ()).throw(OSError()))
    assert command_source(lambda: None) == ""
