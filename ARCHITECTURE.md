# Quetzal architecture

This document describes the architecture introduced by the SOLID refactor and
the compatibility rules that keep existing FreeCAD documents and macros
working.

## Goals

1. **Separate business rules from FreeCAD.** Catalogue parsing, nominal sizes
   and port maths must be testable without a running FreeCAD instance.
2. **Make features data-driven.** Adding a fitting should be a matter of
   declaring a feature definition, not editing several `if/elif` chains.
3. **Keep the public API stable.** `pFeatures.Pipe`, `pCmd.makePipe`,
   `pCmd.doPipes`, command names, property names and the `PType` values are
   part of the contract with saved documents, forms and user macros.
4. **Make the workbench testable headlessly.** FreeCADCmd has no
   `FreeCADGui.Selection` and no main window, so the core must degrade
   gracefully instead of raising `AttributeError`.

## Layers

```mermaid
flowchart LR
    subgraph Domain["quetzal.domain (no FreeCAD)"]
        Catalog[CatalogRepository]
        Sizes[Pipe sizes]
        Ports[Port / Vec3]
    end

    subgraph Application["quetzal.application (no FreeCAD)"]
        Registry[FeatureRegistry]
        Inserter[FeatureInserter]
    end

    subgraph Infra["quetzal.infrastructure"]
        Csv[CsvCatalogRepository]
        Doc[FreeCADDocumentAdapter]
        Props[PropertySpec]
        View[ViewProvider]
    end

    subgraph Features["quetzal.features"]
        Base[PypeFeature]
        Pipe[Pipe + PipeShapeBuilder]
        Cap[Cap + CapShapeBuilder]
    end

    Legacy["pFeatures.py / pCmd.py\n(compatibility facade)"] --> Features
    Legacy --> Application
    Legacy --> Infra
    Features --> Application
    Features --> Infra
    Features --> Domain
    Infra --> Domain
    Application --> Domain
```

**Dependency rule:** arrows point inwards. `quetzal.domain` imports nothing
from the rest of the workbench. `quetzal.application` only depends on the
domain and on protocols. FreeCAD-specific code lives in
`quetzal.infrastructure` and `quetzal.features`.

### Domain

| Module | Responsibility |
| --- | --- |
| `quetzal/domain/catalog.py` | `CatalogTable`, `CatalogRepository` protocol, CSV and in-memory adapters, safe file resolution. |
| `quetzal/domain/pipe_sizes.py` | Single immutable outside-diameter table and lookup helpers. |
| `quetzal/domain/ports.py` | `Vec3`, `Port`, nearest-port calculation. |
| `quetzal/domain/errors.py` | `QuetzalError`, `CatalogNotFoundError`, `FeatureRegistrationError`. |

### Application

| Module | Responsibility |
| --- | --- |
| `quetzal/application/feature_registry.py` | `FeatureDefinition` value object and `FeatureRegistry` (register / lookup / validate). |
| `quetzal/application/insertion.py` | `FeatureInserter` use case and the `DocumentPort` protocol; `InMemoryDocument` test double. |

### Infrastructure

| Module | Responsibility |
| --- | --- |
| `quetzal/infrastructure/catalog.py` | Process-wide CSV repository rooted at `<addon>/tablez`. |
| `quetzal/infrastructure/freecad/properties.py` | `PropertySpec` and `define_properties()` to replace property boilerplate. |
| `quetzal/infrastructure/freecad/document.py` | `FreeCADDocumentAdapter` implementing `DocumentPort`. |
| `quetzal/infrastructure/freecad/view_provider.py` | Icon-only `ViewProvider` and `FreeCADViewFactory`. |

### Features

`quetzal/features/base.py` provides `PypeFeature`, the replacement for the old
`pFeatures.pypeType`. Migrated features (`Pipe`, `Cap`) declare their
properties as `PropertySpec` tuples and delegate shape construction to a
`ShapeBuilder` returning `FeatureGeometry` (shape, ports, directions).

`quetzal/features/catalog.py` registers the migrated features in `FEATURES`.
`pCmd.makeFeature(key, ...)` can build any registered feature without adding a
new factory function.

## Runtime flows

### Declarative insertion (`pCmd.makePipe`, `pCmd.makeCap`)

```mermaid
sequenceDiagram
    participant Caller as pCmd.makePipe / makeFeature
    participant Inserter as FeatureInserter
    participant Registry as FeatureRegistry
    participant Adapter as FreeCADDocumentAdapter
    participant Proxy as Pipe proxy
    Caller->>Registry: get("Pipe")
    Registry-->>Caller: FeatureDefinition
    Caller->>Inserter: insert(definition, rating, props, pos, Z)
    Inserter->>Adapter: add_object("Part::FeaturePython", "Pipe")
    Inserter->>Proxy: create(obj, rating, *props)
    Inserter->>Adapter: attach_view(obj, icon)
    Inserter->>Adapter: place(obj, pos, Z, axis)
    Inserter->>Adapter: set translated label
    Inserter-->>Caller: document object
```

### Attached insertion (`pCmd.doPipes`, `doCaps`, `doFlanges`,
`doReduct`, `doGaskets`, `doBolts_Nuts`)

These flows share `_insert_attached()`:

1. resolve the selected object and closest port (`_attachment_context`);
2. open one transaction;
3. create the fitting (with its placement);
4. run an optional pre-alignment hook (for example, trimming the pipe);
5. align the fitting to the selected port **before** committing, so the
   alignment is part of the same undo step;
6. move the result to the requested pype line;
7. commit and recompute; abort and report on failure instead of leaving
   orphan objects behind.

## Compatibility contract

These are intentionally preserved and covered by tests:

- module/class paths used by FreeCAD's proxy serialization:
  `pFeatures.Pipe`, `pFeatures.Cap`, `pFeatures.pypeType`, `pCmd.ViewProvider`;
- `PType` values and property names/types/groups;
- local port semantics (`Pipe` ports at `(0,0,0)` and `(0,0,Height)`);
- `pCmd.make*` and `pCmd.do*` signatures, including positional `propList`
  ordering;
- all 61 command names, their icon names and toolbar/menu references.

`Pipe` and `Cap` moved to `quetzal.features`, but `pFeatures` re-exports the
same classes, so old documents and `from pFeatures import Pipe` continue to
work. Save/reload is checked by the headless integration suite.

## What has been migrated

| Area | Status |
| --- | --- |
| Catalogue + OD table | Migrated to domain; `pCmd.readTable`, `protoPypeForm.fillSizes`, `pFeatures.pipe_OD` and `pForms.pipe_OD` use it. |
| Feature base class | Migrated to `quetzal.features.base.PypeFeature`; `pFeatures.pypeType` is the same object. |
| Pipe / Cap | Migrated with property schemas, shape builders and registry entries. |
| Generic insertion | `FeatureInserter` + `FeatureRegistry` available. |
| Attached insertion | Shared pipeline for six `do*` flows. |
| Headless support | Selection/view accessors degrade safely; command contract can be validated without a GUI. |
| Module cycle | `pFeatures` no longer imports `pCmd` at module scope. |

## Remaining roadmap

These items are deliberately out of scope for this branch but are the natural
next steps:

1. Split the `Valve` god class into strategies per connection type while
   keeping `Valve` as the public facade.
2. Split `Flange` geometry into builders per `FlangeType`.
3. Move the remaining feature proxies to `PropertySpec` + `FeatureDefinition`
   (`Tee`, `Reduct`, `Elbow`, `Gasket`, `Outlet`, socket fittings, ...).
4. Migrate the remaining `do*` flows (`doElbow`, `doTees`, `doValves`,
   `doSocket*`, `doBeams`, `doOutlets`) to `_insert_attached`.
5. Add a command metadata registry so toolbar/menu definitions and
   `addCommand` calls come from one declarative source.
6. Introduce a `PreviewService` for the dialog previews (single cache key and
   configurable path).
7. Replace label/name child resolution in `PypeLine2`/`PypeBranch2` with
   `App::PropertyLinkList` while reading the legacy string lists.

See [SOLID mapping](docs/architecture/solid-mapping.md),
[extension guide](docs/architecture/extending.md) and
[testing guide](docs/architecture/testing.md).
