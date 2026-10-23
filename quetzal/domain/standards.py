# SPDX-License-Identifier: LGPL-3.0-or-later
"""International standards metadata and unit-aware catalogue classification.

Quetzal ships hundreds of catalogue files whose names encode a family, a
standard/rating and sometimes a connection type.  Instead of scattering those
rules through the UI, this module treats them as data:

* institutions (ASME, DIN, ISO, EN, API, ASTM, MSS, SMACNA, ...);
* standards documents (ASME B16.5, DIN 2543, EN 1092-1, ...);
* dimensions with an explicit unit and description;
* classification rules that map ``Family_Rating.csv`` to a standard;
* conversion of a CSV row to canonical units (mm, kg, bar, °, N·m).

Adding a new standard or catalogue family is a metadata change, not a code
change (Open/Closed Principle).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Tuple

from .nominal_sizes import canonical as canonical_nominal_size
from .errors import StandardsError
from .units import (
    DIMENSIONLESS,
    NOMINAL,
    TEXT,
    Unit,
    canonical_unit,
    convert,
    parse_unit,
)


class UnknownCatalogueFamily(StandardsError):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"No catalogue family matches {filename!r}")


@dataclass(frozen=True)
class Institution:
    code: str
    name: str
    region: str = ""
    website: str = ""
    description: str = ""


@dataclass(frozen=True)
class Standard:
    code: str
    institution: str
    title: str
    scope: str = ""
    edition: str = ""
    notes: str = ""
    related: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DimensionSpec:
    name: str
    unit: Unit
    description: str = ""
    aliases: Tuple[str, ...] = ()
    required: bool = False

    def normalize(self, value: Any, source_unit: Optional[Unit] = None) -> Any:
        """Convert a raw catalogue value to its canonical unit."""

        if value is None or (isinstance(value, str) and not value.strip()):
            return value
        if self.unit.dimension == NOMINAL:
            return canonical_nominal_size(str(value))
        if self.unit.dimension == TEXT:
            return value
        if self.unit.dimension == DIMENSIONLESS:
            try:
                number = float(value)
            except (TypeError, ValueError):
                return value
            return int(number) if number.is_integer() else number
        source = source_unit or self.unit
        if source.dimension != self.unit.dimension:
            raise StandardsError(
                f"Dimension {self.name!r} expects {self.unit.dimension}, got {source.dimension}"
            )
        target = canonical_unit(self.unit.dimension)
        return convert(float(value), source, target)


@dataclass(frozen=True)
class SeriesRule:
    pattern: str
    standard: str
    fields: Mapping[str, str] = field(default_factory=dict)
    notes: str = ""

    def match(self, rating: str) -> Optional[Dict[str, str]]:
        match = re.match(self.pattern, rating)
        if match is None:
            return None
        values = dict(self.fields)
        values.update({key: value for key, value in match.groupdict().items() if value})
        return values


@dataclass(frozen=True)
class StandardSeries:
    family: str
    rating: str
    standard: str
    institution: str
    pressure_class: str = ""
    connection: str = ""
    face: str = ""
    notes: str = ""
    classification: str = "mapped"
    length_unit: str = "mm"
    unit_overrides: Mapping[str, str] = field(default_factory=dict)
    file: str = ""

    def unit_for(self, dimension: DimensionSpec) -> Unit:
        override = self.unit_overrides.get(dimension.name)
        return parse_unit(override) if override else dimension.unit


@dataclass(frozen=True)
class FamilySpec:
    name: str
    prefix: str
    description: str = ""
    dimensions: Tuple[DimensionSpec, ...] = ()
    rules: Tuple[SeriesRule, ...] = ()
    series: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    headerless_columns: Tuple[str, ...] = ()
    fallback_standard: str = "QUETZAL-GENERIC"
    _by_name: Mapping[str, DimensionSpec] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        lookup: Dict[str, DimensionSpec] = {}
        for dimension in self.dimensions:
            lookup[dimension.name.lower()] = dimension
            for alias in dimension.aliases:
                lookup[alias.lower()] = dimension
        object.__setattr__(self, "_by_name", MappingProxyType(lookup))

    def dimension(self, column: str) -> Optional[DimensionSpec]:
        return self._by_name.get(str(column).strip().lower())

    def columns(self) -> Tuple[str, ...]:
        return tuple(dimension.name for dimension in self.dimensions)


class StandardsRepository(Protocol):
    def load(self) -> "StandardsCatalog":
        """Return the standards catalogue."""


class StandardsCatalog:
    """Validated, queryable standards metadata."""

    def __init__(
        self,
        institutions: Mapping[str, Institution],
        standards: Mapping[str, Standard],
        families: Mapping[str, FamilySpec],
        schema_version: int = 1,
    ) -> None:
        self.schema_version = schema_version
        self.institutions = MappingProxyType(dict(institutions))
        self.standards = MappingProxyType(dict(standards))
        self.families = MappingProxyType(dict(families))
        self._validate()

    # ------------------------------------------------------------------ load
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StandardsCatalog":
        if not isinstance(data, Mapping):
            raise StandardsError("Standards metadata must be a JSON object")
        version = int(data.get("schema_version", 0))
        if version != 1:
            raise StandardsError(f"Unsupported standards schema version: {version!r}")

        institutions: Dict[str, Institution] = {}
        for item in data.get("institutions", []):
            institution = Institution(
                code=str(item["code"]).strip(),
                name=str(item["name"]).strip(),
                region=str(item.get("region", "")),
                website=str(item.get("website", "")),
                description=str(item.get("description", "")),
            )
            if institution.code in institutions:
                raise StandardsError(f"Duplicate institution {institution.code!r}")
            institutions[institution.code] = institution

        standards: Dict[str, Standard] = {}
        for item in data.get("standards", []):
            standard = Standard(
                code=str(item["code"]).strip(),
                institution=str(item["institution"]).strip(),
                title=str(item["title"]).strip(),
                scope=str(item.get("scope", "")),
                edition=str(item.get("edition", "")),
                notes=str(item.get("notes", "")),
                related=tuple(item.get("related", ())),
            )
            if standard.code in standards:
                raise StandardsError(f"Duplicate standard {standard.code!r}")
            standards[standard.code] = standard

        dimensions: Dict[str, DimensionSpec] = {}
        for name, item in data.get("dimensions", {}).items():
            dimensions[name] = DimensionSpec(
                name=name,
                unit=parse_unit(str(item.get("unit", "mm"))),
                description=str(item.get("description", "")),
                aliases=tuple(item.get("aliases", ())),
                required=bool(item.get("required", False)),
            )

        families: Dict[str, FamilySpec] = {}
        for name, item in data.get("families", {}).items():
            dimension_names = item.get("dimensions", [])
            family_dimensions = []
            for dimension_name in dimension_names:
                if dimension_name not in dimensions:
                    raise StandardsError(
                        f"Family {name!r} references unknown dimension {dimension_name!r}"
                    )
                family_dimensions.append(dimensions[dimension_name])
            rules = tuple(
                SeriesRule(
                    pattern=str(rule["match"]),
                    standard=str(rule.get("standard", "QUETZAL-GENERIC")),
                    fields=MappingProxyType(dict(rule.get("fields", {}))),
                    notes=str(rule.get("notes", "")),
                )
                for rule in item.get("rules", [])
            )
            family = FamilySpec(
                name=name,
                prefix=str(item.get("prefix", name)),
                description=str(item.get("description", "")),
                dimensions=tuple(family_dimensions),
                rules=rules,
                series=MappingProxyType(
                    {
                        str(rating): MappingProxyType(dict(values))
                        for rating, values in item.get("series", {}).items()
                    }
                ),
                headerless_columns=tuple(item.get("headerless_columns", ())),
                fallback_standard=str(item.get("fallback_standard", "QUETZAL-GENERIC")),
            )
            if family.name in families:
                raise StandardsError(f"Duplicate family {family.name!r}")
            families[family.name] = family

        return cls(institutions, standards, families, version)

    @classmethod
    def from_json(cls, path: "str | Path") -> "StandardsCatalog":
        path = Path(path)
        try:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            raise StandardsError(f"Standards metadata not found: {path}") from None
        except json.JSONDecodeError as exc:
            raise StandardsError(f"Invalid standards JSON in {path}: {exc}") from exc
        return cls.from_dict(data)

    # -------------------------------------------------------------- validate
    def _validate(self) -> None:
        for standard in self.standards.values():
            if standard.institution not in self.institutions:
                raise StandardsError(
                    f"Standard {standard.code!r} references unknown institution "
                    f"{standard.institution!r}"
                )
        for family in self.families.values():
            for rule in family.rules:
                try:
                    re.compile(rule.pattern)
                except re.error as exc:
                    raise StandardsError(
                        f"Family {family.name!r} has invalid rule {rule.pattern!r}: {exc}"
                    ) from exc
                if rule.standard not in self.standards:
                    raise StandardsError(
                        f"Family {family.name!r} references unknown standard {rule.standard!r}"
                    )
            for rating, values in family.series.items():
                code = values.get("standard", family.fallback_standard)
                if code not in self.standards:
                    raise StandardsError(
                        f"Family {family.name!r} series {rating!r} references "
                        f"unknown standard {code!r}"
                    )

    # ---------------------------------------------------------------- lookup
    def institution(self, code: str) -> Institution:
        try:
            return self.institutions[code]
        except KeyError:
            raise StandardsError(f"Unknown institution: {code!r}") from None

    def standard(self, code: str) -> Standard:
        try:
            return self.standards[code]
        except KeyError:
            raise StandardsError(f"Unknown standard: {code!r}") from None

    def family(self, name: str) -> FamilySpec:
        try:
            return self.families[name]
        except KeyError:
            raise UnknownCatalogueFamily(name) from None

    def dimension(self, family: str, column: str) -> Optional[DimensionSpec]:
        return self.family(family).dimension(column)

    def series(self, family: str, rating: str) -> StandardSeries:
        family_spec = self.family(family)
        if rating in family_spec.series:
            values = dict(family_spec.series[rating])
        else:
            values = None
            for rule in family_spec.rules:
                matched = rule.match(rating)
                if matched is not None:
                    values = matched
                    values["standard"] = rule.standard
                    values.setdefault("notes", rule.notes)
                    break
            if values is None:
                values = {
                    "standard": family_spec.fallback_standard,
                    "notes": "No specific standard mapping; vendor/generic data.",
                }
        code = values.get("standard", family_spec.fallback_standard)
        standard = self.standard(code)
        return StandardSeries(
            family=family_spec.name,
            rating=rating,
            standard=standard.code,
            institution=standard.institution,
            pressure_class=str(values.get("pressure_class", "")),
            connection=str(values.get("connection", "")),
            face=str(values.get("face", "")),
            notes=str(values.get("notes", "")),
            classification="mapped" if code != family_spec.fallback_standard else "generic",
            length_unit=str(values.get("length_unit", "mm")),
            unit_overrides=MappingProxyType(dict(values.get("unit_overrides", {}))),
            file=(f"{family_spec.prefix}_{rating}.csv" if rating else f"{family_spec.prefix}.csv"),
        )

    def series_for_file(self, filename: "str | Path") -> StandardSeries:
        name = Path(filename).name
        stem = name[:-4] if name.lower().endswith(".csv") else name
        candidates = [
            family
            for family in self.families.values()
            if stem == family.prefix or stem.startswith(family.prefix + "_")
        ]
        if not candidates:
            raise UnknownCatalogueFamily(name)
        family = max(candidates, key=lambda item: len(item.prefix))
        rating = stem[len(family.prefix) + 1 :] if len(stem) > len(family.prefix) else ""
        return self.series(family.name, rating)

    # ------------------------------------------------------------ normalise
    def normalize_row(self, filename: "str | Path", row: Mapping[str, Any]) -> Dict[str, Any]:
        """Return ``row`` with all recognized dimensions converted to canonical units."""

        series = self.series_for_file(filename)
        family = self.family(series.family)
        result: Dict[str, Any] = {}
        for column, value in row.items():
            dimension = family.dimension(column)
            if dimension is None:
                result[column] = value
                continue
            result[dimension.name] = dimension.normalize(
                value, source_unit=series.unit_for(dimension)
            )
        return result

    def dimensions_for(self, family: str) -> Tuple[DimensionSpec, ...]:
        return self.family(family).dimensions

    def validate_files(self, filenames: Iterable["str | Path"]) -> List[str]:
        """Return human-readable issues for catalogue files that cannot be classified."""

        issues = []
        for filename in filenames:
            name = Path(filename).name
            try:
                series = self.series_for_file(name)
            except UnknownCatalogueFamily:
                issues.append(f"{name}: no matching catalogue family")
                continue
            if series.file != name:
                issues.append(f"{name}: classified as {series.file}")
        return issues


class JsonStandardsRepository:
    """Load a :class:`StandardsCatalog` from a JSON file, with caching."""

    def __init__(self, path: "str | Path") -> None:
        self._path = Path(path)
        self._catalog: Optional[StandardsCatalog] = None

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> StandardsCatalog:
        if self._catalog is None:
            self._catalog = StandardsCatalog.from_json(self._path)
        return self._catalog
