# Changelog

## [Unreleased]

### Added

- Layered `quetzal/` package: pure domain (catalogues, pipe sizes, ports),
  application (feature registry, insertion service), FreeCAD infrastructure
  and migrated feature proxies.
- `FeatureDefinition`/`FeatureRegistry` so features can be added by
  registration instead of editing factory chains.
- Headless integration suite covering 22 features, 243 catalogues, document
  save/reload, 61 commands, 9 insertion flows and the standards metadata.
- Standards and units layer: 10 institutions, 26 international standards,
  86 dimensions and 19 catalogue families in `standards/catalog.json`.
- `Unit`/`Quantity` conversions and ISO 6708 DN/NPS identities in the domain.
- Unit-aware catalogue classification and row normalisation.

### Changed

- `Pipe`, `Cap` and `TerminalAdapter` now use declarative properties,
  injectable shape builders and the generic insertion service; `pFeatures`
  re-exports them for compatibility.
- `Valve` geometry is split into six strategies with pure mode resolvers;
  the public `pFeatures.Valve` facade and its 8-mode geometry are unchanged.
- `Flange` geometry is split into five builders plus a generic fallback;
  ports and insertion offsets live in the pure domain layer.
- `Flange` properties are declared with `PropertySpec`, preserving the
  original order, groups and documentation.
- The port-based `do*` flows (elbow, tee, valve, socket elbow/tee/cap/coupling/
  union) now share the same transaction/selection/alignment pipeline.
- `PypeBranch2` now stores children in authoritative `TubesLink`/`CurvesLink`
  properties, migrates legacy name lists on load and keeps dual writes.
- `PypeLine2` resolves its group through `getParentGroup()` with a unique-label
  fallback; `moveToPyLi`, color updates and purge no longer use `[0]` lookups.
- `Gasket` now uses declarative properties and an injectable shape builder.
- Add a `CommandSpec` registry and a single ordered `quetzal.ui.layout` for
  toolbars, menus, context menus and watchers; `InitGui` and the pie menu use
  it instead of duplicated lists.
- Fix the missing macro source for `Quetzal_CreateCutList` and make the macro
  source extraction robust to blank first lines/pyc-only installs.
- Clear task watchers before re-adding them on workbench activation.
- `pFeatures.pypeType` is now `quetzal.features.base.PypeFeature`; the
  `pFeatures <-> pCmd` module import cycle was removed.
- Six `do*` insertion flows share one transaction/selection/alignment
  pipeline; alignment now happens before the transaction is committed.
- `protoPypeForm.fillSizes` and the nominal OD lookups use the shared
  catalogue repository.
- `pCmd` selection and `ViewObject` access degrade safely in console mode.

### Fixed

- Register `Quetzal_TeeQM` correctly and remove the duplicated
  `Quetzal_CapQM` registration.
- Use `Quetzal_CouplingUnion` without the `.svg` suffix so the icon resolves.
- Avoid headless `AttributeError` on `FreeCADGui.Selection`/`ViewObject`.
- Return the created object from `pCmd.makeTerminalAdapter` instead of `None`.
- Stop mutating the shared `vO/vX/vY/vZ` vectors in the duct builders, which
  corrupted geometry created later in the session.

## [1.7.8] - 2025-12-13

- Sync quetzal version
- Improve branch frame trim and extend method

## [1.1.0] - 2025-01-17

### Added

- Add ASME flange weld neck, lap join, socket slot
- Add German, Greek, Polish and Swedish translations

### Changed

- Update WB icon with an actual quetzal
- Replace original profiles to use BIM profiles
- Update icons to be easier to identify
- Update Spanish translations
- Rename icons and add them to FreeCAD resources path

### Fixed

- Fix object bases & added extra flange & pipe standards
- Mark `openTransaction()` strings for translation
- Don't translate objects' internal name, only translate `obj.Label`

## [1.0.0] - 2024-10-20

🌱 Initial release of Quetzal WB based on the work of **oddtopus** on [Dodo WB].

### Added

- Add Cut List function by File Phil
- Add translation support
- Add Spanish translation
- Add view provider class to assign icons to parametric objects
- Add miter corner feature

### Changed

- Apply black style to Python files
- Make commands to use "Quetzal_" prefix
- Extend RH profile profile CSV file
- Update some icons
- Mark commands unavailable when there is no active document

### Fixed

- Don't remove sketch profile by Ebrahim Raeyat
- Fix touched object after recomputation by Zheng, Lei
- Fix license ID by Chris Hennes
- Fix PypeLineForm pipe generation
- Fix typos

[Dodo WB]: https://github.com/oddtopus/dodo
[1.0.0]: https://github.com/EdgarJRobles/dodo/releases/tag/V1.0.0RC2
[1.1.0]: https://github.com/EdgarJRobles/dodo/releases/tag/1.1.0
