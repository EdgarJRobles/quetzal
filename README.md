# Quetzal Workbench

[![Contributions welcome][ContribsW_badge]][CONTRIBUTING]
[![license][license_badge]][LICENSE]
[![FreeCAD Addon Manager][AddonMgr_badge]][AddonMgr]
[![pre-commit enabled][pre-commit_badge]][pre-commit]
[![Code style: black][black_badge]][black]
[![GitHub Tag][tag_bagde]][tag]
[![Common Changelog][cc_badge]][CHANGELOG]

Quetzal is the fork of Dodo workbench for [FreeCAD](https://freecad.org).
Extending Dodo workbench support & adding translation support.
![screenshot1](https://github.com/user-attachments/assets/70e96920-34db-40d9-a8d6-102e690a13ee "Metal frame created with Quetzal")
![Piping example](https://github.com/user-attachments/assets/0631e4df-e733-403d-8949-fb6a21e2742d)



## Installation

### Automatic Installation

The recommended way to install Quetzal is via FreeCAD's
[Addon Manager](https://wiki.freecad.org/Std_AddonMgr) under
`Tools > Addon Manager` drop-down menu.

Search for **Quetzal** in the workbench category.

### Manual installation

The install path for FreeCAD modules depends on the operating system used.

To find where is the user's application data directory enter next command on
FreeCAD's Python console.

```python
App.getUserAppDataDir()
```

Examples on different OS

- Linux: `/home/user/.local/share/FreeCAD/Mod/`
- macOS: `/Users/user/Library/Preferences/FreeCAD/Mod/`
- Windows: `C:\Users\user\AppData\Roaming\FreeCAD\Mod\`

Use the CLI to enter the `Mod` directory and use Git to install Quetzal:

```shell
git clone https://github.com/EdgarJRobles/quetzal Quetzal
```

If you are updating the code, restarting FreeCAD is advised.

## Usage

Check the documentation on the FreeCAD Wiki article:
<https://wiki.freecad.org/Quetzal_Workbench>

Wiki for older Dodo and Flamingo versions of the workbench
<https://wiki.freecad.org/Dodo_Workbench>

Discussion in the FreeCAD Forum:
<https://forum.freecad.org/viewtopic.php?t=22711>

[Drawings 2D nomeclature of tablez CVS]: ./Nomeclature.md

## Architecture

Quetzal now has a layered core under `quetzal/` (domain, application,
infrastructure and features) while keeping the historical `pFeatures`/`pCmd`
API for existing documents and macros. International standards, dimensions and
units are described in `standards/catalog.json` and exposed through
`quetzal.domain.standards`. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the
dependency rules, the standards layer and the migration roadmap.

Run the fast tests with `python3 -m pytest`. For the headless FreeCAD checks:

```shell
freecadcmd tests/integration/freecad_check.py
```

## Extending Quetzal without breaking SOLID

Quetzal separates four kinds of change. Put each change in the right layer;
most new standards and catalogue entries do not need Python code at all.

| Change | Where it belongs | Normally needs code? |
|---|---|---|
| New institution or standard | `standards/catalog.json` | No |
| New size, schedule, pressure class or series | `tablez/*.csv` + a family rule in `standards/catalog.json` | No |
| New dimension/column | `standards/catalog.json` (`dimensions` + family `dimensions`) | No |
| New variant of an existing geometry (flange face, elbow type, tee type, reducer type) | pure builder/strategy under `quetzal/features/` | Yes, small |
| New feature family (new `PType`) | domain value + feature proxy + `FeatureDefinition` + insertion/UI adapters | Yes |
| New dialog/command | `quetzal/ui/forms.py` + `quetzal/ui/layout.py` + a `FormSpec` | Yes, UI only |

The dependency rule is: **domain/application do not import FreeCAD; UI does not
call `pCmd`; persistence adapters stay thin.** See
[ARCHITECTURE.md](./ARCHITECTURE.md) for the full boundary rules.

### 1. Add an institution or standard

Edit `standards/catalog.json`. An institution is just metadata:

```json
{
  "code": "NF",
  "name": "Association francaise de normalisation",
  "region": "FR",
  "website": "https://www.afnor.org",
  "description": "French mechanical and piping standards."
}
```

A standard points at that institution:

```json
{
  "code": "NF E 29-211",
  "institution": "NF",
  "title": "Industrial valves - Steel gate valves",
  "scope": "valves",
  "notes": "Pressure classes and face-to-face dimensions."
}
```

Then add a rule to the relevant family in `families`. Rules are regular
expressions over the rating part of the CSV filename:

```json
{
  "match": "^NF-(?P<pressure_class>[0-9]+)$",
  "standard": "NF E 29-211",
  "notes": "NF steel valve"
}
```

`quetzal.domain.standards` validates the file, and the pipe/frame dialogs pick
up the new institution/standard automatically through `StandardFilterService`
and `CatalogPresenter`. Do not add institution-specific `if` branches to the
forms.

### 2. Add a size, schedule or pressure class

Add a CSV under `tablez/` following the historical filename convention:

```text
tablez/Flange_NF-16.csv
tablez/Valve_NF-40-Gate.csv
tablez/Pipe_SCH-200.csv
```

The part after the first `_` is the rating shown in the UI. Every column must
exist in `standards/catalog.json` under `dimensions`, and the family must list
it in its `dimensions` array. Run:

```shell
python3 -m pytest tests/unit/test_domain_standards.py
```

If the CSV introduces a new column, add a dimension entry first:

```json
"F2": {
  "unit": "mm",
  "description": "Secondary face dimension"
}
```

Do not parse CSV files inside a dialog. `CatalogPresenter` and
`SectionCatalogPresenter` are the only UI-facing readers; they return
`RatingOption`/`SizeOption` values.

### 3. Add a flange, elbow, tee or reducer variant

A new **variant of an existing family** is a new strategy/builder, not a new
`if` in a form or in `pCmd`.

- Flanges: add a `FlangeShapeBuilder` in
  `quetzal/features/flange/builders.py` and register it with
  `register_flange_builder("NF", NFBuilder)`. Keep `FlangeSpec` as the pure
  input; do not read FreeCAD properties inside the builder.
- Elbows, tees, reducers: add a builder/strategy next to the existing feature
  module (`quetzal/features/elbow.py`, `tee.py`, `reduct.py`) and make it
  implement the same minimal proxy contract (`PType`, `Ports`,
  `PortDirections`, `execute`).
- Valve variants: add a strategy under `quetzal/features/valve/` instead of
  extending a central `if VType == ...` chain.

For a completely new family, declare it once:

```python
from quetzal.application.feature_registry import FEATURES, FeatureDefinition
from quetzal.features.my_feature import MyFeature

FEATURES.register(
    FeatureDefinition(
        key="MyFeature",
        proxy=MyFeature,
        label="My feature",
        icon="Quetzal_MyFeature",
        accepted_prop_counts=(4, 6),
    )
)
```

Then add a thin compatibility adapter only where the legacy API needs it
(`pFeatures` alias and `pCmd.make...`). Do not copy the geometry into both
layers. Keep the proxy class/module path stable: FreeCAD stores it in `.FCStd`
documents, so renaming or moving an existing proxy requires a migration.

### 4. Add a dialog or command

Forms receive `FormServices` and never import `pCmd` or catalogue singletons:

```python
class InsertMyFeatureForm(dodoDialogs.protoPypeForm):
    def __init__(self, services=None):
        super().__init__(..., services=services)
        self._validator = FormValidator(
            (FieldRule("length", "Length", required=True, kind="number", minimum=0.1),)
        )
```

Register the dialog once:

```python
# quetzal/ui/forms.py
("Quetzal_InsertMyFeature", "pForms:insertMyFeatureForm", "pipe"),
```

Add it to the toolbar/menu in `quetzal/ui/layout.py`:

```python
"Quetzal_InsertMyFeature",
```

The command is then resolved lazily by `open_form`; do not add a new command
class with duplicated `IsActive`/`GetResources`. If the command is not a
dialog, register a `CommandSpec` with a module-level handler instead.

### 5. Tests to add

- `tests/unit/` for pure rules: standards classification, builders, validator,
  presenters, feature registry.
- `tests/integration/freecad_check.py` for real FreeCAD geometry: shape
  validity, ports, property persistence and `.FCStd` reload.
- A new baseline only when geometry is intentionally changed; never update a
  baseline to hide a regression.

### SOLID checklist

- **SRP**: CSV parsing in presenters, geometry in builders, orchestration in
  application services, widgets only render.
- **OCP**: add a registry entry/strategy; do not edit long `if/elif` chains.
- **LSP**: every feature proxy exposes the same `PType`/`Ports`/
  `PortDirections`/`execute` contract.
- **ISP**: inject only the services a form needs (`FormServices`); keep ports
  small (`UserReporter`, `PipeInserter`, `FittingInserter`).
- **DIP**: forms and commands depend on protocols/services, not on concrete
  `pCmd`, `pFeatures` or FreeCAD globals.

## Changelog

Read our [CHANGELOG] file to know about the latest changes.

## Contributing

Read our [CONTRIBUTING] file to know about ways how to help on the workbench.

## Roadmap
Here are some of the planned developments for this Workbench:

- [ ] Icrease valve design detail
- [ ] Add HVAC duct support.
  - [X] Elbow (rectangular)
  - [X] Reduction (rectangular)
  - [ ] Branch — SMACNA HVAC metadata ready; geometry pending
  - [ ] Round duct — SMACNA HVAC metadata ready; geometry pending
  - [ ] Square duct — SMACNA HVAC metadata ready; geometry pending
  - [ ] Oval duct — SMACNA HVAC metadata ready; geometry pending
- [ ] Support, if possible, fitting & frame profiles types:
  - [X] Pipe
  - [X] Elbow
  - [X] Cap
  - [X] Gasket
  - [X] Reduction
  - [X] Coupling
  - [X] Flange
  - [ ] Valve
    - [X] Gate Valve
    - [X] Plug Valve
    - [X] Ball Valve
    - [X] Check Valve
    - [X] Globe Valve
    - [X] Butterfly Valve
    - [ ] Needle Valve — ASME B16.34 metadata ready; catalogue data pending
    - [X] Knife gate Valve
    - [X] Pinch Valve
  - [ ] Pipe Clamping
    - [X] U-bolt clamp (DIN 3570)
    - [X] Beam clamp (MSS SP-58)
  - [ ] Beam joins — AISC 360 catalog metadata ready; connection geometry pending
- [ ] Support, if possible, International design standards:
  - [X] ASME B16.5 (NPS 1/2 to 24")
  - [ ] ASME B16.47 (NPS 26 to 60") — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ASME B16.36 (orifice flange) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] DIN 2527 (blind flange) — catalog metadata and rules ready; dimensional CSV pending
  - [X] DIN 2543 PN16 (flat face for welding slip-on flange)
  - [ ] DIN 2544 PN25 (flat face for welding slip-on flange) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] DIN 2545 PN40 (flat face for welding slip-on flange) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ISO 7005-1 PN10 Raised Face (EN 1092-1 equivalent) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ISO 7005-1 PN16 Raised Face (EN 1092-1 equivalent) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ISO 7005-1 PN25 Raised Face (EN 1092-1 equivalent) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ISO 7005-1 PN40 Raised Face (EN 1092-1 equivalent) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ISO 7005-1 PN64 Raised Face (EN 1092-1 equivalent) — catalog metadata and rules ready; dimensional CSV pending
  - [ ] ISO 7005-1 PN100 Raised Face (EN 1092-1 equivalent) — catalog metadata and rules ready; dimensional CSV pending

Valve standards are mapped by type: `API 594` for check valves, `API 599` for
plug valves, `API 609` for butterfly valves, `MSS SP-81` for knife gate valves
and `ASME B16.34` for the remaining pressure-temperature/body classifications.

## Links

- [FreeCAD Site main page](https://www.freecad.org/)

- [FreeCAD Wiki main page](https://www.freecad.org/wiki)

- [FreeCAD Repository](https://github.com/FreeCAD/FreeCAD)

[CONTRIBUTING]: ./CONTRIBUTING.md
[ContribsW_badge]: <https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat>
[LICENSE]: ./LICENSE
[license_badge]: <https://img.shields.io/github/license/EdgarJRobles/quetzal>
[AddonMgr]: <https://github.com/FreeCAD/FreeCAD-addons>
[AddonMgr_badge]: <https://img.shields.io/badge/FreeCAD%20addon%20manager-available-brightgreen>
[pre-commit]: <https://github.com/pre-commit/pre-commit>
[pre-commit_badge]: <https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit>
[black]: <https://github.com/psf/black>
[black_badge]: <https://img.shields.io/badge/code%20style-black-000000.svg>
[tag]: <https://github.com/EdgarJRobles/quetzal/releases>
[tag_bagde]: <https://img.shields.io/github/v/tag/EdgarJRobles/quetzal>
[cc_badge]: <https://common-changelog.org/badge.svg>
[CHANGELOG]: ./CHANGELOG.md
