# Changelog

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
