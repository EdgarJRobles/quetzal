# SPDX-License-Identifier: LGPL-3.0-or-later
"""Build a complete isometric sheet from one pipeline of PCF data (pure Python).

build_sheet(pcf_file, options) -> IsoSheet with the SVG text and everything
the tests and the TechDraw page need.
"""

import datetime
import textwrap
from dataclasses import dataclass, field

from . import iso_bom, iso_dims, iso_graph, iso_layout, iso_symbols
from .iso_draw import (CHAR_W, TEXT, W_SYMBOL, W_THIN, Line, Obstacles, Poly, Text, add,
                       mul, text_box, unit)
from .iso_sheet import ANSI_B
from .iso_svg import render, to_page

ROW_H = 4.6
COLS = (10.0, 20.0, 20.0)  # PT NO, QTY, SIZE; description takes the rest


@dataclass
class Options:
    units: str = "mm"  # "mm" or "ftin"
    size_system: str = "DN"  # "DN" or "NPS"
    sheet: object = ANSI_B
    rotation: object = None  # quarter turns about Z, None = automatic
    compression: object = None  # pipe factor k, None = fit to the sheet


@dataclass
class IsoSheet:
    svg: str
    items: list  # page items (mm, Y down)
    layout: object
    dimensions: list
    bom: list
    balloons: list  # (item number, page centre, page anchor)
    title: dict
    scale: float  # uniform shrink applied to fit the iso area (1 = none)
    warnings: list = field(default_factory=list)
    notes: list = field(default_factory=list)  # note texts, unnumbered


def build_sheet(pcf_file, options=None, sheet_label="1 OF 1", tables=True):
    """tables=False leaves the BOM table and the notes out of the SVG, for a
    TechDraw page that shows them as an editable spreadsheet and annotation."""
    opt = options or Options()
    fmt = opt.sheet
    x0, y0, x1, y1 = fmt.iso_area
    graph = iso_graph.build(pcf_file)
    warnings = ["component %d (%s): %s" % (ci, pcf_file.components[ci].keyword, why)
                for ci, why in graph.skipped]
    if not graph.edges:
        raise ValueError("pipeline %r has nothing to draw" % pcf_file.pipeline_reference)

    layout = iso_layout.layout_graph(graph, x1 - x0, y1 - y0, opt.rotation, opt.compression)
    if layout.clashes:
        warnings.append("%d line clashes could not be removed" % len(layout.clashes))
    if layout.open_loops:
        warnings.append("%d closed loop(s) drawn out of true direction" % len(layout.open_loops))
    if layout.zoom < 1.0:
        warnings.append("symbols shrunk to %.0f%%: the line is long for one sheet, consider "
                        "splitting it into several pipelines" % (layout.zoom * 100))

    paper, anchors = iso_symbols.draw(layout, opt.units)
    obstacles = Obstacles()
    obstacles.add_drawing(paper)
    dim_items, dimensions = iso_dims.place_dimensions(layout, opt.units, obstacles)
    dim_items += iso_dims.place_slopes(layout, obstacles)
    dim_items += iso_dims.place_rolls(layout, obstacles)
    dim_items += iso_dims.place_skew_offsets(layout, opt.units, obstacles)
    bom = iso_bom.bom_items(pcf_file, opt.units, opt.size_system)
    balloon_items, balloons = iso_bom.place_balloons(bom, anchors, layout, obstacles)
    paper = paper + dim_items + balloon_items

    transform, scale = _fit_transform(paper, fmt.iso_area)
    if scale < 1.0:
        warnings.append("drawing shrunk to %.0f%% to fit the sheet" % (scale * 100))
    items = to_page(paper, transform, scale)
    balloons = [(num, transform(c), transform(a)) for num, c, a in balloons]

    spec = pcf_file.pipeline_attr("PIPING-SPEC", "")
    title = fmt.title_fields({
        "pipeline": pcf_file.pipeline_reference, "spec": spec, "sheet": sheet_label,
        "date": datetime.date.today().isoformat(),
    })
    items += _north_arrow(layout, fmt)
    items.append(bom_heading(fmt))
    notes = _notes(pcf_file, opt, spec)
    if tables:
        bom_bottom, table = _bom_table(bom, fmt)
        items += table
        items += _notes_block(notes, fmt, bom_bottom, warnings)
    svg = render(items, fmt.width, fmt.height)
    return IsoSheet(svg, items, layout, dimensions, bom, balloons, title, scale, warnings, notes)


# --------------------------------------------------------------------------
# Placement on the sheet
# --------------------------------------------------------------------------


def _points(it):
    if isinstance(it, Line):
        return [it.p1, it.p2]
    if isinstance(it, Poly):
        return it.points
    if isinstance(it, Text):
        return text_box(it)
    return [(it.centre[0] - it.r, it.centre[1] - it.r), (it.centre[0] + it.r, it.centre[1] + it.r)]


def _fit_transform(paper, area):
    pts = [p for it in paper for p in _points(it)]
    bx0, by0 = min(p[0] for p in pts), min(p[1] for p in pts)
    bx1, by1 = max(p[0] for p in pts), max(p[1] for p in pts)
    ax0, ay0, ax1, ay1 = area
    scale = min(1.0, (ax1 - ax0) / max(bx1 - bx0, 1e-6), (ay1 - ay0) / max(by1 - by0, 1e-6))
    cx, cy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
    mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2

    def transform(p):
        return (cx + (p[0] - mx) * scale, cy - (p[1] - my) * scale)

    return transform, scale


def _north_arrow(layout, fmt):
    x0, y0, _x1, _y1 = fmt.iso_area
    centre = (x0 + 16.0, y0 + 16.0)  # the arrow is centred here whichever way it points
    n = unit(iso_layout.project((0.0, 1.0, 0.0), layout.rotation))
    d = (n[0], -n[1])  # page Y is down
    base = add(centre, mul(d, -7.0))
    tip = add(centre, mul(d, 7.0))
    side = (-d[1], d[0])
    head = [tip, add(add(tip, mul(d, -3.5)), mul(side, 1.3)), add(add(tip, mul(d, -3.5)), mul(side, -1.3))]
    label = add(tip, mul(d, 3.5))
    return [Line(base, tip, W_SYMBOL), Poly(head, W_THIN, fill=True),
            Text((label[0], label[1] + 1.2), "N", 3.5, bold=True)]


def _wrap(text, width_mm, size):
    chars = max(8, int(width_mm / (CHAR_W * size)))
    return textwrap.wrap(text, chars) or [""]


TABLE_TOP = 6.0  # the table starts this far below the top of the BOM area


def bom_heading(fmt):
    x0, y0, x1, _y1 = fmt.bom_area
    return Text(((x0 + x1) / 2, y0 + 4.0), "BILL OF MATERIAL", 3.5, bold=True)


def _bom_table(bom, fmt):
    """Table rows from the top of the BOM area; returns (bottom y, items)."""
    x0, y0, x1, y1 = fmt.bom_area
    cols = [x0, x0 + COLS[0], x0 + COLS[0] + COLS[1], x0 + sum(COLS), x1]
    size = TEXT
    items = []
    y = y0 + TABLE_TOP
    top = y
    heads = ("PT", "QTY", "SIZE", "DESCRIPTION")
    for i, h in enumerate(heads):
        items.append(Text((cols[i] + 1.0, y + ROW_H - 1.3), h, size, anchor="start", bold=True))
    y += ROW_H
    items.append(Line((x0, y), (x1, y), W_SYMBOL))
    category = None
    for row in bom:
        if row.category != category:
            category = row.category
            items.append(Text((cols[3] + 1.0, y + ROW_H - 1.3), category, size, anchor="start",
                              bold=True))
            y += ROW_H
        lines = _wrap(row.description, cols[4] - cols[3] - 2.0, size)
        for i, value in enumerate((str(row.number), row.quantity, row.size)):
            items.append(Text((cols[i] + 1.0, y + ROW_H - 1.3), value, size, anchor="start"))
        for line in lines:
            items.append(Text((cols[3] + 1.0, y + ROW_H - 1.3), line, size, anchor="start"))
            y += ROW_H
        items.append(Line((x0, y), (x1, y), W_THIN))
    for x in cols:
        items.append(Line((x, top), (x, y), W_THIN if x not in (x0, x1) else W_SYMBOL))
    items.append(Line((x0, top), (x1, top), W_SYMBOL))
    items.append(Line((x0, y), (x1, y), W_SYMBOL))
    return y, items


def _notes(pcf_file, opt, spec):
    notes = ["NOT TO SCALE.",
             "DIMENSIONS IN %s." % ("FEET AND INCHES" if opt.units == "ftin" else "MILLIMETRES"),
             "DIMENSIONS ARE TO FITTING CENTRELINES, REDUCER ENDS, FLANGE FACES AND OPEN ENDS.",
             "PIPELINE: %s" % pcf_file.pipeline_reference]
    if spec:
        notes.append("PIPING SPEC: %s" % spec)
    return notes


def _notes_block(notes, fmt, bom_bottom, warnings):
    x0, _y0, x1, _y1 = fmt.bom_area
    size = TEXT
    lines = []
    for i, note in enumerate(notes, 1):
        wrapped = _wrap("%d. %s" % (i, note), x1 - x0 - 2.0, size)
        lines.extend(wrapped)
    height = (len(lines) + 1) * ROW_H
    top = fmt.notes_bottom - height
    if top < bom_bottom + 3.0:
        warnings.append("notes overlap the bill of material")
    items = [Text((x0 + 1.0, top + ROW_H - 1.3), "NOTES:", size, anchor="start", bold=True)]
    for i, line in enumerate(lines, 1):
        items.append(Text((x0 + 1.0, top + (i + 1) * ROW_H - 1.3), line, size, anchor="start"))
    return items
