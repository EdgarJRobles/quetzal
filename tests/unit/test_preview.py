# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for canonical preview keys, paths, cache and service."""

from __future__ import annotations

from pathlib import Path

from quetzal.application.preview import InMemoryPreviewCache, PreviewService
from quetzal.domain.preview import PreviewKey, safe_component
from quetzal.infrastructure.preview_paths import PreviewCache, PreviewPaths


def test_preview_key_legacy_and_variant_names():
    key = PreviewKey("Pipe", "SCH-STD", "DN50")
    assert key.legacy_stem == "SCH-STDDN50"
    assert key.filename == "SCH-STDDN50.png"
    assert PreviewKey("Tee", "3000lb_SW", "DN100", "DN40").stem == "3000lb_SWDN100xDN40"
    assert PreviewKey("Elbow", "SCH-40", "DN50", variant="BA45").filename == (
        "SCH-40DN50__BA45.png"
    )


def test_safe_component_rejects_path_characters():
    assert safe_component("a/b\\c:d") == "a_b_c_d"
    assert safe_component("  ") == "preview"


def test_preview_paths_prefer_override(tmp_path, monkeypatch):
    root = tmp_path / "addon"
    legacy = tmp_path / "legacy"
    paths = PreviewPaths(root=root, legacy_root=legacy)
    assert paths.write_root == root / "iconz" / "PreviewSections"
    assert paths.read_dirs("Pipe")[0] == paths.write_root / "Pipe"
    assert legacy / "Pipe" in paths.read_dirs("Pipe")

    monkeypatch.setenv("QUETZAL_PREVIEW_DIR", str(tmp_path / "override"))
    overridden = PreviewPaths(root=root, legacy_root=legacy)
    assert overridden.write_root == tmp_path / "override"


def test_preview_cache_find_and_target(tmp_path):
    paths = PreviewPaths(root=tmp_path)
    cache = PreviewCache(paths)
    key = PreviewKey("Pipe", "SCH-STD", "DN50")
    assert cache.find(key) is None
    target = cache.target(key)
    assert target.parent.is_dir()
    assert target.name == "SCH-STDDN50.png"
    target.write_bytes(b"png")
    assert cache.find(key) == target


class FakeRenderer:
    def __init__(self, result=True, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def capture(self, key, factory, target):
        self.calls += 1
        if self.error:
            raise self.error
        Path(target).write_bytes(b"png") if self.result else None
        return self.result


def test_service_cache_hit_skips_renderer(tmp_path):
    cache = InMemoryPreviewCache(tmp_path)
    key = PreviewKey("Pipe", "SCH-STD", "DN50")
    cache.images[key.filename] = tmp_path / "hit.png"
    renderer = FakeRenderer()
    service = PreviewService(cache, renderer)
    assert service.image_for(key, lambda: None) == cache.images[key.filename]
    assert renderer.calls == 0


def test_service_miss_renders_once(tmp_path):
    cache = InMemoryPreviewCache(tmp_path)
    renderer = FakeRenderer()
    service = PreviewService(cache, renderer)
    key = PreviewKey("Pipe", "SCH-STD", "DN50")
    result = service.image_for(key, lambda: None)
    assert result == cache.target(key)
    assert renderer.calls == 1


def test_service_swallows_render_errors_and_guards_reentrancy(tmp_path):
    messages = []
    cache = InMemoryPreviewCache(tmp_path)
    renderer = FakeRenderer(error=RuntimeError("boom"))
    service = PreviewService(cache, renderer, logger=messages.append)
    key = PreviewKey("Pipe", "SCH-STD", "DN50")
    assert service.image_for(key, lambda: None) is None
    assert "boom" in messages[-1]

    service._busy = True
    assert service.image_for(key, lambda: None) is None
    service._busy = False
