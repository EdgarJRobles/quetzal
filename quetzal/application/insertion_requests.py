# SPDX-License-Identifier: LGPL-3.0-or-later
"""Application requests and ports for form-driven insertion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol


@dataclass(frozen=True)
class PipeInsertRequest:
    rating: str
    psize: str
    od: float
    thk: float
    height: float
    pypeline: Optional[str] = None


class PipeInserter(Protocol):
    def insert_pipe(self, request: PipeInsertRequest) -> Any:
        """Insert the pipe and return the created document object."""


@dataclass(frozen=True)
class FittingInsertRequest:
    kind: str
    props: tuple[Any, ...]
    rating: Optional[str] = None
    pypeline: Optional[str] = None
    options: Mapping[str, Any] = field(default_factory=dict)


class FittingInserter(Protocol):
    def insert(self, request: FittingInsertRequest) -> Any:
        """Insert a fitting and return the created document object."""
