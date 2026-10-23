# SPDX-License-Identifier: LGPL-3.0-or-later
"""Preview directory policy, independent from FreeCAD."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

from ..domain.preview import PreviewKey


def addon_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class PreviewPaths:
    """Resolve read/write preview directories.

    The addon bundle is preferred for both reading and writing; an explicit
    ``QUETZAL_PREVIEW_DIR`` wins.  The legacy per-user directory is read-only
    fallback so existing installations keep their thumbnails.
    """

    def __init__(
        self,
        root: "str | Path | None" = None,
        legacy_root: "str | Path | None" = None,
        override: Optional[str] = None,
    ) -> None:
        self.root = Path(root) if root is not None else addon_root()
        self.legacy_root = Path(legacy_root) if legacy_root is not None else None
        env_override = os.environ.get("QUETZAL_PREVIEW_DIR")
        self.override = Path(override or env_override) if (override or env_override) else None

    @property
    def write_root(self) -> Path:
        return self.override or (self.root / "iconz" / "PreviewSections")

    def write_dir(self, family: str) -> Path:
        directory = self.write_root / family
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def read_dirs(self, family: str) -> List[Path]:
        directories: List[Path] = [self.write_root / family]
        if self.legacy_root is not None:
            directories.extend([self.legacy_root / family, self.legacy_root])
        unique: List[Path] = []
        for directory in directories:
            if directory not in unique:
                unique.append(directory)
        return unique

    def paths_for(self, key: PreviewKey) -> Iterable[Path]:
        for directory in self.read_dirs(key.family):
            yield directory / key.filename


class PreviewCache:
    def __init__(self, paths: PreviewPaths) -> None:
        self.paths = paths

    @property
    def write_root(self) -> Path:
        return self.paths.write_root

    def find(self, key: PreviewKey) -> Optional[Path]:
        for path in self.paths.paths_for(key):
            if path.is_file() and path.stat().st_size > 0:
                return path
        return None

    def target(self, key: PreviewKey) -> Path:
        return self.paths.write_dir(key.family) / key.filename
