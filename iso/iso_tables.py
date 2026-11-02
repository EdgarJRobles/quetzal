# SPDX-License-Identifier: LGPL-3.0-or-later
"""Editable BOM spreadsheet and notes annotation on an isometric page (FreeCAD).

The BOM is a Spreadsheet::Sheet shown by a TechDraw::DrawViewSpreadsheet
(columns A-D; hidden columns F-G hold each row's key and generated text).
The notes are a TechDraw::DrawViewAnnotation.  Both can be edited by hand;
iso_editable decides what a regeneration keeps.
"""

import FreeCAD

from . import iso_build, iso_editable
from .iso_editable import Row

PX_MM = 0.2646  # spreadsheet pixel size on the page
ROW_PX = 17  # 4.5 mm rows
SHEET_TEXT = 9.0  # DrawViewSpreadsheet.TextSize giving ~2.5 mm text in those rows
FIXED_COLS_MM = (10.0, 20.0, 20.0)  # PT, QTY, SIZE; DESCRIPTION takes the rest
NOTE_TEXT = 2.5
NOTE_PITCH = 4.7  # mm per annotation line at NOTE_TEXT (measured)
NOTE_CHAR = 1.75  # mm per capital at NOTE_TEXT (measured, average)
VISIBLE, KEY_COL, GEN_COL = "ABCD", "F", "G"


def _warn(msg):
    FreeCAD.Console.PrintWarning("Isometric: " + msg + "\n")


def _set(sheet, cell, text):
    # A leading apostrophe stores text: set('6"') would parse to 152.4 mm.
    sheet.set(cell, "'" + text if text else "")


def _get(sheet, cell):
    try:
        text = sheet.getContents(cell) or ""
    except ValueError:
        return ""
    return text[1:] if text.startswith("'") else text


def read_rows(sheet):
    """Rows below the header, as iso_editable.Row."""
    used = sheet.getUsedCells() if hasattr(sheet, "getUsedCells") else []
    last = 0
    for cell in used:
        digits = "".join(ch for ch in cell if ch.isdigit())
        last = max(last, int(digits or 0))
    rows = []
    for r in range(2, last + 1):
        vals = [_get(sheet, "%s%d" % (c, r)) for c in VISIBLE + KEY_COL + GEN_COL]
        rows.append(Row(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]))
    return rows


def write_rows(sheet, rows, fmt):
    sheet.clearAll()
    for i, row in enumerate(rows, 1):
        for col, text in zip(VISIBLE + KEY_COL + GEN_COL,
                             (row.pt, row.qty, row.size, row.desc, row.key, row.gen)):
            _set(sheet, "%s%d" % (col, i), text)
        if row.style:
            sheet.setStyle("A%d:D%d" % (i, i), row.style)
        sheet.setRowHeight(str(i), ROW_PX)
    for col, mm in zip(VISIBLE, _column_mm(fmt)):
        sheet.setColumnWidth(col, int(round(mm / PX_MM)))


def _column_mm(fmt):
    x0, _y0, x1, _y1 = fmt.bom_area
    return FIXED_COLS_MM + (x1 - x0 - sum(FIXED_COLS_MM),)


def _page_y(fmt, y_down):
    return fmt.height - y_down  # TechDraw page Y is up


def _link(view, name, obj=None):
    """Get or set a hidden link property on the isometric view."""
    if not hasattr(view, name):
        view.addProperty("App::PropertyLinkHidden", name, "Isometric", "Editable table of this iso")
    if obj is not None:
        setattr(view, name, obj)
    return getattr(view, name)


def safe_label(text):
    """A label TechDraw can use: it writes view labels into SVG ids unescaped,
    so a quote (e.g. 8"x12") breaks the page's SVG and the view draws blank."""
    return text.replace('"', "''").replace("&", "and").replace("<", "(").replace(">", ")")


def update_tables(view, sheet_result, fmt):
    """Create or refresh the BOM spreadsheet and notes for an iso view."""
    doc = view.Document
    page = view.findParentPage()
    pipeline = view.IsoPipeline

    # --- BOM ---
    sheet = _link(view, "IsoBomSheet")
    previous = []
    if sheet is None:
        sheet = _link(view, "IsoBomSheet", doc.addObject("Spreadsheet::Sheet", "IsoBOM"))
        sheet.Label = safe_label("BOM " + pipeline)
    else:
        previous = read_rows(sheet)
    rows, lost = iso_editable.bom_rows(sheet_result.bom, previous)
    for key, text in lost:
        _warn("%s: edited BOM row %r is no longer in the model and was dropped: %r"
              % (pipeline, key[len("item:"):], text))
    write_rows(sheet, rows, fmt)
    doc.recompute()

    table = _link(view, "IsoBomView")
    if table is not None:
        table.Label = safe_label(table.Label)  # repairs tables made before labels were safe
    else:
        table = _link(view, "IsoBomView", doc.addObject("TechDraw::DrawViewSpreadsheet", "IsoBOMView"))
        table.Label = safe_label("BOM table " + pipeline)
        table.Source = sheet
        page.addView(table)  # recentres: position afterwards
    table.CellStart, table.CellEnd = "A1", "D%d" % len(rows)
    table.TextSize = SHEET_TEXT
    x0, y0, _x1, _y1 = fmt.bom_area
    width = sum(_column_mm(fmt))
    height = len(rows) * ROW_PX * PX_MM
    top = y0 + iso_build.TABLE_TOP
    table.X, table.Y = x0 + width / 2.0, _page_y(fmt, top + height / 2.0)  # X/Y is the centre

    # --- notes ---
    notes = _link(view, "IsoNotesView")
    current = []
    if notes is None:
        notes = _link(view, "IsoNotesView", doc.addObject("TechDraw::DrawViewAnnotation", "IsoNotes"))
        notes.Label = safe_label("Notes " + pipeline)
        page.addView(notes)
    else:
        current = list(notes.Text)
    if not hasattr(view, "IsoNotesGenerated"):
        view.addProperty("App::PropertyStringList", "IsoNotesGenerated", "Isometric",
                         "Generated notes last written, to keep the user's own notes")
    chars = int((width - 2.0) / NOTE_CHAR)
    generated = iso_editable.note_lines(sheet_result.notes, chars)
    lines, refreshed = iso_editable.merge_notes(current, view.IsoNotesGenerated, generated)
    if not refreshed:
        _warn("%s: the generated notes were edited by hand, so they were not refreshed" % pipeline)
    notes.Text = lines
    notes.TextSize = NOTE_TEXT
    view.IsoNotesGenerated = generated
    block_w = max(len(line) for line in lines) * NOTE_CHAR
    block_h = len(lines) * NOTE_PITCH
    notes.X = x0 + 1.0 + block_w / 2.0  # X/Y is the centre of the text block
    notes.Y = _page_y(fmt, fmt.notes_bottom - block_h / 2.0)
    if fmt.notes_bottom - block_h < top + height + 3.0:
        _warn("%s: the notes overlap the bill of material; move one of them on the page" % pipeline)
