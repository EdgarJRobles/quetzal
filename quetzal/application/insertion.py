# SPDX-License-Identifier: LGPL-3.0-or-later
"""Use case: insert a feature into a document.

The service depends only on small protocols, so it can be tested with a fake
document and reused by every command/factory.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, Sequence

from ..domain.ports import Vec3
from .feature_registry import FeatureDefinition


class DocumentPort(Protocol):
    """Minimal document operations required by :class:`FeatureInserter`."""

    def add_object(self, object_type: str, name: str) -> Any:
        """Create a document object and return it."""

    def place(self, obj: Any, position: Vec3, direction: Vec3, axis: Vec3) -> None:
        """Position ``obj`` so that its local ``axis`` points along ``direction``."""

    def attach_view(self, obj: Any, icon: str) -> None:
        """Attach the GUI view provider when a GUI is available."""


LabelTranslator = Callable[[str], str]


def _identity_label(label: str) -> str:
    return label


class FeatureInserter:
    """Create, configure, place and label a feature from its definition."""

    def __init__(
        self,
        document: DocumentPort,
        label_translator: Optional[LabelTranslator] = None,
    ) -> None:
        self._document = document
        self._translate = label_translator or _identity_label

    def insert(
        self,
        definition: FeatureDefinition,
        rating: str,
        properties: Sequence[Any] = (),
        position: Optional[Vec3] = None,
        direction: Optional[Vec3] = None,
        label: Optional[str] = None,
    ) -> Any:
        obj = self._document.add_object(definition.object_type, definition.key)
        definition.create(obj, rating, properties)
        self._document.attach_view(obj, definition.icon)
        self._document.place(
            obj,
            position or Vec3(),
            direction or Vec3(0.0, 0.0, 1.0),
            definition.alignment_axis,
        )
        obj.Label = self._translate(label or definition.label or definition.key)
        return obj


class InMemoryDocument:
    """Fake :class:`DocumentPort` used by unit tests."""

    def __init__(self) -> None:
        self.objects: list[Any] = []
        self.created: list[tuple[str, str]] = []
        self.views: list[tuple[Any, str]] = []
        self.placements: list[tuple[Any, Vec3, Vec3, Vec3]] = []

    def add_object(self, object_type: str, name: str) -> Any:
        obj = type("FakeObject", (), {})()
        obj.Name = name
        obj.Label = name
        self.objects.append(obj)
        self.created.append((object_type, name))
        return obj

    def place(self, obj: Any, position: Vec3, direction: Vec3, axis: Vec3) -> None:
        self.placements.append((obj, position, direction, axis))

    def attach_view(self, obj: Any, icon: str) -> None:
        self.views.append((obj, icon))
