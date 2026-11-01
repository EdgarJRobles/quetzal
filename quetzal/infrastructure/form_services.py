# SPDX-License-Identifier: LGPL-3.0-or-later
"""Production FormServices composition."""

from __future__ import annotations

from functools import lru_cache

from ..application.form_services import FormServices
from ..application.workbench_state import default_workbench_state
from .freecad.preview import default_preview_service
from .catalog import default_catalog_repository
from .freecad.reporting import FreeCADReporter
from .standard_filters import default_standard_filter_service


@lru_cache(maxsize=1)
def default_form_services() -> FormServices:
    return FormServices(
        catalog=default_catalog_repository(),
        standard_filters=default_standard_filter_service(),
        preview=default_preview_service(),
        state=default_workbench_state(),
        reporter=FreeCADReporter(),
    )
