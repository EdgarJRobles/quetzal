# SPDX-License-Identifier: LGPL-3.0-or-later
"""Flange shape builders selected by ``FlangeType`` at execute time."""

from __future__ import annotations

from typing import Any, Dict, Protocol

import FreeCAD

from ...domain.flange import FlangeSpec
from ..geometry import FeatureGeometry
from . import primitives


def _geometry(shape: Any, spec: FlangeSpec) -> FeatureGeometry:
    return FeatureGeometry(
        shape=shape,
        ports=tuple(FreeCAD.Vector(*point) for point in spec.port_offsets()),
        directions=tuple(FreeCAD.Vector(*direction) for direction in spec.port_directions()),
    )


class FlangeShapeBuilder(Protocol):
    key: str

    def build(self, spec: FlangeSpec) -> FeatureGeometry: ...


class _BaseBuilder:
    key = ""


class SOFlangeBuilder(_BaseBuilder):
    key = "SO"

    def build(self, spec: FlangeSpec) -> FeatureGeometry:
        shape = primitives.body(spec)
        shape = primitives.add_hub_and_raised_face(shape, spec)
        return _geometry(shape, spec)


class WNFlangeBuilder(_BaseBuilder):
    key = "WN"

    def build(self, spec: FlangeSpec) -> FeatureGeometry:
        shape = primitives.body(spec)
        shape = primitives.add_hub_and_raised_face(shape, spec)
        shape = primitives.add_weld_neck(shape, spec)
        return _geometry(shape, spec)


class SWFlangeBuilder(_BaseBuilder):
    key = "SW"

    def build(self, spec: FlangeSpec) -> FeatureGeometry:
        shape = primitives.body(spec)
        shape = primitives.add_hub_and_raised_face(shape, spec)
        shape = primitives.add_socket(shape, spec)
        return _geometry(shape, spec)


class LJFlangeBuilder(_BaseBuilder):
    key = "LJ"

    def build(self, spec: FlangeSpec) -> FeatureGeometry:
        shape = primitives.body(spec)
        shape = primitives.add_hub_and_raised_face(shape, spec)
        shape = primitives.add_lap_joint(shape, spec)
        return _geometry(shape, spec)


class BLFlangeBuilder(_BaseBuilder):
    key = "BL"

    def build(self, spec: FlangeSpec) -> FeatureGeometry:
        shape = primitives.body(spec)
        shape = primitives.add_solid_raised_face(shape, spec)
        return _geometry(shape, spec)


class GenericFlangeBuilder(_BaseBuilder):
    """Unknown/legacy type: flat disc with the legacy port fallback."""

    key = "generic"

    def build(self, spec: FlangeSpec) -> FeatureGeometry:
        return _geometry(primitives.body(spec), spec)


FLANGE_BUILDERS: Dict[str, FlangeShapeBuilder] = {
    builder.key: builder
    for builder in (
        SOFlangeBuilder(),
        WNFlangeBuilder(),
        SWFlangeBuilder(),
        LJFlangeBuilder(),
        BLFlangeBuilder(),
    )
}
DEFAULT_FLANGE_BUILDER: FlangeShapeBuilder = GenericFlangeBuilder()


def register_flange_builder(
    flange_type: str, builder: FlangeShapeBuilder, replace: bool = False
) -> FlangeShapeBuilder:
    if flange_type in FLANGE_BUILDERS and not replace:
        raise ValueError(f"Flange builder {flange_type!r} is already registered")
    FLANGE_BUILDERS[flange_type] = builder
    return builder


def builder_for(flange_type: str) -> FlangeShapeBuilder:
    return FLANGE_BUILDERS.get(flange_type, DEFAULT_FLANGE_BUILDER)
