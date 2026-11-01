# SPDX-License-Identifier: LGPL-3.0-or-later
"""Dependency container passed to UI forms.

Forms depend on these small services instead of importing ``pCmd``, the
concrete preview singleton or FreeCAD globals.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.catalog import CatalogRepository
from .catalog_presenter import CatalogPresenter
from .insertion_requests import FittingInserter, PipeInserter
from .preview import PreviewService
from .section_catalog import SectionCatalogPresenter
from .reporting import UserReporter
from .standard_filters import StandardFilterService
from .workbench_state import WorkbenchState


@dataclass(frozen=True)
class FormServices:
    catalog: CatalogRepository
    pipe_inserter: PipeInserter
    fitting_inserter: FittingInserter
    catalog_presenter: CatalogPresenter
    section_presenter: SectionCatalogPresenter
    standard_filters: StandardFilterService
    preview: PreviewService
    state: WorkbenchState
    reporter: UserReporter
