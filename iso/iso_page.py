# SPDX-License-Identifier: LGPL-3.0-or-later
"""TechDraw pages hosting generated isometrics (FreeCAD).

Each page holds one DrawViewSymbol the size of the sheet, placed at the page
centre, so SVG coordinates are page millimetres.  The inputs needed to
regenerate it are stored as properties on that view.  The BOM and notes are
separate, editable objects (see iso_tables).
"""

import os
import re

import FreeCAD

import quetzal_units
from pcf import pcf_export, pcf_model

from . import iso_build, iso_sheet, iso_tables

translate = FreeCAD.Qt.translate
GROUP = "Isometric"


def _warn(msg):
    FreeCAD.Console.PrintWarning("Isometric: " + msg + "\n")


def default_options():
    nps = quetzal_units.get_size_system() == 1
    return iso_build.Options(units="ftin" if nps else "mm", size_system="NPS" if nps else "DN",
                             sheet=iso_sheet.ANSI_B if nps else iso_sheet.ISO_A3)


def template_path(fmt):
    return os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates", *fmt.template.split("/"))


# --------------------------------------------------------------------------
# PCF data for a view
# --------------------------------------------------------------------------


def _pcf_files_for(view):
    """PcfFiles the view was made from (model objects or a .pcf file)."""
    if view.IsoPcfPath:
        with open(view.IsoPcfPath, encoding="utf-8", errors="replace") as f:
            files = pcf_model.parse(f.read())
        return [pcf_model.to_mm(pf) for pf in files]
    units_bore = "INCH" if view.IsoSizeSystem == "NPS" else "MM"
    if view.IsoSource:  # a selection is drawn as one pipeline
        return pcf_export.build_pcf_files(view.IsoSource, units_bore=units_bore, single=True)
    return pcf_export.build_pcf_files(view.Document.Objects, units_bore=units_bore)


def _options_for(view):
    opt = default_options()
    opt.units = view.IsoUnits
    opt.size_system = view.IsoSizeSystem
    opt.sheet = iso_sheet.FORMATS.get(view.IsoSheetFormat, opt.sheet)
    opt.rotation = None if view.IsoRotation < 0 else view.IsoRotation
    opt.compression = view.IsoCompression or None
    return opt


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------


_ISO_SOURCE_DOC = "Model objects drawn; empty = whole document"


def _migrate_iso_source(view):
    """Pages made before IsoSource was a global link: convert in place.  A
    local-scope link makes App::Part pull the view and all its sources into
    whichever container one of them is added to."""
    if view.getTypeIdOfProperty("IsoSource") != "App::PropertyLinkList":
        return
    src = list(view.IsoSource)
    view.removeProperty("IsoSource")
    view.addProperty("App::PropertyLinkListGlobal", "IsoSource", GROUP, _ISO_SOURCE_DOC)
    view.IsoSource = src


def _add_iso_properties(view):
    props = (
        # global scope: the view references model objects in any container
        ("App::PropertyLinkListGlobal", "IsoSource", _ISO_SOURCE_DOC),
        ("App::PropertyFile", "IsoPcfPath", "PCF file drawn, instead of model objects"),
        ("App::PropertyString", "IsoPipeline", "Pipeline reference drawn on this page"),
        ("App::PropertyInteger", "IsoRotation", "View rotation 0-3 in quarter turns about Z (0 = FreeCAD standard isometric); -1 = automatic, fewest clashes"),
        ("App::PropertyFloat", "IsoCompression", "Pipe length factor on paper; 0 = fit to the sheet"),
        ("App::PropertyString", "IsoUnits", "Dimension units: ftin or mm"),
        ("App::PropertyString", "IsoSizeSystem", "Nominal sizes: NPS or DN"),
        ("App::PropertyString", "IsoSheetFormat", "Sheet format: ANSI B or ISO A3"),
    )
    for ptype, name, doc in props:
        if not hasattr(view, name):
            view.addProperty(ptype, name, GROUP, doc)
    _migrate_iso_source(view)


def _set_title(template, fields):
    with open(template.Template, encoding="utf-8") as f:
        keys = set(re.findall(r'freecad:editable="([^"]+)"', f.read()))
    texts = dict(template.EditableTexts)
    texts.update({k: v for k, v in fields.items() if k in keys})
    template.EditableTexts = texts  # a new dict: in-place edits do not stick


def _render(view, pcf_file):
    """Redraw the iso, and create or refresh its editable BOM and notes."""
    page = view.findParentPage()
    sheet = iso_build.build_sheet(pcf_file, _options_for(view), tables=False)
    view.Symbol = sheet.svg
    fmt = iso_sheet.FORMATS[view.IsoSheetFormat]
    view.X, view.Y = fmt.width / 2.0, fmt.height / 2.0
    _set_title(page.Template, sheet.title)
    iso_tables.update_tables(view, sheet, fmt)
    for w in sheet.warnings:
        _warn("%s: %s" % (pcf_file.pipeline_reference, w))
    return sheet


def create_page(doc, pcf_file, options, source=None, pcf_path=""):
    """New TechDraw page with the isometric of one pipeline."""
    fmt = options.sheet
    page = doc.addObject("TechDraw::DrawPage", "IsoPage")
    page.Label = iso_tables.safe_label("ISO " + pcf_file.pipeline_reference)
    template = doc.addObject("TechDraw::DrawSVGTemplate", "IsoTemplate")
    template.Template = template_path(fmt)
    page.Template = template
    view = doc.addObject("TechDraw::DrawViewSymbol", "Isometric")
    view.Label = iso_tables.safe_label("Isometric " + pcf_file.pipeline_reference)
    _add_iso_properties(view)
    view.IsoSource = list(source or [])
    view.IsoPcfPath = pcf_path
    view.IsoPipeline = pcf_file.pipeline_reference
    view.IsoRotation = -1 if options.rotation is None else options.rotation
    view.IsoCompression = options.compression or 0.0
    view.IsoUnits = options.units
    view.IsoSizeSystem = options.size_system
    view.IsoSheetFormat = fmt.name
    if hasattr(view, "ScaleType"):
        view.ScaleType = "Custom"
    view.Scale = 1.0
    page.addView(view)  # recentres the view: position it afterwards
    _render(view, pcf_file)
    return page


def pages_from_objects(doc, objects=None, options=None):
    """Isometric pages: one for the selected objects (they are drawn together,
    e.g. a spool plus loose assembly items), or one per pipeline in the whole
    document when objects is None."""
    options = options or default_options()
    units_bore = "INCH" if options.size_system == "NPS" else "MM"
    if objects:
        files = pcf_export.build_pcf_files(objects, units_bore=units_bore, single=True)
    else:
        files = pcf_export.build_pcf_files(doc.Objects, units_bore=units_bore)
    pages = [create_page(doc, pf, options, source=objects) for pf in files]
    doc.recompute()
    return pages


def pages_from_pcf(doc, path, options=None):
    options = options or default_options()
    with open(path, encoding="utf-8", errors="replace") as f:
        files = [pcf_model.to_mm(pf) for pf in pcf_model.parse(f.read())]
    pages = [create_page(doc, pf, options, pcf_path=path) for pf in files]
    doc.recompute()
    return pages


def iso_views(objects):
    """Isometric views among objects, including those on selected pages."""
    views = []
    for o in objects:
        if hasattr(o, "IsoPipeline"):
            views.append(o)
        elif o.isDerivedFrom("TechDraw::DrawPage"):
            views.extend(v for v in o.Views if hasattr(v, "IsoPipeline"))
    return views


def update(view):
    """Regenerate an isometric view from its stored inputs."""
    _add_iso_properties(view)  # bring pages from older versions up to date
    files = _pcf_files_for(view)
    match = [pf for pf in files if pf.pipeline_reference == view.IsoPipeline]
    if not match:
        _warn("pipeline %r no longer found; page left unchanged" % view.IsoPipeline)
        return None
    sheet = _render(view, match[0])
    view.Document.recompute()
    return sheet
