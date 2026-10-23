# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the feature registry and insertion use case."""

from __future__ import annotations

import pytest

from quetzal.application.feature_registry import (
    FeatureDefinition,
    FeatureRegistry,
)
from quetzal.application.insertion import FeatureInserter, InMemoryDocument
from quetzal.domain.errors import FeatureRegistrationError
from quetzal.domain.ports import Vec3


class FakeProxy:
    def __init__(self, obj, rating, *properties):
        obj.rating = rating
        obj.properties = properties


def definition(**overrides):
    values = dict(
        key="Pipe",
        proxy=FakeProxy,
        label="Tube",
        icon="Quetzal_InsertPipe",
        accepted_prop_counts=(4,),
    )
    values.update(overrides)
    return FeatureDefinition(**values)


def test_definition_validates_required_fields():
    with pytest.raises(FeatureRegistrationError):
        definition(key="")
    with pytest.raises(FeatureRegistrationError):
        definition(label="")
    with pytest.raises(FeatureRegistrationError):
        definition(icon="")


def test_registry_rejects_duplicates():
    registry = FeatureRegistry()
    registry.register(definition())
    with pytest.raises(FeatureRegistrationError):
        registry.register(definition())
    registry.register(definition(), replace=True)
    assert len(registry) == 1


def test_registry_unknown_key_lists_known_features():
    registry = FeatureRegistry()
    registry.register(definition())
    with pytest.raises(KeyError) as exc:
        registry.get("Cap")
    assert "Pipe" in str(exc.value)


def test_proxy_gets_properties_only_for_declared_counts():
    defn = definition()
    document = InMemoryDocument()
    inserter = FeatureInserter(document)

    with_props = inserter.insert(defn, "SCH-40", [1, 2, 3, 4])
    assert with_props.properties == (1, 2, 3, 4)

    without_props = inserter.insert(defn, "SCH-40", [1, 2])
    assert without_props.properties == ()  # fallback to proxy defaults


def test_inserter_places_labels_and_attaches_view():
    document = InMemoryDocument()
    inserter = FeatureInserter(document, label_translator=lambda text: f"T:{text}")
    obj = inserter.insert(
        definition(),
        "SCH-40",
        properties=(1, 2, 3, 4),
        position=Vec3(10, 20, 30),
        direction=Vec3(0, 1, 0),
    )

    assert document.created == [("Part::FeaturePython", "Pipe")]
    assert obj.Label == "T:Tube"
    assert document.views == [(obj, "Quetzal_InsertPipe")]
    assert document.placements == [
        (obj, Vec3(10, 20, 30), Vec3(0, 1, 0), Vec3(0, 0, 1))
    ]
