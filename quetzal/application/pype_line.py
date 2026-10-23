# SPDX-License-Identifier: LGPL-3.0-or-later
"""PypeLine group resolution without relying on ``[0]`` label lookups."""

from __future__ import annotations

from typing import Any, List

from ..domain.errors import QuetzalError


class LineGroupError(QuetzalError):
    def __init__(self, reference: str, candidates: List[Any]) -> None:
        self.reference = reference
        self.candidates = candidates
        super().__init__(
            f"Cannot resolve PypeLine group {reference!r}; candidates="
            f"{[getattr(obj, 'Label', obj) for obj in candidates]}"
        )


def line_group(line: Any) -> Any:
    """Return the DocumentObjectGroup that owns ``line``.

    Preference order: the real parent group, then exactly one label match.
    Ambiguous or missing labels raise instead of silently picking ``[0]``.
    """

    parent = line.getParentGroup() if hasattr(line, "getParentGroup") else None
    if parent is not None and hasattr(parent, "OutList"):
        return parent
    document = getattr(line, "Document", None)
    reference = getattr(line, "Group", "")
    candidates = document.getObjectsByLabel(reference) if document and reference else []
    if len(candidates) != 1:
        raise LineGroupError(reference, list(candidates))
    return candidates[0]


def resolve_line(reference: str, document: Any) -> Any:
    """Resolve a PypeLine by internal name first, then by a unique label."""

    obj = document.getObject(reference) if document else None
    if obj is not None and getattr(obj, "PType", "") == "PypeLine":
        return obj
    candidates = document.getObjectsByLabel(reference) if document else []
    matches = [item for item in candidates if getattr(item, "PType", "") == "PypeLine"]
    if len(matches) == 1:
        return matches[0]
    raise LineGroupError(reference, matches)
