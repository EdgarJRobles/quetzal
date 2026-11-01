# SPDX-License-Identifier: LGPL-3.0-or-later
"""Small user-notification port for UI controllers and forms."""

from __future__ import annotations

from typing import Protocol


class UserReporter(Protocol):
    def info(self, message: str) -> None:
        """Show an informational message."""

    def warning(self, message: str) -> None:
        """Show a recoverable warning."""

    def error(self, message: str) -> None:
        """Show an error."""


class NullReporter:
    """No-op reporter for tests and headless use."""

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


class RecordingReporter:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        self.messages.append(("info", message))

    def warning(self, message: str) -> None:
        self.messages.append(("warning", message))

    def error(self, message: str) -> None:
        self.messages.append(("error", message))
