# SPDX-License-Identifier: LGPL-3.0-or-later
"""Bridge from legacy command metadata to the lazy form registry."""

from __future__ import annotations

from dataclasses import replace

from ...application.command_registry import CommandSpec
from ...application.macro_source import command_source
from ...ui.forms import open_form
from .commands import register_spec


def register_form_command(name: str, legacy, group: str, source: str = ""):
    """Register a form command whose dialog is resolved by ``open_form``."""

    spec = CommandSpec.from_legacy(name, legacy, group, source)
    macro_source = source or command_source(getattr(legacy, "Activated", None) or (lambda: None))
    spec = replace(
        spec,
        handler=lambda: open_form(name),
        macro_source=macro_source,
        command=None,
    )
    return register_spec(spec, replace=True)


def register_legacy_command(name: str, legacy, group: str, source: str = ""):
    """Register a non-form legacy command through CommandSpec metadata."""

    spec = CommandSpec.from_legacy(name, legacy, group, source)
    return register_spec(spec, replace=True)
