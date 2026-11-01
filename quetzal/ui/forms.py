# SPDX-License-Identifier: LGPL-3.0-or-later
"""Lazy form registry used by command objects.

Commands should not import a concrete form module just to open a dialog.  A
``FormSpec`` names the command, the factory and the UI category; the registry
resolves the factory only when the command is activated.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass(frozen=True)
class FormSpec:
    command: str
    factory: str  # "module:function"
    category: str
    needs_preview: bool = True
    needs_document: bool = True

    def resolve(self) -> Callable[..., Any]:
        module_name, _, attribute = self.factory.partition(":")
        if not module_name or not attribute:
            raise ValueError(f"Invalid form factory: {self.factory!r}")
        module = importlib.import_module(module_name)
        return getattr(module, attribute)


class FormRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, FormSpec] = {}

    def add(self, spec: FormSpec, replace: bool = False) -> FormSpec:
        if spec.command in self._specs and not replace:
            raise ValueError(f"Form for {spec.command!r} is already registered")
        self._specs[spec.command] = spec
        return spec

    def get(self, command: str) -> FormSpec:
        try:
            return self._specs[command]
        except KeyError:
            raise KeyError(f"No form registered for {command!r}") from None

    def names(self) -> Tuple[str, ...]:
        return tuple(self._specs)

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, command: object) -> bool:
        return command in self._specs


FORMS = FormRegistry()


def open_form(command: str, services: Optional[Any] = None) -> Any:
    """Instantiate the form registered for ``command``.

    Forms that accept a ``services`` keyword receive the injected container;
    legacy forms are called without arguments.
    """

    register_default_forms()
    factory = FORMS.get(command).resolve()
    parameters = inspect.signature(factory).parameters
    if "services" in parameters:
        return factory(services=services)
    return factory()


def register_default_forms() -> FormRegistry:
    specs = (
        ("Quetzal_InsertPipe", "pForms:insertPipeForm", "pipe"),
        ("Quetzal_InsertElbow", "pForms:insertElbowForm", "pipe"),
        ("Quetzal_InsertDuctElbow", "pForms:insertDuctElbowForm", "pipe"),
        ("Quetzal_InsertTee", "pForms:insertTeeForm", "pipe"),
        ("Quetzal_InsertReduct", "pForms:insertReductForm", "pipe"),
        ("Quetzal_InsertDuctReduction", "pForms:insertDuctReductionForm", "pipe"),
        ("Quetzal_InsertCap", "pForms:insertCapForm", "pipe"),
        ("Quetzal_InsertCoupling", "pForms:insertCouplingUnionForm", "pipe"),
        ("Quetzal_InsertValve", "pForms:insertValveForm", "pipe"),
        ("Quetzal_InsertFlange", "pForms:insertFlangeForm", "pipe"),
        ("Quetzal_InsertGasket", "pForms:insertGasketForm", "pipe"),
        ("Quetzal_InsertOutlet", "pForms:insertOutletForm", "pipe"),
        ("Quetzal_InsertUBolt", "pForms:insertUboltForm", "pipe"),
        ("Quetzal_InsertPypeLine", "pForms:insertPypeLineForm", "pipe"),
        ("Quetzal_InsertBranch", "pForms:insertBranchForm", "pipe"),
        ("Quetzal_InsertTank", "pForms:insertTankForm", "pipe"),
        ("Quetzal_InsertTerminalAdapter", "pForms:insertTerminalAdapterForm", "pipe"),
        ("Quetzal_InsertRoute", "pForms:insertRouteForm", "pipe"),
        ("Quetzal_InsertBeam", "pForms:insertBeamForm", "pipe"),
        ("Quetzal_BreakPipe", "pForms:breakForm", "pipe"),
        ("Quetzal_JoinPype", "pForms:joinForm", "pipe"),
        ("Quetzal_InsertSection", "fFeatures:insertSectForm", "frame"),
        ("Quetzal_FrameBranchManager", "fFeatures:frameBranchForm", "frame"),
    )
    for command, factory, category in specs:
        if command not in FORMS:
            FORMS.add(FormSpec(command, factory, category))
    return FORMS
