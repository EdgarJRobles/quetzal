# SPDX-License-Identifier: LGPL-3.0-or-later
"""Core package for the Quetzal workbench.

The package follows a layered architecture:

``quetzal.domain``
    Pure Python business rules.  It must never import ``FreeCAD``, ``Part``
    or ``PySide`` so it can be reasoned about and tested in isolation.

``quetzal.application``
    Use cases that orchestrate domain objects through small protocols.  It
    still does not import FreeCAD; adapters are injected at the edges.

``quetzal.infrastructure``
    Concrete adapters for the outside world (FreeCAD document, properties,
    view providers, CSV catalogue files).

``quetzal.features``
    FreeCAD feature proxies built on top of the domain and infrastructure
    layers.  Legacy module-level names (``pFeatures.Pipe`` ...) are kept as
    re-exports for backwards compatibility.
"""

__version__ = "1.8.11"
