# Notes for agents working on Quetzal

Lessons from adding the threaded fittings (hex bushings and plugs, threaded
ells, tees, couplings, caps, unions and olets) and the gate, globe and check
valves, and testing them in a live FreeCAD session over MCP. Read this
before adding a component type, a valve or a fitting table.

## Adding a component type

A new PType touches all of these. Missing one usually fails silently: the
part builds but won't insert from the GUI, round-trip through PCF or match
sizes.

| Where | What |
|---|---|
| `tablez/<Family>_<rating>.csv` | Dimension table (see *Tables* below) |
| `pFeatures.py` | Feature class: properties, `execute()`, `Ports`, `PortDirections` |
| `pCmd.py` | `make<Type>()` and `do<Type>()`. Straight two-port and one-port parts can reuse `_makeSocketStraight` / `_doSocketStraight` |
| `pCmd.getSelectedPortDimensions` | Add socket and threaded PTypes so a form preselects the size from the selected port |
| `pForms.py` | Insert form. Socket-style forms reuse `_port2List` / `_port2DictList` / `_uniqueSizeList`, which the base `changeSize` already understands for preview file names |
| `CPipe.py`, `InitGui.py` | Command class, `addCommand(...)`, toolbar/menu list |
| `Quetzal_tooltips.py`, `iconz/` | Tooltip and SVG icon (`ViewProvider` resolves the icon name without `.svg`) |
| `pcf/pcf_map.py` | `KEYWORDS`, `keyword_and_skey`, and `ptype_for` for import. Use `SKEY_PTYPES` when a type shares a PCF keyword with another PType |
| `pcf/pcf_export.py` | Endpoint branch in `component_for`, and the BOM description lead in `_item_code` |
| `pcf/pcf_import.py` | `_build_*` builder, `BUILDERS`, the single-port checks in `correspondences` / `solve_rotation`, and end ordering for reducer-like parts |
| `pcf/pcf_catalog.py` | Resolver in `_RESOLVERS`, for files from other programs that carry no Quetzal record |
| `Nomeclature.md` | New property letters |

A new **rating** of an existing family needs only a CSV. The forms list
`<PType>_*.csv` files as grades and treat a table as socket or threaded when
its `Conn` column is `SW` or `TH`. Threaded fittings reuse the `Socket*`
classes with `Conn = "TH"`.

## Tables

- `;`-delimited and read as `utf-8-sig`. Keys are DN sizes (`DN20`), and every
  dimension is in mm.
- `Union_*` files have **no header row**. Readers pass the field names
  themselves (`UNION_COLUMNS`, `_UNION_FIELDS`).
- Write tables with a generator script, not by hand, and keep the mapping
  rules in its comments. The script lives outside the repo, so put the rules
  where the next person will find them (e.g. a class docstring).
- Port convention: a socket or threaded port sits at the **socket or thread
  bottom**, where the pipe end rests, and points outward. A male end's port
  sits at its tip, like a pipe end.
- Thread engagement is (L1 + L2)/2 from ASME B1.20.1. The threaded tables use
  it as their socket depth.

## Valves

`Valve` is one PType with several builders. `execute()` picks one from
`Conn` and the start of `PRating` (the table's `VType`):

| Conn | PRating | Builder |
|---|---|---|
| pressure class (`150lb`...) | `Check_Swing...` | `_execute_swing_check_valve` |
| | `Gate...` / `Globe...` | `_execute_rising_flanged` |
| | anything else | `_execute_flanged` (trunnion ball) |
| `SW` / `TH` | `Gate...` / `Globe...` | `_execute_rising_sw_th` |
| | `Check...` | `_execute_check_sw_th` |
| | anything else | `_execute_sw_th` (ball) |
| none | | `_execute_legacy` (two-cone, knife gate, pinch) |

- Shared pieces: `_blFlange` (blind-flange end), `_gearboxWheel`, and
  `_risingStemValve`, which builds the bonnet, yoke, stem and actuator for
  gate and globe; `_gateInternals` / `_globeInternals` supply the body,
  cavity and trim.
- **Flow direction**: the inlet ("back") is port 0 at +Z and the outlet
  ("front") is port 1 at -Z. `doValves(port=...)` mates that port to the
  selected one (the form's *Connect to back / front*). PCF writes port 0 as
  END-POINT 1, and the iso check symbol fills the triangle at END-POINT 2.
- **SW / TH valves**: a table row gives port 0 (`E`, `Conn`); optional
  `E2` / `Conn2` give port 1 for socket x threaded. A mixed valve keeps
  `Conn = "SW"` so every SW/TH check still works. Grades are
  `Valve_<Family>-Threaded`, `-Socket` and `-SocketxThreaded`. A PCF SKEY
  holds one end type, so a socket x threaded valve imported without the
  Quetzal record comes back socket x socket.
- `Actuator` strings: `Handle`, `Handle-closed`, `Gearbox` (ball);
  `Handwheel`, `Gearbox` and, on flanged globes, `Pneumatic`, each with a
  `-closed` form (gate, globe). Values a valve doesn't offer draw as its
  default. `insertValveForm` shows the options for the loaded table
  (`_isRisingStemTable`, `_isDirectionalTable`, `_isCheckTable`).
- `pcf_catalog._valve` maps the SKEY family to a table; add new valve
  tables there too.
- Before refactoring shared valve geometry, record volume and bounding box
  of a few rows per builder and compare afterwards.

## Getting dimension data

- WebFetch often refuses to reproduce dimension tables, or summarizes them
  with columns shifted. Download the page with `curl` and parse the `<table>`
  rows yourself. In Git Bash on Windows, set `PYTHONIOENCODING=utf-8` and read
  the HTML as `latin-1`.
- **Read what each letter means before using it.** When a page doesn't label its letters, say what you inferred.
- Check derived values against a second source, or flag them as unchecked.
- Read the page's footnotes, not just the table. On the B16.10 face-to-face
  pages the globe / lift check column holds rows marked "swing check only".
- When matching a photo, find the flow arrow before deciding which end a
  feature belongs on.

## Geometry checks that caught real problems

- **Ports lining up is not enough.** Mated parts can still overlap.
  - A male end seated by its tip in a socket deeper than the thread
    engagement sank its hex 8 mm into the fitting.
  - Run `spatial_query batch_interference` on every assembly.
  - Mated parts should show zero or near-zero volume. About 0.7 mm³ per
    pipe-in-socket joint is a known artefact: the pipe table's OD is 0.001 mm
    over the fitting's socket.
- Check **what the joint looks like**, not just that it closes. A made-up
  threaded joint leaves a gap between the hex and the fitting face.
- **Build every row of a new table** in a scratch document. Check
  `Shape.isValid()`, a single solid, positive volume and the port positions.
  This catches thin walls and inverted lengths that a single test part won't.
- Where a body and its socket band have the same radius, fusing leaves seam
  rings. `cut(...).removeSplitter()` merges them without changing the volume.
- Look inside: cut the shape in half with a box, show it as a
  `Part::Feature` and screenshot it. Probe internals with small solids,
  e.g. a cylinder in the bore must hit a closed disc and miss an open one,
  and a thin ring just inside each socket bottom must be fully solid.
- `BoundBox` is loose around tori and splines; measure with
  `optimalBoundingBox()`.

## OCC boolean pitfalls

Each of these made a valve shape invalid, split it into several solids or
returned a null shape on some table rows only:

- **Tangent or coplanar faces**: a circle tangent to a plane, a flat side at
  exactly a tube's radius, a cylinder ending on another's face, two coaxial
  surfaces of the same radius. Overlap by a margin (0.3 to 0.5 wall) or
  change a radius by a few percent instead.
- **Thin overlaps** (0.01 mm) leave two solids after a fuse.
- **A cylinder coaxial with a torus** may not merge with it; move it off the
  axis by a few percent of its radius.
- **Lofts**: fusing a `makeLoft` solid made later booleans invalid. Shapes
  that checked valid right after their fuse were invalid afterwards (later
  booleans change shared tolerances). Use exact primitives (cones, tori,
  revolved faces).
- `removeSplitter()` can return an invalid solid; keep the unsplit shape
  when it is valid and the merged one is not.
- To find the failing step, run an AST-instrumented copy of the builder that
  logs `isValid()` and solid count after every `fuse` / `cut`, and keep the
  shapes to re-check after the function returns.

## Working in the live FreeCAD session over MCP

See also the `quetzal-piping` skill in the AI_Piping_Design repo ([§2 and §10](https://github.com/petermaginot/AI_Piping_Design))
for the session preamble and verification recipe.

- **FreeCAD runs the installed copy** (`%APPDATA%\FreeCAD\v1-1\Mod\Quetzal`),
  not this checkout. To test repo code:
  1. Check that the installed modules match `HEAD`.
  2. Put the repo root first on `sys.path`.
  3. Delete `pFeatures`, `pCmd`, `pForms`, **`dodoDialogs`** and `pcf*` from
     `sys.modules`, then re-import.

  `dodoDialogs` matters: forms scan `tablez/` next to that file, so a stale
  copy hides new CSVs and leaves the grade list empty.
- New tables don't reach the installed workbench until they're copied there.
  A rating missing from a form is a deployment problem, not a code bug.
- **Autosave**: the bridge saves the active document before each call if it
  has a file path and unsaved changes.
  - Create scratch documents with `view_control create_document` before the
    first `execute_python`.
  - Check `FileName` and `Modified` on every open document before touching
    any of them.
- **Leave the user's model as you found it.** When asked to change a part in
  it, change only its properties, inside one transaction, and say what you
  changed. Report anything odd (such as a part sitting 1" off its port)
  rather than "fixing" it.
- `execute_python` keeps its namespace between calls, but loses it when
  FreeCAD restarts. Redefine helpers rather than relying on stale ones, and
  keep each call under about 50 s.
- Building every row of a valve table takes minutes (about 1 to 2 s per
  valve). Use `execute_python_async`; past 120 s it returns a job id for
  `poll_job`. Foreground `sleep` is blocked, so wait with a background Bash
  timer.
- FreeCAD can crash under long sessions. `spawn_freecad_instance` fails on
  Windows (its socket path must be under `/tmp`), so ask the user to restart
  FreeCAD, then check the open documents again.
- `FreeCADGui.insert` / `export` fail inside the MCP context. Call
  `pcf_export.export(...)` and `pcf_import.insert(path, docname)` directly.
- Maker signatures differ. `pCmd.makePipe(rating, propList)` takes the rating
  first. `makeOutlet` puts the rating inside the propList and takes a
  `Rotation`. `makeSocketElbow` / `makeSocketTee` take `rating=`.
- Screenshots: `ActiveView.saveImage(path, w, h, "White")`, then read the
  PNG. Rasterize iso SVGs with `PySide6.QtSvg.QSvgRenderer`.
- Open the forms from code too: set the grade and size, call `insert()`,
  and check `PRating` and `Conn` on the new object. This caught grades that
  were stored wrong.

## Testing

- `python -m unittest discover -s pcf/tests -t .` and
  `python -m unittest discover -s iso/tests -t .` run with system Python, no
  FreeCAD needed.
- `pcf_map` imports FreeCAD (through `quetzal_units`), so test PCF mapping
  live: export, then import with and without the `COMPONENT-ATTRIBUTE99`
  record. Also import a file whose end points are in the other order.
- After a PCF change, build an iso sheet from the exported file
  (`iso_build.build_sheet`) and read its BOM and warnings.

## Editing files

- The working tree uses **CRLF** (`core.autocrlf=true`). Appending LF text
  leaves files with mixed line endings. When scripting edits, read with
  `newline=None` and write with `newline="\r\n"`, and assert each `old`
  string occurs the expected number of times.
- In Git Bash, `grep -c $'\r'` reported 0 on CRLF files. Count line endings
  with Python instead.
- Large heredocs containing quotes can break the Bash tool. Write the
  content to a scratch file and append or run it from there.
- A Bash heredoc turned `\\` into `\`, which joined two lines of
  `pFeatures.py` silently. Write scripts containing backslashes with the
  Write tool.
