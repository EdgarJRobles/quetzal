# SPDX-License-Identifier: LGPL-3.0-or-later
"""Production FormServices composition."""

from __future__ import annotations

from functools import lru_cache

from ..application.catalog_presenter import CatalogPresenter
from ..application.form_services import FormServices
from ..application.workbench_state import default_workbench_state
from .freecad.preview import default_preview_service
from .catalog import default_catalog_repository
from .freecad.fitting_inserter import FreeCADFittingInserter
from .freecad.pipe_inserter import FreeCADPipeInserter
from .freecad.pype_line_service import FreeCADPypeLineService
from .freecad.reporting import FreeCADReporter
from .freecad.section_presenter import default_section_presenter
from .standard_filters import default_standard_filter_service


@lru_cache(maxsize=1)
def default_form_services() -> FormServices:
    catalog = default_catalog_repository()
    filters = default_standard_filter_service()
    return FormServices(
        catalog=catalog,
        pipe_inserter=FreeCADPipeInserter(),
        pype_line=FreeCADPypeLineService(),
        fitting_inserter=FreeCADFittingInserter(),
        catalog_presenter=CatalogPresenter(catalog, filters),
        section_presenter=default_section_presenter(),
        standard_filters=filters,
        preview=default_preview_service(),
        state=default_workbench_state(),
        reporter=FreeCADReporter(),
    )
