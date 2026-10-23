# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain-level exception hierarchy."""


class QuetzalError(Exception):
    """Base class for all recoverable Quetzal errors."""


class CatalogNotFoundError(QuetzalError):
    """Raised when a catalogue table cannot be located on disk."""

    def __init__(self, family: str, rating: str, path: str) -> None:
        self.family = family
        self.rating = rating
        self.path = path
        super().__init__(
            f"Catalogue table not found for family={family!r}, rating={rating!r} ({path})"
        )


class FeatureRegistrationError(QuetzalError):
    """Raised when a feature definition is invalid or registered twice."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnitConversionError(QuetzalError):
    """Raised when units are unknown or belong to different dimensions."""


class StandardsError(QuetzalError):
    """Raised when standards metadata is invalid or cannot be resolved."""
