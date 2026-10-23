# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for PypeBranch legacy/link child storage."""

from __future__ import annotations

from quetzal.application.pype_children import (
    CHILD_SCHEMA_LINKS,
    CHILD_SCHEMA_LEGACY,
    branch_children,
    clear_branch_children,
    ensure_branch_schema,
    migrate_branch_children,
    resolve_names,
    set_branch_children,
)


class FakeDocument:
    def __init__(self, objects):
        self._objects = {obj.Name: obj for obj in objects}

    def getObject(self, name):
        return self._objects.get(name)


class FakeChild:
    def __init__(self, name):
        self.Name = name
        self.Document = None


class FakeBranch:
    def __init__(self, document, tubes=(), curves=()):
        self.Document = document
        self.Tubes = list(tubes)
        self.Curves = list(curves)
        self._properties = set()

    def addProperty(self, type_id, name, group, doc):
        self._properties.add(name)
        setattr(self, name, [] if "List" in type_id else 0)
        return self


def make_branch(legacy=True):
    tubes = [FakeChild("Pipe"), FakeChild("Pipe001")]
    curves = [FakeChild("Elbow")]
    document = FakeDocument(tubes + curves)
    branch = FakeBranch(document, [o.Name for o in tubes], [o.Name for o in curves])
    branch.ChildrenSchema = CHILD_SCHEMA_LEGACY if legacy else CHILD_SCHEMA_LINKS
    return branch, document, tubes, curves


def test_resolve_names_reports_missing():
    branch, document, tubes, curves = make_branch()
    resolved, missing = resolve_names(document, ["Pipe", "Nope"])
    assert resolved == [tubes[0]]
    assert missing == ["Nope"]


def test_ensure_adds_link_and_schema_properties():
    branch, document, tubes, curves = make_branch()
    ensure_branch_schema(branch)
    assert hasattr(branch, "TubesLink")
    assert hasattr(branch, "CurvesLink")
    assert branch.ChildrenSchema == CHILD_SCHEMA_LEGACY


def test_legacy_branch_reads_by_name():
    branch, document, tubes, curves = make_branch()
    assert branch_children(branch) == (tubes, curves)


def test_migrate_resolves_all_names_and_sets_links():
    branch, document, tubes, curves = make_branch()
    ensure_branch_schema(branch)
    assert migrate_branch_children(branch) is True
    assert branch.ChildrenSchema == CHILD_SCHEMA_LINKS
    assert branch.TubesLink == tubes
    assert branch.CurvesLink == curves


def test_migrate_refuses_when_a_child_is_missing():
    branch, document, tubes, curves = make_branch()
    branch.Tubes = ["Pipe", "Deleted"]
    ensure_branch_schema(branch)
    assert migrate_branch_children(branch) is False
    assert branch.ChildrenSchema == CHILD_SCHEMA_LEGACY


def test_links_are_authoritative_even_when_empty():
    branch, document, tubes, curves = make_branch(legacy=False)
    branch.TubesLink = []
    branch.CurvesLink = []
    assert branch_children(branch) == ([], [])


def test_set_and_clear_write_both_representations():
    branch, document, tubes, curves = make_branch(legacy=False)
    set_branch_children(branch, tubes, curves)
    assert branch.Tubes == ["Pipe", "Pipe001"]
    assert branch.Curves == ["Elbow"]
    assert branch.TubesLink == tubes
    assert branch.CurvesLink == curves
    assert branch.ChildrenSchema == CHILD_SCHEMA_LINKS
    clear_branch_children(branch)
    assert branch.Tubes == []
    assert branch.Curves == []
    assert branch.TubesLink == []
    assert branch.CurvesLink == []
