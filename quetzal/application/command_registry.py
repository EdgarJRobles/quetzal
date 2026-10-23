# SPDX-License-Identifier: LGPL-3.0-or-later
"""Command metadata registry.

The FreeCAD workbench historically described each command twice: once in a
class (``GetResources``/``IsActive``/``Activated``) and again in the
``InitGui`` toolbar/menu lists.  This registry records one :class:`CommandSpec`
per command and lets the layout reference commands by name.

Existing command classes are adopted through :meth:`CommandRegistry.add_legacy`;
new commands can be declared directly with a handler and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from ..domain.errors import QuetzalError


class CommandRegistrationError(QuetzalError):
    """Raised for invalid or duplicate command metadata."""


Handler = Callable[[], Any]


@dataclass(frozen=True)
class CommandSpec:
    name: str
    group: str
    handler: Optional[Handler] = None
    menu_text: str = ""
    tooltip: Optional[str] = None
    icon: Optional[str] = None
    accel: Optional[str] = None
    context: Optional[str] = None
    macro_source: str = ""
    is_active: Optional[Handler] = None
    command: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.name.startswith("Quetzal_"):
            raise CommandRegistrationError(
                f"Command names must start with 'Quetzal_': {self.name!r}"
            )
        if not self.menu_text:
            raise CommandRegistrationError(f"Command {self.name!r} needs menu_text")
        if self.icon and ("/" in self.icon or "\\" in self.icon or self.icon.endswith(".svg")):
            raise CommandRegistrationError(
                f"Command {self.name!r} icon must be a bare name: {self.icon!r}"
            )

    @property
    def icon_name(self) -> str:
        return self.icon or self.name

    @property
    def context_name(self) -> str:
        return self.context or self.name

    @classmethod
    def from_legacy(cls, name: str, command: Any, group: str, source: str) -> "CommandSpec":
        resources = command.GetResources() if hasattr(command, "GetResources") else {}
        return cls(
            name=name,
            group=group,
            handler=getattr(command, "Activated", None),
            menu_text=resources.get("MenuText", name),
            tooltip=resources.get("ToolTip"),
            icon=resources.get("Pixmap", name),
            accel=resources.get("Accel"),
            context=name,
            macro_source=source,
            is_active=getattr(command, "IsActive", None),
            command=command,
        )


class CommandRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, CommandSpec] = {}
        self.legacy_only: Dict[str, str] = {}

    def add(self, spec: CommandSpec, replace: bool = False) -> CommandSpec:
        if spec.name in self._specs and not replace:
            raise CommandRegistrationError(f"Command {spec.name!r} is already registered")
        self._specs[spec.name] = spec
        return spec

    def add_legacy(self, name: str, command: Any, source: str, group: str) -> CommandSpec:
        spec = CommandSpec.from_legacy(name, command, group, source)
        return self.add(spec, replace=True)

    def mark_legacy_only(self, name: str, reason: str) -> None:
        self.legacy_only[name] = reason

    def get(self, name: str) -> CommandSpec:
        try:
            return self._specs[name]
        except KeyError:
            raise CommandRegistrationError(f"Unknown command {name!r}") from None

    def names(self) -> Tuple[str, ...]:
        return tuple(self._specs)

    def by_group(self, group: str) -> Tuple[CommandSpec, ...]:
        return tuple(spec for spec in self._specs.values() if spec.group == group)

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, name: object) -> bool:
        return name in self._specs

    def validate_layout(
        self, groups: Dict[str, Iterable[str]], legacy_only: Dict[str, str]
    ) -> None:
        listed = []
        for group, names in groups.items():
            for name in names:
                listed.append(name)
                if name not in self._specs:
                    raise CommandRegistrationError(
                        f"Layout lists unregistered command {name!r} in group {group!r}"
                    )
        duplicates = {name for name in listed if listed.count(name) > 1}
        if duplicates:
            raise CommandRegistrationError(f"Commands listed more than once: {sorted(duplicates)}")
        unlisted = set(self._specs) - set(listed) - set(legacy_only)
        if unlisted:
            raise CommandRegistrationError(
                f"Registered commands missing from the layout: {sorted(unlisted)}"
            )


REGISTRY = CommandRegistry()
