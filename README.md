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
<https://wiki.freecad.org/Dodo_Workbench>

Discussion in the FreeCAD Forum:
<https://forum.freecad.org/viewtopic.php?t=22711>

## Changelog

Read our [CHANGELOG] file to know about the latest changes.

## Contributing

Read our [CONTRIBUTING] file to know about ways how to help on the workbench.

## Roadmap
Here are some of the planned developments for this Workbench:

- [ ] Icrease valve design detail
- [ ] Add HVAC duct support.
  - [ ] Elbow
  - [ ] Reduction
  - [ ] Branch
  - [ ] Round duct
  - [ ] Square duct
  - [ ] Oval duct
- [ ] Support, if possible, fitting & frame profiles types:
  - [X] Pipe
  - [X] Elbow
  - [X] Cap
  - [X] Gasket
  - [X] Reduction
  - [X] Coupling
  - [X] Flange
  - [ ] Valve
    - [ ] Gate Valve
    - [ ] Plug Valve
    - [X] Ball Valve
    - [ ] Check Valve
    - [ ] Globe Valve
    - [X] Butterfly Valve
    - [ ] Needle Valve
    - [ ] Knife gate Valve
    - [ ] Pinch Valve
  - [ ] Pipe Clamping
    - [X] U-bolt clamp
    - [ ] Beam clamp
  - [ ] Beam joins
- [ ] Support, if possible, International design standarts:
  - [ ] ASME B16.5 (NPS 1/2 to 24")
  - [ ] ASME B16.47 (NPS 26 to 60")
  - [ ] ASME B16.36 (orifice flange)
  - [ ] DIN 2527 (Blink flange)
  - [ ] DIN 2543 PN16 (Flat face for welding slip on flange)
  - [ ] DIN 2544 PN25 (Flat face for welding slip on flange)
  - [ ] DIN 2545 PN40 (Flat face for welding slip on flange)
  - [ ] ISO 7005-1 PN10 Raise Face(EN 1092-1 equivalent)
  - [ ] ISO 7005-1 PN16 Raise Face(EN 1092-1 equivalent)
  - [ ] ISO 7005-1 PN25 Raise Face(EN 1092-1 equivalent)
  - [ ] ISO 7005-1 PN40 Raise Face(EN 1092-1 equivalent)
  - [ ] ISO 7005-1 PN64 Raise Face(EN 1092-1 equivalent)
  - [ ] ISO 7005-1 PN100 Raise Face(EN 1092-1 equivalent)

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
