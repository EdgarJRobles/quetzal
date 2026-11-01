# SPDX-License-Identifier: LGPL-3.0-or-later

import FreeCAD

FreeCAD.addImportType("Piping Component File (*.pcf)", "pcf.pcf_import")
FreeCAD.addExportType("Piping Component File (*.pcf)", "pcf.pcf_export")
