# Extending Quetzal

This guide shows the intended extension points. The goal is that a new feature,
catalogue consumer or command can be added without editing unrelated modules.

## Add a new parametric feature

Suppose you want a `Blind` feature (a flat blind flange). Create
`quetzal/features/blind.py`:

```python
from __future__ import annotations

from typing import Any

import FreeCAD
import Part

from ..application.feature_registry import FeatureDefinition
from ..infrastructure.freecad.properties import PropertySpec, define_properties
from .base import PypeFeature
from .geometry import FeatureGeometry

BLIND_PROPERTIES = (
    PropertySpec("App::PropertyLength", "OD", "Blind", "Outside diameter"),
    PropertySpec("App::PropertyLength", "thk", "Blind", "Thickness"),
    PropertySpec("App::PropertyString", "Profile", "Blind", "Section dim."),
)


class BlindShapeBuilder:
    def build(self, fp: Any) -> FeatureGeometry:
        shape = Part.makeCylinder(float(fp.OD) / 2, float(fp.thk))
        return FeatureGeometry(
            shape=shape,
            ports=(FreeCAD.Vector(),),
            directions=(FreeCAD.Vector(0, 0, -1),),
        )


class Blind(PypeFeature):
    shape_builder_class = BlindShapeBuilder

    def __init__(self, obj, rating="150lb", DN="DN50", OD=160.0, thk=15.0):
        super().__init__(obj)
        obj.Proxy = self
        obj.PType = "Blind"
        obj.PRating = rating
        obj.PSize = DN
        define_properties(obj, BLIND_PROPERTIES, {"OD": OD, "thk": thk})
        self.execute(obj)

    def execute(self, fp):
        fp.Profile = f"{fp.OD}x{fp.thk}"
        geometry = self.shape_builder_class().build(fp)
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super().execute(fp)


BLIND_FEATURE = FeatureDefinition(
    key="Blind",
    proxy=Blind,
    label="Blind",
    icon="Quetzal_InsertFlange",
    accepted_prop_counts=(4,),
)
```

Register it in `quetzal/features/catalog.py`:

```python
from .blind import BLIND_FEATURE

for _definition in (PIPE_FEATURE, CAP_FEATURE, BLIND_FEATURE):
    FEATURES.register(_definition)
```

Re-export it from `quetzal/features/__init__.py` so legacy code and saved
documents can resolve `pFeatures.Blind`:

```python
from .blind import Blind

__all__ = ["Blind", "Cap", "FEATURES", "Pipe", "PypeFeature"]
```

Expose it in `pFeatures.py` with the other compatibility imports:

```python
from quetzal.features import Blind, Cap, Pipe, PypeFeature as pypeType
```

No new branch is needed in `pCmd`: any registered feature can be created with

```python
pCmd.makeFeature("Blind", "150lb", [ "DN50", 160.0, 15.0 ], pos, Z)
```

If the feature needs a stable public factory, add a one-line wrapper:

```python
def makeBlind(propList=(), pos=None, Z=None, rating="150lb"):
    return _feature_inserter.insert(
        FEATURES.get("Blind"), rating, propList, _as_vec3(pos), _as_vec3(Z)
    )
```

### Checklist

- [ ] Proxy inherits `PypeFeature` (common properties and `nearestPort`).
- [ ] Properties are declared with `PropertySpec`.
- [ ] Geometry lives in a `ShapeBuilder` returning `FeatureGeometry`.
- [ ] `FeatureDefinition` registered in `quetzal/features/catalog.py`.
- [ ] Class re-exported from `pFeatures` for document compatibility.
- [ ] Unit test for the registry/definition.
- [ ] Integration test builds the feature headlessly.

## Add a catalogue consumer

Depend on the protocol, not on the filesystem:

```python
from quetzal.domain.catalog import CatalogRepository


class MyRatingSelector:
    def __init__(self, catalog: CatalogRepository):
        self._catalog = catalog

    def choices(self, family: str):
        return self._catalog.ratings(family)

    def first_row(self, family: str, rating: str):
        return self._catalog.get_table(family, rating).first()
```

Production code passes `default_catalog_repository()`; tests pass
`InMemoryCatalogRepository`:

```python
repo = InMemoryCatalogRepository()
repo.add("Pipe", "SCH-40", [{"PSize": "DN50", "OD": "60.32"}])
selector = MyRatingSelector(repo)
assert selector.choices("Pipe") == ("SCH-40",)
```

The repository caches parsed tables, strips the UTF-8 BOM, validates file
names (no path traversal) and raises `CatalogNotFoundError` instead of
returning a silently empty list.

## Add a command

The current command registration is still class-based because
`quetzal_config.addCommand()` records the source of `Activated` for FreeCAD's
macro recorder. Until the command metadata registry lands (see roadmap):

1. Create the class in the appropriate command module (`CPipe.py`,
   `CFrame.py`, `CUtils.py` or `cut_list/cut_list_commands.py`).
2. Return `Pixmap` **without** the `.svg` extension and with an existing
   `iconz/<name>.svg`.
3. Register it with `quetzal_config.addCommand("Quetzal_<Name>", <Name>())`.
4. Add the name to the relevant toolbar/menu list in `InitGui.py`.
5. Run the command contract check; it fails on duplicate names, missing icons
   and `InitGui` references to unregistered commands.

```python
class insertBlind:
    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        import pForms

        pForms.insertBlindForm()

    def GetResources(self):
        return {
            "Pixmap": "Quetzal_InsertFlange",
            "MenuText": QT_TRANSLATE_NOOP("Quetzal_InsertBlind", "Insert a blind"),
            "ToolTip": QT_TRANSLATE_NOOP("Quetzal_InsertBlind", "Insert a blind flange"),
        }
```

Use the headless-safe helpers `_selection()`, `_selection_ex()`,
`_view_object()` and `_set_shape_color()` from `pCmd` instead of touching
`FreeCADGui.Selection` or `ViewObject` directly.

## Add a dialog data source

`protoPypeForm.fillSizes()` now uses the shared repository. Subclasses that
still open CSV files should be migrated one at a time:

```python
from quetzal.domain.errors import CatalogNotFoundError
from quetzal.infrastructure.catalog import default_catalog_repository


def fillSizes(self):
    self.sizeList.clear()
    try:
        table = default_catalog_repository().get_table(self.PType, self.PRating)
    except CatalogNotFoundError as exc:
        self.pipeDictList = []
        FreeCAD.Console.PrintWarning(f"{exc}\n")
        return
    self.pipeDictList = table.to_dicts()
    for row in self.pipeDictList:
        self.sizeList.addItem(self._format(row))
```

Keep `self.pipeDictList`, `self.ratingList` and `self.PRating` intact: command
flows and subclasses rely on them.
