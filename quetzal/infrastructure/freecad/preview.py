# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD renderer for dialog previews.

The renderer captures a temporary object and restores the camera, camera type,
selection and visibility even when the factory or the image save fails.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import FreeCAD
import FreeCADGui

from ...application.preview import PreviewService
from ...domain.preview import PreviewKey
from ..preview_paths import PreviewCache, PreviewPaths


def _visibility(obj: Any) -> Any:
    view = getattr(obj, "ViewObject", None)
    return getattr(view, "Visibility", None) if view is not None else None


def _set_visibility(obj: Any, value: Any) -> None:
    view = getattr(obj, "ViewObject", None)
    if view is not None and value is not None:
        view.Visibility = value


class TemporaryScene:
    """Context manager that restores the user's view and selection."""

    def __init__(self, document: Any, gui: Any, view: Any) -> None:
        self.document = document
        self.gui = gui
        self.view = view
        self._before: set = set()
        self._selection: List[Tuple[Any, Tuple[str, ...]]] = []
        self._camera = None
        self._camera_type = None
        self._visibility: Dict[str, Any] = {}

    def __enter__(self) -> "TemporaryScene":
        self._before = {obj.Name for obj in self.document.Objects}
        self._selection = [
            (item.Object, tuple(item.SubElementNames))
            for item in self.gui.Selection.getSelectionEx()
        ]
        self._camera = self.view.getCamera()
        if hasattr(self.view, "getCameraType"):
            self._camera_type = self.view.getCameraType()
        self._visibility = {
            obj.Name: state
            for obj in self.document.Objects
            if (state := _visibility(obj)) is not None
        }
        self.gui.Selection.clearSelection()
        return self

    def created(self) -> List[Any]:
        return [obj for obj in self.document.Objects if obj.Name not in self._before]

    def prepare(self, primary: Any) -> None:
        for obj in self.document.Objects:
            if obj is not primary:
                _set_visibility(obj, False)
        self.view.viewAxometric()
        if hasattr(self.view, "setCameraType"):
            self.view.setCameraType("Orthographic")
        self.view.fitAll()
        if hasattr(self.gui, "updateGui"):
            self.gui.updateGui()

    def __exit__(self, exc_type, exc, tb) -> None:
        for obj in reversed(self.created()):
            if self.document.getObject(obj.Name) is not None:
                self.document.removeObject(obj.Name)
        for name, state in self._visibility.items():
            target = self.document.getObject(name)
            if target is not None:
                _set_visibility(target, state)
        if self._camera is not None:
            self.view.setCamera(self._camera)
        if self._camera_type is not None and hasattr(self.view, "setCameraType"):
            self.view.setCameraType(self._camera_type)
        for obj, subelements in self._selection:
            try:
                if subelements:
                    for subelement in subelements:
                        self.gui.Selection.addSelection(obj, subelement)
                else:
                    self.gui.Selection.addSelection(obj)
            except Exception:
                pass
        try:
            self.document.recompute()
        except Exception:
            pass


class FreeCADPreviewRenderer:
    def capture(self, key: PreviewKey, factory: Callable[[], Any], target: Any) -> bool:
        document = FreeCAD.ActiveDocument
        gui = FreeCADGui.ActiveDocument
        if document is None or gui is None:
            return False
        view = gui.ActiveView
        if view is None:
            return False
        target = Path(target)
        with TemporaryScene(document, gui, view) as scene:
            primary = factory()
            if isinstance(primary, (list, tuple)):
                primary = primary[-1] if primary else None
            if primary is None:
                created = scene.created()
                primary = created[-1] if created else None
            if primary is None:
                return False
            primary.Placement = FreeCAD.Placement()
            document.recompute()
            scene.prepare(primary)
            temporary = target.with_name("." + target.name + ".tmp")
            view.saveImage(str(temporary), 300, 300, "Transparent")
            if not temporary.exists() or temporary.stat().st_size == 0:
                return False
            os.replace(temporary, target)
        return target.exists()


def default_preview_service() -> PreviewService:
    root = Path(__file__).resolve().parents[3]
    try:
        legacy = Path(FreeCAD.getUserAppDataDir()) / "Mod" / "quetzal" / "iconz" / "PreviewSections"
    except Exception:
        legacy = None
    paths = PreviewPaths(root=root, legacy_root=legacy)
    return PreviewService(
        PreviewCache(paths),
        FreeCADPreviewRenderer(),
        logger=lambda message: FreeCAD.Console.PrintWarning(message + "\n"),
    )
