# SOLID mapping

This page records which concrete changes address each principle, and which
legacy hotspots remain. It is meant to be updated as the migration advances.

## Single Responsibility Principle (SRP)

| Before | After |
| --- | --- |
| `pFeatures.pypeType` registered properties, resolved the nearest port and imported `pCmd`. | `quetzal.features.base.PypeFeature` registers the common contract and uses pure port maths from `quetzal.domain.ports`. |
| `pFeatures.Pipe` mixed property registration, parent-group length adjustment, shape construction and port bookkeeping. | `Pipe` keeps the lifecycle; `PipeShapeBuilder` owns geometry; `PropertySpec` owns property registration; parent-group adjustment is an isolated function. |
| `pFeatures.TerminalAdapter` imported `pCmd` just to build a hexagon. | `TerminalAdapter` uses `quetzal.features.shapes.make_regular_polygon`; geometry is isolated in `TerminalAdapterShapeBuilder`. |
| `pCmd.readTable()` opened files directly. | `CsvCatalogRepository` owns file resolution, encoding, parsing and caching. |
| `pCmd.ViewProvider` lived next to geometry factories. | `quetzal.infrastructure.freecad.view_provider` owns GUI concerns. |
| Every `do*` flow had its own selection/transaction/alignment logic. | Six flows share `_insert_attached()`; the remaining ones are listed in the roadmap. |

## Open/Closed Principle (OCP)

- `FeatureDefinition` + `FeatureRegistry` describe features as data. The
  generic `pCmd.makeFeature(key, ...)` builds any registered feature.
- `PropertySpec` tuples let a feature declare properties without repeating
  `addProperty(...)` code.
- `ShapeBuilder` classes can be replaced on a subclass
  (`shape_builder_class`) without editing `execute()`.
- `VALVE_STRATEGIES` maps each connection/rating mode to a strategy; adding a
  valve variant registers a new strategy instead of growing `Valve.execute`.
- `CatalogRepository` can be swapped (CSV, in-memory, future database) without
  changing consumers.
- `standards/catalog.json` adds institutions, standards, dimensions and series
  rules without touching feature or dialog code.

## Liskov Substitution Principle (LSP)

- All migrated features honour the `PypeFeature` contract: common properties,
  `execute()` lifecycle, `nearestPort()` result shape.
- Legacy classes continue to inherit the same base via the
  `pFeatures.pypeType` alias, so `isinstance`/`super()` behaviour is unchanged.
- The integration suite builds every legacy feature (including ones that do
  not inherit `PypeFeature`, such as `Shell` and `PypeLine2`) and checks the
  documented exceptions instead of assuming a uniform contract.

## Interface Segregation Principle (ISP)

Small protocols replace large implicit contracts:

- `CatalogRepository`: `get_table`, `read_file`, `ratings`, `families`.
- `StandardsRepository`: one `load()` method returning a validated catalogue.
- `DimensionSpec`: one `normalize(value, source_unit)` contract for all units.
- `DocumentPort`: `add_object`, `place`, `attach_view`.
- `ViewFactory`: one `attach(view_object, icon)` method.
- `ShapeBuilder`: one `build(fp)` method.

No consumer is forced to depend on FreeCAD or Qt to use these.

## Dependency Inversion Principle (DIP)

- `FeatureInserter` depends on `DocumentPort`, not on `FreeCAD.ActiveDocument`.
- `FeatureRegistry` stores plain callables; FreeCAD proxies are injected by
  the feature modules.
- `dodoDialogs.protoPypeForm.fillSizes` depends on the catalogue protocol
  instead of opening CSV files.
- Catalogue consumers can depend on `StandardsRepository` rather than on the
  JSON file location; unit conversion is injected through dimension metadata.
- `pFeatures` no longer imports `pCmd` at module scope. The remaining
  behavioural calls (`PypeLine2.update`, `PypeBranch2.redraw`) use local
  imports so importing the feature module no longer loads the command layer.

## Evidence in the test suite

| Check | What it protects |
| --- | --- |
| `tests/unit/test_domain_catalog.py` | Repository parsing, caching, traversal protection, errors. |
| `tests/unit/test_domain_sizes.py` | Single OD table, immutable lookup, port maths. |
| `tests/unit/test_domain_units.py` | Length/mass/pressure/angle conversions and dimension checks. |
| `tests/unit/test_domain_nominal_sizes.py` | DN/NPS identity mapping and display. |
| `tests/unit/test_domain_standards.py` | Metadata validation, 243-file classification, unit normalisation and metadata-only extension. |
| `tests/unit/test_feature_registry.py` | Registry validation, property count fallback, insertion service placement/labels. |
| `tests/integration/freecad_check.py` | 22 feature proxies, 243 catalogues, save/reload, 61 command contracts, 9 headless insertion flows. |

## Known legacy hotspots (not claimed as solved)

1. `Valve` geometry is split, but its property schema is still dynamic and
   construction-dependent.
2. `Flange` still has magic edge indices and GUI code in `execute()`.
3. `PypeLine2`/`PypeBranch2` still resolve children by label/name.
4. Command classes still repeat `IsActive`/`GetResources`; metadata and
   toolbar lists are still split between command modules and `InitGui.py`.
5. Dialog preview code still has two implementations.
6. `doElbow`, `doTees`, `doValves`, the socket flows, `doBeams` and
   `doOutlets` still contain their own insertion pipelines.

The roadmap in [ARCHITECTURE.md](../ARCHITECTURE.md#remaining-roadmap) tracks
these items.
