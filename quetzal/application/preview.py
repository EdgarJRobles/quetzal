# SPDX-License-Identifier: LGPL-3.0-or-later
"""Preview orchestration: cache lookup, render, re-entrancy guard."""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol

from ..domain.preview import PreviewKey


class PreviewCachePort(Protocol):
    def find(self, key: PreviewKey) -> Optional[Any]:
        """Return an existing image path for ``key``, if any."""

    def target(self, key: PreviewKey) -> Any:
        """Return the destination path for ``key`` and ensure its directory."""


class PreviewRenderer(Protocol):
    def capture(self, key: PreviewKey, factory: Callable[[], Any], target: Any) -> bool:
        """Render ``factory()`` to ``target`` and return success."""


class PreviewService:
    def __init__(
        self,
        cache: PreviewCachePort,
        renderer: PreviewRenderer,
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.cache = cache
        self._renderer = renderer
        self._busy = False
        self._log = logger or (lambda message: None)

    def find(self, key: PreviewKey) -> Optional[Any]:
        return self.cache.find(key)

    def image_for(self, key: PreviewKey, factory: Callable[[], Any]) -> Optional[Any]:
        cached = self.cache.find(key)
        if cached is not None:
            return cached
        if self._busy:
            return None
        self._busy = True
        try:
            target = self.cache.target(key)
            if self._renderer.capture(key, factory, target):
                return target
            return None
        except Exception as exc:  # never break a Qt signal
            self._log(f"preview {key.stem}: {exc}")
            return None
        finally:
            self._busy = False


class InMemoryPreviewCache:
    """Test double with deterministic paths."""

    def __init__(self, root: Any) -> None:
        self.root = root
        self.images: dict = {}

    def find(self, key: PreviewKey) -> Optional[Any]:
        return self.images.get(key.filename)

    def target(self, key: PreviewKey) -> Any:
        path = self.root / key.family / key.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
