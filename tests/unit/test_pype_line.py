# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for PypeLine group resolution."""

from __future__ import annotations

import pytest

from quetzal.application.pype_line import LineGroupError, line_group, resolve_line


class FakeGroup:
    def __init__(self, label):
        self.Label = label
        self.OutList = []


class FakeLine:
    PType = "PypeLine"

    def __init__(self, name, label, group=None, document=None):
        self.Name = name
        self.Label = label
        self.Group = label + "_pieces"
        self.Document = document
        self._parent = group

    def getParentGroup(self):
        return self._parent


class FakeDocument:
    def __init__(self, objects=(), groups=()):
        self.objects = {obj.Name: obj for obj in objects}
        self.groups = list(groups)

    def getObject(self, name):
        return self.objects.get(name)

    def getObjectsByLabel(self, label):
        return [obj for obj in self.objects.values() if obj.Label == label] + [
            group for group in self.groups if group.Label == label
        ]


def test_parent_group_wins():
    line = FakeLine("Line", "Line")
    group = FakeGroup("Line_pieces")
    line._parent = group
    assert line_group(line) is group


def test_unique_label_fallback():
    line = FakeLine("Line", "Line")
    group = FakeGroup("Line_pieces")
    document = FakeDocument([line], [group])
    line.Document = document
    assert line_group(line) is group


def test_missing_or_ambiguous_label_raises():
    line = FakeLine("Line", "Line")
    document = FakeDocument([line], [])
    line.Document = document
    with pytest.raises(LineGroupError):
        line_group(line)
    document.groups = [FakeGroup("Line_pieces"), FakeGroup("Line_pieces")]
    with pytest.raises(LineGroupError):
        line_group(line)
    assert len(document.groups) == 2


def test_resolve_line_by_name_then_label():
    line = FakeLine("Line", "My line")
    document = FakeDocument([line])
    assert resolve_line("Line", document) is line
    assert resolve_line("My line", document) is line
    with pytest.raises(LineGroupError):
        resolve_line("missing", document)
