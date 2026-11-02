# SPDX-License-Identifier: LGPL-3.0-or-later
"""Export Quetzal piping objects to PCF.

FreeCAD calls export(objects, filename) from File > Export.
"""

import os
import re

import FreeCAD

import pCmd
import quetzal_units

from . import pcf_fittings, pcf_map, pcf_model
from .pcf_model import PcfComponent, PcfFile, PcfPoint

translate = FreeCAD.Qt.translate


def _log_warning(msg):
    FreeCAD.Console.PrintWarning("PCF export: " + msg + "\n")


# --------------------------------------------------------------------------
# Object collection and pipeline grouping
# --------------------------------------------------------------------------


def _expand(objects):
    """Flatten groups (folders, PypeLine groups, App::Part containers) into their members."""
    seen = set()
    out = []

    def visit(o):
        if o.Name in seen:
            return
        seen.add(o.Name)
        if hasattr(o, "PType"):
            out.append(o)
        if o.hasExtension("App::GroupExtension"):
            for child in o.Group:
                visit(child)

    for o in objects:
        visit(o)
    return out


def _pipeline_name(obj):
    """Label of the PypeLine owning obj, else of its group or App::Part
    container (e.g. a spool), else the document."""
    parent = obj.getParentGroup() or obj.getParentGeoFeatureGroup()
    while parent is not None:
        for member in parent.Group:
            if getattr(member, "PType", None) == "PypeLine":
                return member.Label
        above = parent.getParentGroup() or parent.getParentGeoFeatureGroup()
        if above is None:
            return parent.Label
        parent = above
    return obj.Document.Label


def collect_pipelines(objects, single=False):
    """Return {pipeline name: [objects]} in document order.

    single=True puts everything in one pipeline, named after the first
    pypeline or container found (e.g. a spool plus loose assembly items)."""
    lines = {}
    for o in _expand(objects):
        if o.PType in ("PypeLine", "PypeBranch"):
            continue
        if o.PType not in pcf_map.KEYWORDS:
            _log_warning("%s (%s) has no PCF equivalent, skipped" % (o.Label, o.PType))
            continue
        lines.setdefault(_pipeline_name(o), []).append(o)
    if single and len(lines) > 1:
        doc_label = next(iter(lines.values()))[0].Document.Label
        name = next((n for n in lines if n != doc_label), doc_label)
        lines = {name: [o for members in lines.values() for o in members]}
    elif len(lines) > 1:
        _supports_to_their_pipes(lines)
    return lines


SUPPORT_REACH = 150.0  # mm a support may sit off the pipe surface (shoe, clamp on a beam below)


def _supports_to_their_pipes(lines):
    """Move each support into the pipeline of the pipe it carries: supports
    are often kept in a group of their own, which would give them a drawing
    without their pipe."""
    pipes = []
    for name, members in lines.items():
        for o in members:
            if o.PType == "Pipe":
                ends = [o.getGlobalPlacement().multVec(o.Placement.inverse().multVec(p))
                        for p in (pCmd.portsPos(o) or [])]
                if len(ends) == 2:
                    pipes.append((name, ends[0], ends[1], float(o.OD) / 2.0))
    for name in list(lines):
        for o in list(lines[name]):
            if o.PType != "Clamp":
                continue
            at = o.getGlobalPlacement().Base
            best = None
            for owner, a, b, radius in pipes:
                off = _off_segment(at, a, b)
                if off is not None and off <= radius + SUPPORT_REACH and (best is None or off < best[0]):
                    best = (off, owner)
            if best is not None and best[1] != name:
                lines[name].remove(o)
                lines[best[1]].append(o)
    for name in [n for n, members in lines.items() if not members]:
        del lines[name]


def _off_segment(p, a, b):
    """Distance from p to segment a-b, None when p is beyond either end."""
    ab = b - a
    den = ab.dot(ab)
    if den < 1e-9:
        return None
    t = (p - a).dot(ab) / den
    if t < -1e-6 or t > 1 + 1e-6:
        return None
    return (p - (a + ab * t)).Length


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------


def _pt(v, bore=0.0):
    return PcfPoint(v.x, v.y, v.z, bore)


def _closest_point_between_lines(p1, d1, p2, d2):
    """Midpoint of the shortest segment between two lines, None if parallel."""
    w = p1 - p2
    a, b, c = d1.dot(d1), d1.dot(d2), d2.dot(d2)
    d, e = d1.dot(w), d2.dot(w)
    den = a * c - b * b
    if abs(den) < 1e-9:
        return None
    s = (b * e - c * d) / den
    t = (a * e - b * d) / den
    return ((p1 + d1 * s) + (p2 + d2 * t)) * 0.5


def _project_on_line(p, a, b):
    ab = b - a
    if ab.Length < 1e-9:
        return FreeCAD.Vector(a)
    return a + ab * ((p - a).dot(ab) / ab.dot(ab))


# --------------------------------------------------------------------------
# Component builders
# --------------------------------------------------------------------------


def component_for(obj, units_bore):
    """Build the PcfComponent for one Quetzal object (None if unsupported)."""
    keyword, skey = pcf_map.keyword_and_skey(obj)
    if keyword is None:
        return None
    ptype = obj.PType
    bore = pcf_map.bore_for(obj.PSize, units_bore)
    if bore == 0:
        _log_warning("%s: size %r is not a DN size, bore written as 0" % (obj.Label, obj.PSize))
    # Ports are in the object's parent frame; map them to world coordinates
    # for objects inside a moved App::Part container.
    to_world = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
    placement = obj.getGlobalPlacement()
    ports = [to_world.multVec(p) for p in (pCmd.portsPos(obj) or [])]
    dirs = [to_world.Rotation.multVec(d) for d in (pCmd.portsDir(obj) or [])]
    comp = PcfComponent(keyword=keyword, skey=skey)

    if ptype in ("Elbow", "SocketEll"):
        comp.end_points = [_pt(ports[0], bore), _pt(ports[1], bore)]
        centre = _closest_point_between_lines(ports[0], dirs[0], ports[1], dirs[1])
        comp.centre_point = _pt(centre if centre is not None else placement.Base)
    elif ptype in ("Tee", "SocketTee"):
        bore2 = pcf_map.bore_for(getattr(obj, "PSizeBranch", "") or obj.PSize, units_bore)
        comp.end_points = [_pt(ports[0], bore), _pt(ports[1], bore)]
        comp.centre_point = _pt(_project_on_line(ports[2], ports[0], ports[1]))
        comp.branch_points = [_pt(ports[2], bore2)]
    elif ptype in ("Reduct", "SocketCoupling", "HexBushing"):
        bore2 = pcf_map.bore_for(getattr(obj, "PSize2", "") or obj.PSize, units_bore)
        comp.end_points = [_pt(ports[0], bore), _pt(ports[1], bore2)]
    elif ptype in ("Cap", "SocketCap", "HexPlug"):
        comp.end_points = [_pt(ports[0], bore)]
    elif ptype == "Outlet":
        carrier_r = float(getattr(obj, "CarrierOD", 0)) / 2.0
        if carrier_r == 0:
            _log_warning("%s: carrier OD unknown, olet CENTRE-POINT placed on its base" % obj.Label)
        centre = placement.multVec(FreeCAD.Vector(0, 0, -carrier_r))
        comp.centre_point = _pt(centre)
        comp.branch_points = [_pt(ports[0], bore)]
    elif ptype == "Bolts_Nuts":
        comp.co_ords = _pt(placement.Base, bore)
        comp.attributes += [
            ("BOLT-DIA", "%.4g" % float(obj.dBolt)),
            ("BOLT-LENGTH", "%.4g" % float(obj.lBolt)),
            ("BOLT-QUANTITY", "%d" % int(obj.n)),
        ]
    elif ptype == "Clamp":
        comp.co_ords = _pt(placement.Base, bore)
        comp.attributes.append(("NAME", obj.Label))
    else:  # two-port inline items: Pipe, Flange, Valve, Gasket, SocketUnion
        comp.end_points = [_pt(p, bore) for p in ports[:2]]

    comp.item_code, description = _item_code(obj, keyword)
    comp.attributes.append((pcf_map.QUETZAL_ATTRIBUTE,
                            pcf_map.encode_record(pcf_map.quetzal_record(obj))))
    return comp, description


def _item_code(obj, keyword):
    parts = [obj.PType, obj.PSize]
    for name in ("PSize2", "PSizeBranch"):
        other = getattr(obj, name, "")
        if other and other != obj.PSize:
            parts.append(other)
    conn = str(getattr(obj, "Conn", "") or "")
    for name in ("FlangeType", "FClass", "PRating", "Conn"):
        value = str(getattr(obj, name, "") or "")
        # socket/threaded grades are stored as "3000lb_SW" / "3000lb_TH"; Conn follows
        if name == "PRating" and conn and value.endswith("_" + conn):
            value = value[:-len(conn) - 1]
        if value and value != "No rating" and value not in parts:
            parts.append(value)
    # Sizes in the description follow the user's DN/NPS preference.
    sizes = {obj.PSize, getattr(obj, "PSize2", ""), getattr(obj, "PSizeBranch", "")} - {""}
    words = [quetzal_units.format_psize(p) if p in sizes else p for p in parts[1:]]
    lead = [keyword]
    if obj.PType in ("HexBushing", "HexPlug"):
        # exported as a reducer / cap, but the BOM should say what it is
        lead = ["HEX", "BUSHING" if obj.PType == "HexBushing" else "PLUG"]
    # Elbows differ by angle and radius, which PRating (a schedule) does not
    # show: a 90 LR, a 45 LR and a 6D bend must not share an item code.
    if obj.PType in ("Elbow", "SocketEll") and hasattr(obj, "BendAngle"):
        angle = float(getattr(obj.BendAngle, "Value", obj.BendAngle))
        if obj.PType == "Elbow" and hasattr(obj, "BendRadius"):
            radius = float(getattr(obj.BendRadius, "Value", obj.BendRadius))
            dn = pcf_map.dn_number(obj.PSize) or 50
            des = pcf_fittings.elbow_designation(angle, radius, dn)
            parts.append(des.code)
            lead = ["BEND" if des.is_bend else "ELBOW", "%sDEG" % des.angle_text,
                    des.radius_class or "R%d" % round(radius)]
        else:  # socket-weld / screwed elbow: the angle is enough
            text = ("%.1f" % angle).rstrip("0").rstrip(".")
            parts.append(text)
            lead = [keyword, "%sDEG" % text]
    code = re.sub(r"[^A-Za-z0-9_.\-]+", "_", "-".join(parts)).upper()
    description = " ".join(lead + words)
    return code, description


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def units_bore_preference():
    return "INCH" if quetzal_units.get_size_system() == 1 else "MM"


def build_pcf_files(objects, units_bore=None, single=False):
    """Return a list of PcfFile, one per pipeline found in objects
    (a single one when single=True)."""
    units_bore = units_bore or units_bore_preference()
    files = []
    for name, members in collect_pipelines(objects, single).items():
        pf = PcfFile(
            header={
                "ISOGEN-FILES": "ISOGEN.FLS",
                "UNITS-BORE": units_bore,
                "UNITS-CO-ORDS": "MM",
                "UNITS-WEIGHT": "KGS",
                "UNITS-BOLT-DIA": "MM",
                "UNITS-BOLT-LENGTH": "MM",
            },
            pipeline_reference=name,
        )
        for o in members:
            try:
                result = component_for(o, units_bore)
            except Exception as e:  # keep going; report the object
                _log_warning("%s: %s, skipped" % (o.Label, e))
                continue
            if result is None:
                continue
            comp, description = result
            pf.components.append(comp)
            pf.materials.setdefault(comp.item_code, description)
        files.append(pf)
    return files


def _safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "pipeline"


def export(objects, filename, units_bore=None):
    """Write objects to filename.  Several pipelines give several files
    named <filename>_<pipeline>.pcf.  Returns the list of files written."""
    files = build_pcf_files(objects, units_bore)
    if not files:
        _log_warning("no piping objects to export")
        return []
    written = []
    base, ext = os.path.splitext(filename)
    ext = ext or ".pcf"
    for pf in files:
        path = base + ext if len(files) == 1 else "%s_%s%s" % (base, _safe(pf.pipeline_reference), ext)
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(pcf_model.write(pf))
        written.append(path)
        FreeCAD.Console.PrintMessage(
            translate("PCF", "PCF export: {0} components written to {1}").format(
                len(pf.components), path) + "\n")
    return written
