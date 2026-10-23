# SPDX-License-Identifier: LGPL-3.0-or-later
"""Child storage for PypeBranch: legacy names plus authoritative links.

Old documents store child *names* in ``Tubes``/``Curves`` (StringList).  New
documents add ``TubesLink``/``CurvesLink`` (LinkList) and a ``ChildrenSchema``
flag.  Both representations are written during the transition; links are read
only when the schema says they are authoritative, so an explicitly empty list
never resurrects deleted children from the legacy names.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple

CHILD_SCHEMA_LEGACY = 0
CHILD_SCHEMA_LINKS = 1


def ensure_branch_schema(fp: Any) -> None:
    """Add the new properties to legacy documents (idempotent)."""

    if not hasattr(fp, "TubesLink"):
        prop = fp.addProperty(
            "App::PropertyLinkList",
            "TubesLink",
            "PypeBranch",
            "The tubes of the branch (linked).",
        )
        if prop is not None:
            fp.TubesLink = []
    if not hasattr(fp, "CurvesLink"):
        prop = fp.addProperty(
            "App::PropertyLinkList",
            "CurvesLink",
            "PypeBranch",
            "The curves of the branch (linked).",
        )
        if prop is not None:
            fp.CurvesLink = []
    if not hasattr(fp, "ChildrenSchema"):
        prop = fp.addProperty(
            "App::PropertyInteger",
            "ChildrenSchema",
            "PypeBranch",
            "Child storage schema (0=legacy names, 1=links).",
        )
        if prop is not None:
            fp.ChildrenSchema = CHILD_SCHEMA_LEGACY


def resolve_names(document: Any, names: Iterable[str]) -> Tuple[List[Any], List[str]]:
    objects, missing = [], []
    for name in names or []:
        obj = document.getObject(name) if document is not None and name else None
        if obj is None:
            missing.append(name)
        else:
            objects.append(obj)
    return objects, missing


def branch_children(fp: Any) -> Tuple[List[Any], List[Any]]:
    if getattr(fp, "ChildrenSchema", CHILD_SCHEMA_LEGACY) >= CHILD_SCHEMA_LINKS:
        return list(getattr(fp, "TubesLink", [])), list(getattr(fp, "CurvesLink", []))
    tubes, _ = resolve_names(getattr(fp, "Document", None), getattr(fp, "Tubes", []))
    curves, _ = resolve_names(getattr(fp, "Document", None), getattr(fp, "Curves", []))
    return tubes, curves


def set_branch_children(fp: Any, tubes: Sequence[Any], curves: Sequence[Any]) -> None:
    fp.Tubes = [obj.Name for obj in tubes]
    fp.Curves = [obj.Name for obj in curves]
    fp.TubesLink = list(tubes)
    fp.CurvesLink = list(curves)
    fp.ChildrenSchema = CHILD_SCHEMA_LINKS


def migrate_branch_children(fp: Any) -> bool:
    ensure_branch_schema(fp)
    if getattr(fp, "ChildrenSchema", CHILD_SCHEMA_LEGACY) >= CHILD_SCHEMA_LINKS:
        return True
    document = getattr(fp, "Document", None)
    tubes, missing_tubes = resolve_names(document, getattr(fp, "Tubes", []))
    curves, missing_curves = resolve_names(document, getattr(fp, "Curves", []))
    missing = missing_tubes + missing_curves
    if missing:
        return False
    fp.TubesLink = tubes
    fp.CurvesLink = curves
    fp.ChildrenSchema = CHILD_SCHEMA_LINKS
    return True


def clear_branch_children(fp: Any) -> None:
    fp.Tubes = []
    fp.Curves = []
    fp.TubesLink = []
    fp.CurvesLink = []
    fp.ChildrenSchema = CHILD_SCHEMA_LINKS
