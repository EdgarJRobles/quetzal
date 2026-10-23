# SPDX-License-Identifier: LGPL-3.0-or-later
"""Declarative feature registry.

Before this module, adding a feature meant editing ``pCmd.make*`` in several
places, copying an ``addObject``/``ViewProvider``/placement block and keeping
``pFeatures.objs`` in sync.  A :class:`FeatureDefinition` now describes a
feature once and the :class:`FeatureRegistry` makes it available to generic
factories.

The registry itself is FreeCAD-free: proxies are injected as plain classes and
the registry only calls them.  Adapters live in ``quetzal.infrastructure``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from ..domain.errors import FeatureRegistrationError
from ..domain.ports import Vec3

ProxyFactory = Callable[[Any, str, Sequence[Any]], None]


def _default_proxy_factory(
    proxy: Callable[..., Any],
    accepted_prop_counts: Tuple[int, ...],
) -> ProxyFactory:
    """Replicate the historic ``len(propList) == N`` fallback rule."""

    def create(obj: Any, rating: str, properties: Sequence[Any]) -> None:
        if properties and (not accepted_prop_counts or len(properties) in accepted_prop_counts):
            proxy(obj, rating, *properties)
        else:
            proxy(obj, rating)

    return create


@dataclass(frozen=True)
class FeatureDefinition:
    """Everything the generic insertion service needs to build a feature."""

    key: str
    proxy: Callable[..., Any]
    label: str
    icon: str
    object_type: str = "Part::FeaturePython"
    accepted_prop_counts: Tuple[int, ...] = field(default_factory=tuple)
    alignment_axis: Vec3 = Vec3(0.0, 0.0, 1.0)
    _create: Optional[ProxyFactory] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise FeatureRegistrationError("Feature key must not be empty")
        if not self.label.strip():
            raise FeatureRegistrationError(f"Feature {self.key!r} needs a label")
        if not self.icon.strip():
            raise FeatureRegistrationError(f"Feature {self.key!r} needs an icon")
        if not callable(self.proxy):
            raise FeatureRegistrationError(f"Feature {self.key!r} proxy must be callable")

    def create(self, obj: Any, rating: str, properties: Sequence[Any]) -> None:
        """Attach the proxy to ``obj`` using the declared property count."""

        factory = self._create or _default_proxy_factory(self.proxy, self.accepted_prop_counts)
        factory(obj, rating, tuple(properties))


class FeatureRegistry:
    """Mutable catalogue of feature definitions, keyed by PType."""

    def __init__(self) -> None:
        self._definitions: Dict[str, FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition, replace: bool = False) -> FeatureDefinition:
        if not isinstance(definition, FeatureDefinition):
            raise FeatureRegistrationError(
                f"Expected FeatureDefinition, got {type(definition).__name__}"
            )
        if definition.key in self._definitions and not replace:
            raise FeatureRegistrationError(f"Feature {definition.key!r} is already registered")
        self._definitions[definition.key] = definition
        return definition

    def get(self, key: str) -> FeatureDefinition:
        try:
            return self._definitions[key]
        except KeyError:
            known = ", ".join(sorted(self._definitions)) or "<none>"
            raise KeyError(f"Unknown feature {key!r}; registered: {known}") from None

    def __contains__(self, key: object) -> bool:
        return key in self._definitions

    def __len__(self) -> int:
        return len(self._definitions)

    def __iter__(self):
        return iter(self._definitions.values())

    def keys(self) -> Tuple[str, ...]:
        return tuple(self._definitions)
