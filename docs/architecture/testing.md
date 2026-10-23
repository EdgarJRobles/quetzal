# Testing Quetzal

The refactor splits the test suite in two: fast pure-Python tests and a
headless FreeCAD integration script.

## Requirements

- Python 3.8+ with `pytest` for the unit tests.
- FreeCAD 1.0+ in `PATH` (`freecadcmd` or `FreeCADCmd`) for the integration
  checks. The script uses FreeCAD's own bundled Python, so it must be run with
  `freecadcmd`, not with the system interpreter.

## Unit tests

```bash
python3 -m pytest
```

`pytest.ini` limits collection to `tests/unit`. These tests import only
`quetzal.domain` and `quetzal.application`, so they run on any machine, without
FreeCAD or Qt.

What is covered:

- CSV parsing, BOM handling, caching, rating/family discovery and path
  traversal rejection;
- nominal outside-diameter lookups and immutability;
- vector/port math;
- `FeatureDefinition` validation, duplicate registration;
- `FeatureInserter` placement, label translation, view attachment and the
  legacy property-count fallback;
- unit conversions and dimension safety;
- DN/NPS identity parsing and display;
- standards metadata validation, classification of every bundled CSV and
  unit-aware row normalisation.

## Integration checks

```bash
freecadcmd tests/integration/freecad_check.py
```

The script exits with status `1` on the first reporting pass if any check
fails. It runs without a GUI and verifies:

1. **Feature construction** – every legacy proxy plus the migrated `Pipe` and
   `Cap` creates a valid shape and the expected `PType` (with documented
   exceptions for `Shell` and `PypeLine2`).
2. **Compatibility aliases** – `pFeatures.Pipe`, `pFeatures.Cap` and
   `pFeatures.pypeType` still resolve.
3. **Registry** – `FEATURES.get("Pipe"/"Cap")` returns definitions.
4. **Catalogue** – all 243 bundled CSV files load through the repository.
5. **Persistence** – the document is saved, closed, reopened and recomputed;
   proxies and `PType` survive the round-trip.
6. **Command contract** – `CPipe`, `CFrame`, `CUtils` and
   `cut_list.cut_list_commands` register 61 unique commands, every `Pixmap`
   exists, and every command referenced by `InitGui.py` is registered.
7. **Insertion flows** – `doPipes`, `doCaps`, `doTees`, `doFlanges`,
   `doReduct`, `doGaskets`, `doBolts_Nuts`, `doElbow` and `doValves` create
   valid objects with no GUI selection.
8. **Valve/Flange baselines** – 8 Valve modes and 6 Flange types pinned to
   volume, area, bounding box, ports and serialized properties.
9. **Shared-vector stability** – the duct builders must not mutate
   `vO/vX/vY/vZ`.
10. **Standards metadata** – all 243 catalogues resolve to a family, standard
    and institution; dimensions cover every CSV header.
11. **Command registry/layout** – 61 unique commands, 60 listed in groups,
    one macro-only command, every icon exists and every command has a macro
    source.
12. **PypeBranch links** – children are created as `TubesLink`/`CurvesLink`,
    survive a label rename and save/reload, and legacy name lists migrate on
    recompute.
13. **PypeLine group** – parent-group resolution, unique-label fallback,
    `moveToPyLi` membership and safe purge.

### How the script is executed

`freecadcmd` imports the script as a module, so `__name__` is the file stem
rather than `"__main__"`. The entry point accepts both:

```python
if __name__ in ("__main__", os.path.splitext(os.path.basename(__file__))[0]):
    sys.exit(main())
```

### Geometric golden checks

During the migration, `Pipe` and `Cap` were compared against a pre-refactor
snapshot of volume, area, bounding box, ports and properties for default and
custom sizes. The diff was empty. If you change a shape builder, add a similar
snapshot for the affected feature before touching the code.

## Continuous integration

`.github/workflows/tests.yml` runs the unit tests and a byte-compilation check
on every push and pull request. FreeCAD is not installed in CI because the
official packages are large; run the integration script locally or in a
FreeCAD container before releasing.

## Conventions

- Unit tests live in `tests/unit/test_*.py` and must not import FreeCAD.
- Integration helpers live in `tests/integration/` and may import FreeCAD.
- Keep new domain logic free of `FreeCAD`, `Part`, `PySide` and `FreeCADGui`.
- Prefer `InMemoryCatalogRepository` over temporary files in unit tests.
