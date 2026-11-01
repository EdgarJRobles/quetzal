# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the lazy form registry."""

from __future__ import annotations

from quetzal.ui.forms import FormRegistry, FormSpec, open_form, register_default_forms


def test_form_registry_unique_and_lazy():
    registry = FormRegistry()
    spec = FormSpec("Quetzal_Test", "tests.fake_forms:make_form", "utils")
    registry.add(spec)
    assert registry.get("Quetzal_Test") is spec
    assert registry.names() == ("Quetzal_Test",)
    assert "Quetzal_Test" in registry
    try:
        registry.add(spec)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate form registration must fail")


def test_default_forms_cover_pipe_and_frame_commands():
    registry = register_default_forms()
    assert "Quetzal_InsertPipe" in registry
    assert "Quetzal_InsertSection" in registry
    assert len(registry) >= 20


def test_open_form_resolves_lazily():
    # A module-level factory is used so the test does not need Qt.
    import tests.unit.fake_form_module as fake

    registry = FormRegistry()
    FORMS_BACKUP = None
    from quetzal.ui import forms

    FORMS_BACKUP = forms.FORMS
    forms.FORMS = registry
    try:
        registry.add(FormSpec("Quetzal_Test", "tests.unit.fake_form_module:make_form", "utils"))
        result = open_form("Quetzal_Test", services="injected")
        assert result == "injected"
        assert fake.calls == 1
    finally:
        forms.FORMS = FORMS_BACKUP
