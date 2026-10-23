# Standards metadata

`catalog.json` is the machine-readable description of the international
standards used by the bundled `tablez/` catalogues.

## Contents

- `schema_version` — currently `1`.
- `institutions` — issuing bodies (ASME, DIN, ISO, EN, API, ASTM, MSS, SMACNA,
  QUETZAL).
- `standards` — document code, institution, title, scope and notes.
- `dimensions` — every catalogue column with its unit, description and
  aliases.
- `families` — catalogue prefix, dimensions, series overrides and ordered
  regex rules that map a rating to a standard.

## Rules

- **Explicit `series` entries win** over regex rules.
- Rules are evaluated in array order; put specific patterns before generic
  ones.
- A family fallback is `QUETZAL-GENERIC` unless `fallback_standard` overrides
  it.
- `headerless_columns` lists field names for CSV files without a header row
  (currently `Union`).
- `unit_overrides` on a series can change the unit of individual dimensions
  when a table is not in millimetres.

## Validation

`StandardsCatalog.from_json()` rejects:

- unsupported schema versions;
- duplicate institution or standard codes;
- standards referencing unknown institutions;
- dimensions/families using unknown units or dimensions;
- rules or series referencing unknown standards;
- invalid regular expressions.

`StandardsCatalog.validate_files()` additionally verifies that every CSV in
`tablez/` resolves to a family and that the computed filename matches the real
one.

The unit tests read every bundled CSV header and require each non-empty column
to map to a declared dimension. Add a dimension before adding a CSV column.

## Updating a standard

1. Edit `catalog.json`.
2. Keep institutions/standards codes stable; they are referenced by rules.
3. Run `python3 -m pytest tests/unit/test_domain_standards.py`.
4. Run `freecadcmd tests/integration/freecad_check.py`.

See [the standards and units guide](../docs/architecture/standards-and-units.md)
for the design rationale.
