# SPDX-License-Identifier: LGPL-3.0-or-later
"""Sheet formats: where the iso, BOM and notes go, and title-block fields.

Page coordinates are millimetres with Y down (SVG convention).  Areas were
measured from the FreeCAD 1.1 TechDraw templates named below.
"""

import textwrap
from dataclasses import dataclass

# Characters that fit the title-block cells at the templates' font sizes.
TITLE_CHARS_ANSI = 30  # DrawingTitle1..3
NUMBER_CHARS_ANSI = 22  # drawing_number
TITLE_CHARS_A3 = 26  # title and drawing_number


def _shorten(text, width):
    """text cut at a word boundary to at most width characters."""
    if len(text) <= width:
        return text
    cut = text[:width - 1].rsplit(" ", 1)[0] if " " in text[:width - 1] else text[:width - 1]
    return cut + "…"


@dataclass(frozen=True)
class SheetFormat:
    name: str
    template: str  # relative to <FreeCAD resources>/Mod/TechDraw/Templates
    width: float
    height: float
    iso_area: tuple  # x0, y0, x1, y1
    bom_area: tuple  # x0, y0, x1, y1 (the table grows down from y0)
    notes_bottom: float  # notes sit above this y, in the BOM column

    def title_fields(self, info):
        """Title-block values for template keys, from info (pipeline, spec, date, sheet).

        Long pipeline names are wrapped or shortened to fit the template's cells."""
        pipeline = info.get("pipeline", "")
        if self.name == "ANSI B":
            lines = textwrap.wrap(pipeline, TITLE_CHARS_ANSI)[:2] or [""]
            lines.append("PIPING ISOMETRIC")
            if info.get("spec"):
                lines.append("SPEC " + info["spec"])
            lines += ["", ""]
            return {
                "DrawingTitle1": lines[0],
                "DrawingTitle2": lines[1],
                "DrawingTitle3": lines[2],
                "drawing_number": _shorten(pipeline, NUMBER_CHARS_ANSI),
                "scale": "NTS",
                "Sheet": info.get("sheet", "1 OF 1"),
                "revision_index": "",
                "CompanyName": "", "CompanyAddress": "", "DrawnBy": "", "CheckedBy": "",
                "Approved1": "", "Approved2": "", "Code": "", "Weight": "",
            }
        return {
            "title": _shorten(pipeline, TITLE_CHARS_A3),
            "document_type": "Piping isometric",
            "drawing_number": _shorten(pipeline, TITLE_CHARS_A3),
            "scale": "NTS",
            "sheet_number": info.get("sheet", "1/1"),
            "date_of_issue": info.get("date", ""),
            "part_material": ("Spec " + info["spec"]) if info.get("spec") else "",
            "revision_index": "", "creator": "", "approval_person": "",
            "legal_owner_1": "", "legal_owner_2": "", "legal_owner_3": "", "legal_owner_4": "",
            "general_tolerances": "",
        }


ANSI_B = SheetFormat(
    name="ANSI B",
    template="ASME/ANSIB_Landscape.svg",
    width=431.8, height=279.4,
    iso_area=(26.0, 26.4, 259.0, 253.4),  # left of the title block (x >= 264, y >= 210)
    bom_area=(266.0, 26.4, 405.0, 205.0),
    notes_bottom=205.0,
)

ISO_A3 = SheetFormat(
    name="ISO A3",
    template="ISO/A3_Landscape_ISO5457_minimal.svg",
    width=420.0, height=297.0,
    iso_area=(24.0, 14.0, 224.0, 283.0),  # left of the title block (x >= 228, y >= 234)
    bom_area=(230.0, 14.0, 406.0, 231.0),
    notes_bottom=231.0,
)

FORMATS = {"ANSI B": ANSI_B, "ISO A3": ISO_A3}
