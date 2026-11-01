# SPDX-License-Identifier: LGPL-3.0-or-later
"""Small declarative validation layer for UI forms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    issues: Sequence[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def first_message(self) -> str:
        return self.issues[0].message if self.issues else ""


@dataclass(frozen=True)
class FieldRule:
    field: str
    label: str = ""
    required: bool = False
    kind: str = "text"  # "text" | "number"
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    choices: Sequence[str] = ()
    validator: Optional[Callable[[Any], Optional[str]]] = None

    def validate(self, value: Any) -> Optional[ValidationIssue]:
        name = self.label or self.field
        if value is None or (isinstance(value, str) and not value.strip()):
            if self.required:
                return ValidationIssue(self.field, f"{name} is required")
            return None
        if self.kind == "number":
            try:
                number = float(value)
            except (TypeError, ValueError):
                return ValidationIssue(self.field, f"{name} must be a number")
            if self.minimum is not None and number < self.minimum:
                return ValidationIssue(self.field, f"{name} must be at least {self.minimum:g}")
            if self.maximum is not None and number > self.maximum:
                return ValidationIssue(self.field, f"{name} must be at most {self.maximum:g}")
        elif self.choices and str(value) not in self.choices:
            return ValidationIssue(self.field, f"{name} must be one of: {', '.join(self.choices)}")
        if self.validator is not None:
            message = self.validator(value)
            if message:
                return ValidationIssue(self.field, message)
        return None


class FormValidator:
    def __init__(self, rules: Iterable[FieldRule]) -> None:
        self._rules = tuple(rules)

    @property
    def rules(self) -> tuple[FieldRule, ...]:
        return self._rules

    def validate(self, values: Mapping[str, Any]) -> ValidationResult:
        issues = []
        for rule in self._rules:
            issue = rule.validate(values.get(rule.field))
            if issue is not None:
                issues.append(issue)
        return ValidationResult(tuple(issues))
