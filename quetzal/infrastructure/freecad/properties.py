# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD property definitions expressed as data.

A large share of ``pFeatures`` was repetitive ``addProperty(...).X = value``
boilerplate.  :class:`PropertySpec` captures one property as a value object and
:func:`define_properties` applies a whole tuple in one call, so features can
declare *what* they need instead of repeating *how* to register it.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Tuple

import FreeCAD

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP


class _Unset:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<unset>"


UNSET: Any = _Unset()


@dataclass(frozen=True)
class PropertySpec:
    """Declarative description of one FreeCAD property."""

    type_id: str
    name: str
    group: str
    doc: str = ""
    default: Any = UNSET

    def define(self, obj: Any) -> Any:
        prop = obj.addProperty(
            self.type_id,
            self.name,
            self.group,
            QT_TRANSLATE_NOOP("App::Property", self.doc),
        )
        if prop is None:
            return None
        if self.default is not UNSET:
            setattr(obj, self.name, _materialize(self.default))
        return prop


def _materialize(value: Any) -> Any:
    """Copy mutable defaults so documents never share the same list/dict."""

    if isinstance(value, (list, dict, set)):
        return copy.deepcopy(value)
    return value


def define_properties(
    obj: Any,
    specs: Iterable[PropertySpec],
    values: Optional[Mapping[str, Any]] = None,
) -> Tuple[str, ...]:
    """Register ``specs`` on ``obj`` and apply defaults/overrides.

    Returns the names of the properties that were successfully added, which
    lets callers detect schema conflicts if needed.
    """

    added = []
    for spec in specs:
        if spec.define(obj) is not None:
            added.append(spec.name)
    for name, value in (values or {}).items():
        setattr(obj, name, value)
    return tuple(added)


def serialized_length(value: Any) -> str:
    """Render a length property exactly like the legacy ``str(obj.OD)`` code."""

    return str(value)
