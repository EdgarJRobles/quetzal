# SPDX-License-Identifier: LGPL-3.0-or-later
"""Single source of truth for toolbar/menu command order.

Texts are plain strings; ``InitGui`` wraps them with the original
``QT_TRANSLATE_NOOP("Workbench", ...)`` contexts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..application.command_registry import REGISTRY

UTILS: Tuple[str, ...] = (
    "Quetzal_SelectSolids",
    "Quetzal_QueryModel",
    "Quetzal_MoveWorkPlane",
    "Quetzal_OffsetWorkPlane",
    "Quetzal_RotateWorkPlane",
    "Quetzal_HackedLine",
    "Quetzal_MoveHandle",
    "Quetzal_PressureLossCalculator",
)

FRAME: Tuple[str, ...] = (
    "Quetzal_FrameIt",
    "Quetzal_FrameBranchManager",
    "Quetzal_InsertSection",
    "Quetzal_SpinSection",
    "Quetzal_ReverseBeam",
    "Quetzal_ShiftBeam",
    "Quetzal_PivotBeam",
    "Quetzal_LevelBeam",
    "Quetzal_AlignEdge",
    "Quetzal_RotateJoin",
    "Quetzal_AlignFlange",
    "Quetzal_StretchBeam",
    "Quetzal_ExtendBeam",
    "Quetzal_AdjustFrameAngle",
    "Quetzal_InsertPath",
    "Quetzal_CreateCutList",
)

PIPE: Tuple[str, ...] = (
    "Quetzal_InsertPipe",
    "Quetzal_InsertElbow",
    "Quetzal_InsertDuctElbow",
    "Quetzal_InsertTee",
    "Quetzal_InsertReduct",
    "Quetzal_InsertDuctReduction",
    "Quetzal_InsertCap",
    "Quetzal_InsertCoupling",
    "Quetzal_InsertValve",
    "Quetzal_InsertFlange",
    "Quetzal_InsertGasket",
    "Quetzal_InsertOutlet",
    "Quetzal_InsertUBolt",
    "Quetzal_InsertPypeLine",
    "Quetzal_InsertBranch",
    "Quetzal_InsertTank",
    "Quetzal_InsertTerminalAdapter",
    "Quetzal_InsertRoute",
    "Quetzal_BreakPipe",
    "Quetzal_MateEdges",
    "Quetzal_Flat",
    "Quetzal_ExtendIntersection2",
    "Quetzal_ExtendIntersection1",
    "Quetzal_MakeHeader",
    "Quetzal_Laydown",
    "Quetzal_Raiseup",
    "Quetzal_Attach2Tube",
    "Quetzal_Point2Point",
    "Quetzal_InsertAnyShape",
    "Quetzal_InsertBeam",
)

QM: Tuple[str, ...] = (
    "Quetzal_PipeQM",
    "Quetzal_ElbowQM",
    "Quetzal_FlangeQM",
    "Quetzal_ValveQM",
    "Quetzal_CapQM",
    "Quetzal_TeeQM",
)

GROUPS: Dict[str, Tuple[str, ...]] = {
    "utils": UTILS,
    "frame": FRAME,
    "pipe": PIPE,
    "qm": QM,
}


@dataclass(frozen=True)
class Surface:
    key: str
    group: str
    label: str
    provider: Optional[str] = None


TOOLBARS: Tuple[Surface, ...] = (
    Surface("utils", "utils", "Utils"),
    Surface("frame", "frame", "Frame tools"),
    Surface(
        "draft_snap",
        "draft_snap",
        "Draft snap",
        provider="draftutils.init_tools:get_draft_snap_commands",
    ),
    Surface("pipe", "pipe", "Pipe tools"),
)

MENUS: Tuple[Surface, ...] = (
    Surface("menu_frame", "frame", "Frame tools"),
    Surface("menu_pipe", "pipe", "Pipe tools"),
    Surface("menu_utils", "utils", "Utils"),
    Surface("menu_qm", "qm", "QM Menus"),
)

CONTEXT_MENUS: Tuple[Surface, ...] = (
    Surface("ctx_frames", "frame", "Frames"),
    Surface("ctx_pipes", "pipe", "Pipes"),
    Surface("ctx_utils", "utils", "Utils"),
)


@dataclass(frozen=True)
class WatcherRule:
    key: str
    title: str
    predicate: str
    commands: Tuple[str, ...]


WATCHERS: Tuple[WatcherRule, ...] = (
    WatcherRule(
        "no_objects",
        "No Objects",
        "quetzal.infrastructure.freecad.watchers:no_objects",
        ("Quetzal_HackedLine", "Quetzal_Point2Point"),
    ),
    WatcherRule(
        "wire_objects",
        "Wire Objects",
        "quetzal.infrastructure.freecad.watchers:wire_objects",
        (
            "Quetzal_FrameBranchManager",
            "Quetzal_InsertPipe",
            "Quetzal_InsertPypeLine",
            "Quetzal_InsertBranch",
        ),
    ),
    WatcherRule(
        "tube_objects",
        "Tube Objects",
        "quetzal.infrastructure.freecad.watchers:tube_objects",
        (
            "Quetzal_InsertFlange",
            "Quetzal_InsertTerminalAdapter",
            "Quetzal_InsertElbow",
            "Quetzal_InsertTee",
        ),
    ),
)

LEGACY_ONLY: Dict[str, str] = {
    "Quetzal_JoinPype": "Registered for macros; intentionally absent from toolbars/menus."
}


def group_of(name: str) -> str:
    for group, names in GROUPS.items():
        if name in names:
            return group
    return "legacy"


def validate_registry() -> None:
    REGISTRY.validate_layout(GROUPS, LEGACY_ONLY)
