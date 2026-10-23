# International standards and units

Quetzal's catalogue data comes from several standards families and is stored in
CSV files whose dimensions are expressed in different units. This layer makes
that explicit and extensible.

## Why a separate layer?

Before this change:

- the outside-diameter table was duplicated in `pFeatures.py` and `pForms.py`;
- the DN/NPS mapping lived in the Qt preferences module;
- every dialog opened its own CSV and assumed millimetres;
- there was no machine-readable record that `Flange_ASME-WN-RF-150lb.csv`
  belongs to ASME B16.5 or that a gasket table belongs to ASME B16.20.

The new layer answers three questions in one place:

1. **Which institution and standard does this catalogue belong to?**
2. **What does each column mean, and in which unit is it expressed?**
3. **How do I convert it to the canonical unit used by the geometry code?**

## Layers

| Layer | Module | Responsibility |
| --- | --- | --- |
| Domain | `quetzal/domain/units.py` | `Unit`, `Quantity`, conversions, canonical units (mm, kg, bar, °, N·m). |
| Domain | `quetzal/domain/nominal_sizes.py` | DN/NPS identities and ISO 6708 lookup. DN/NPS are *not* a unit conversion. |
| Domain | `quetzal/domain/standards.py` | Institutions, standards, dimensions and series rules; JSON loader; row normalisation. |
| Infrastructure | `quetzal/infrastructure/standards.py` | Repository rooted at `<addon>/standards/catalog.json`. |
| Data | `standards/catalog.json` | Institutions, standards, dimensions, families and classification rules. |
| UI compatibility | `quetzal_units.py` | Existing preference and label helpers now use the domain DN/NPS map. |

The domain layer imports no FreeCAD, Qt or filesystem APIs, so the whole
standards model is testable with plain `pytest`.

## Institutions

`standards/catalog.json` currently declares:

| Code | Institution | Region |
| --- | --- | --- |
| ASME | American Society of Mechanical Engineers | US |
| ANSI | American National Standards Institute | US |
| API | American Petroleum Institute | US |
| ASTM | ASTM International | US |
| DIN | Deutsches Institut für Normung | DE |
| EN | European Committee for Standardization (CEN) | EU |
| ISO | International Organization for Standardization | INT |
| MSS | Manufacturers Standardization Society | US |
| SMACNA | Sheet Metal and Air Conditioning Contractors' National Association | US |
| QUETZAL | Quetzal generic/vendor catalogue | INT |

Each institution has a name, a region, an optional website and a description.

## Standards

The metadata includes the document code, issuing institution, title, scope and
notes. Examples:

- **ASME B16.5** — pipe flanges NPS 1/2–24, pressure classes 150–2500 lb.
- **ASME B16.9** — buttweld fittings (elbows, tees, caps, reducers).
- **ASME B16.11** — forged socket-weld/threaded fittings (3000/6000/9000 lb).
- **ASME B36.10M / B36.19M** — carbon and stainless steel pipe schedules.
- **ASME B16.34** — valve pressure-temperature and body dimensions.
- **API 6D / API 608** — pipeline and threaded metal ball valves.
- **DIN 1626 / 2527 / 2543 / 2544 / 2545** — DIN pipe and flange families.
- **EN 1092-1 / EN 10365** — PN flanges and hot-rolled sections.
- **ISO 6708 / ISO 7005-1** — DN definition and metallic flanges.
- **ASTM A6 / A615** — structural shapes and reinforcement bars.
- **MSS SP-97** — integrally reinforced branch outlets.
- **SMACNA HVAC** — rectangular duct construction.
- **QUETZAL-GENERIC** — vendor/generic data without a single applicable standard.

`ASME B16.47` is included for completeness even though the bundled tables stop
at NPS 24.

## Dimensions and units

Every dimension has a name, a unit and a description. Units are grouped by
dimension so conversions are type-safe:

| Dimension | Canonical unit | Examples |
| --- | --- | --- |
| length | mm | OD, thk, D, t, C, BendRadius |
| mass | kg | flange `kg` |
| pressure | bar | future pressure columns |
| angle | ° | `BendAngle`, `Ang` |
| torque | N·m | clamp `TorqueNm` |
| flow coefficient | m³/h/bar | valve `Kv` |
| nominal | DN label | `PSize`, `PSize2`, `PSizeBranch` |
| dimensionless | — | `n` (bolt count) |
| text | — | `Conn`, `VType`, `Material`, `Source` |

Example:

```python
from quetzal.domain.units import IN, MM, convert, quantity

assert convert(2.375, IN, MM) == 60.325
assert str(quantity(60.325, MM)) == "60.325 mm"
```

CSV values are normalised through the series' declared unit. Today all bundled
tables are millimetres, but a future imperial table only needs a
`unit_overrides` entry; no feature code changes.

## Families and classification

| Family | Prefix | Default standard | Notes |
| --- | --- | --- | --- |
| Pipe | `Pipe` | ASME B36.10M | Schedules `5S/10S/40S/80S` use B36.19M; conduit and rebars use generic/ASTM A615. |
| Elbow | `Elbow` | ASME B16.9 | `3000/6000/9000lb_SW` → B16.11; `DIN_1626_90` → DIN 1626. |
| Tee | `Tee` | ASME B16.9 | Socket-weld → B16.11. |
| Cap | `Cap` | ASME B16.9 | Socket-weld → B16.11. |
| Reduct | `Reduct` | ASME B16.9 | |
| Flange | `Flange` | ASME B16.5 | `DIN-PN16` → DIN 2543; `PN16-WN` → EN 1092-1. |
| Valve | `Valve` | ASME B16.34 | Threaded ball → API 608. |
| Gasket | `Gasket` | ASME B16.20 | |
| Bolt | `Bolt` | ASME B18.2.1 | |
| Section | `Section` | EN 10365 | HEA/IPE/UPN; REBARS → ASTM A615. |
| Beam | `Beam` | EN 10365 / ASTM A6 | HEA vs S/W. |
| Clamp | `Clamp` | QUETZAL-GENERIC | Vendor data. |
| Outlet | `Outlet` | MSS SP-97 | |
| Coupling | `Coupling` | ASME B16.11 | |
| Union | `Union` | ASME B16.11 | Headerless CSV; field names are declared in metadata. |
| TerminalAdapter | `TerminalAdapter` | QUETZAL-GENERIC | PVC conduit adapter. |
| DuctElbow | `DuctElbow` | SMACNA HVAC | Rectangular duct. |
| DuctReduction | `DuctReduction` | SMACNA HVAC | Rectangular transition. |
| roughness | `roughness` | QUETZAL-GENERIC | Material roughness table. |

Classification is ordered: explicit `series` entries win, then the first
matching regex rule, then the family fallback. Unknown families raise
`UnknownCatalogueFamily`.

## Metadata schema

```json
{
  "schema_version": 1,
  "institutions": [
    {"code": "ASME", "name": "...", "region": "US", "website": "..."}
  ],
  "standards": [
    {"code": "ASME B16.5", "institution": "ASME", "title": "...", "scope": "flanges"}
  ],
  "dimensions": {
    "OD": {"unit": "mm", "description": "Outside diameter", "aliases": ["od"]}
  },
  "families": {
    "Flange": {
      "prefix": "Flange",
      "dimensions": ["PSize", "D", "d", "..."],
      "rules": [
        {
          "match": "^ASME-(?P<connection>[A-Z]+)-(?P<face>[A-Z]+)-(?P<pressure_class>[0-9]+lb)$",
          "standard": "ASME B16.5",
          "notes": "ASME B16.5 flange"
        }
      ],
      "series": {
        "DIN-PN16": {"standard": "DIN 2543", "pressure_class": "16"}
      },
      "headerless_columns": []
    }
  }
}
```

Validation rejects duplicate institution/standard codes, unknown units,
unknown dimensions, unknown standards in rules/series, invalid regexes and
unsupported schema versions.

## Adding a standard

1. Add the institution (if new) and the standard document to
   `standards/catalog.json`.
2. Add the dimensions with their unit and description.
3. Add the family/rule that maps a filename rating to the standard.
4. Add a unit test in `tests/unit/test_domain_standards.py`.
5. Run `python3 -m pytest` and
   `freecadcmd tests/integration/freecad_check.py`.

No feature, command or dialog code needs to change for a new standard family
that fits an existing dimension set.

## Dialog filters

`StandardFilterService` (in `quetzal/application/standard_filters.py`) turns the
metadata into UI-ready lists. All original catalogue series remain available:

- default **All institutions / All standards** shows the complete original set;
- pipe form: `ASME` (`B36.10M`, `B36.19M`) for `SCH-*`, `ASTM` (`A615`) for
  `REBARS`, and `Quetzal / generic` (`Generic / vendor`) for `Conduit*`;
- frame section/branch forms: `EN` (`EN 10365`) for `HEA`/`IPE`/`UPN`,
  `ASTM` (`A615`) for `REBARS`, and `Quetzal / generic` for `RH`/`TSLOT`;
- frame branch form also keeps the BIM preset ratings when **All** is selected,
  so profile families that only exist in `ArchProfile` are not lost.

Changing the institution refreshes the standard list; changing the standard
refreshes the rating list. The actual CSV data and the insertion commands are
unchanged.

## Compatibility notes

- **DN/NPS are labels, not conversions.** `NPS 2` and `DN50` are related by
  ISO 6708 but the mapping is a lookup, not `inch × 25.4`.
- **Pressure classes are text** (`150lb`, `PN16`), not numeric pressures.
- **Some tables are generic by design.** Vendor clamps, PVC conduit adapters
  and roughness data are explicitly classified as `QUETZAL-GENERIC` rather
  than guessed.
- **The UI keeps its existing `quetzal_units` API.** It now delegates the
  DN/NPS map to the domain, so existing forms and macros are unaffected.
- **Catalogue files remain in `tablez/`.** The standards layer describes them;
  it does not move or rewrite them.

## References

- ASME: <https://www.asme.org>
- DIN: <https://www.din.de>
- ISO: <https://www.iso.org>
- CEN/EN: <https://www.cencenelec.eu>
- API: <https://www.api.org>
- ASTM: <https://www.astm.org>
- MSS: <https://www.mss.org>
- SMACNA: <https://www.smacna.org>
