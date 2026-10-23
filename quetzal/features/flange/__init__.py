# SPDX-License-Identifier: LGPL-3.0-or-later
"""Flange geometry collaborators (the public class stays in pFeatures)."""

from .builders import (
    BLFlangeBuilder,
    DEFAULT_FLANGE_BUILDER,
    FLANGE_BUILDERS,
    GenericFlangeBuilder,
    LJFlangeBuilder,
    SOFlangeBuilder,
    SWFlangeBuilder,
    WNFlangeBuilder,
    builder_for,
    register_flange_builder,
)
from .primitives import configure_view
from .spec import spec_from_object

__all__ = [
    "BLFlangeBuilder",
    "DEFAULT_FLANGE_BUILDER",
    "FLANGE_BUILDERS",
    "GenericFlangeBuilder",
    "LJFlangeBuilder",
    "SOFlangeBuilder",
    "SWFlangeBuilder",
    "WNFlangeBuilder",
    "builder_for",
    "configure_view",
    "register_flange_builder",
    "spec_from_object",
]
