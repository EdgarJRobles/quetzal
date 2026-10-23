# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD view-provider adapter.

The class used to live in ``pCmd`` next to geometry factories.  It only
depends on FreeCAD and the icon resolver, so it belongs to the infrastructure
layer.  ``pCmd.ViewProvider`` still re-exports it for backwards compatibility.
"""

from __future__ import annotations

from typing import Any

import FreeCAD


class ViewProvider:
    """Minimal view provider that gives an object an icon."""

    def __init__(self, obj: Any, icon_fn: str) -> None:
        # In console mode DocumentObject.ViewObject is None (FreeCAD returns
        # Py::None when FreeCADGui has no Gui::Document for the App document),
        # so guard once here for every call site.
        if obj is None or not FreeCAD.GuiUp:
            return
        obj.Proxy = self
        self._check_attr()
        self.icon_fn = _icon_path(icon_fn or "quetzal")

    def _check_attr(self) -> None:
        if not hasattr(self, "icon_fn"):
            setattr(self, "icon_fn", _icon_path("quetzal"))

    def getIcon(self) -> str:
        self._check_attr()
        return self.icon_fn


def _icon_path(icon_name: str) -> str:
    # Imported lazily to avoid pulling FreeCADGui at module import time when
    # this module is used by pure unit tests.
    from quetzal_config import get_icon_path

    return get_icon_path(icon_name)


class FreeCADViewFactory:
    """Attach a :class:`ViewProvider` to a document object when GUI is up."""

    def attach(self, view_object: Any, icon: str) -> None:
        if view_object is None:
            return
        ViewProvider(view_object, icon)
