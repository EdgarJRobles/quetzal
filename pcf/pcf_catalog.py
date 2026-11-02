# SPDX-License-Identifier: LGPL-3.0-or-later
"""Catalog (tablez/*.csv) lookup for PCF components that carry no Quetzal
round-trip record, i.e. files written by other programs.

resolve(ptype, comp, ctx) returns a dict keyed by Quetzal property names
(the same shape pcf_map.quetzal_record() produces), built from the best
matching catalog row plus lengths measured from the PCF points.
"""

import csv
import math
import os
import re

import FreeCAD

from . import pcf_map

TABLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tablez")

DEFAULT_SCHEDULE = "SCH-STD"
DEFAULT_CLASS = "150lb"
DEFAULT_SOCKET_CLASS = "3000lb"
SOCKET_CLASSES = ("3000lb", "6000lb", "9000lb")
THREADED_CLASSES = ("2000lb", "3000lb", "6000lb")
UNION_COLUMNS = ["PSize", "OD", "A", "C", "D", "E", "Conn"]


class ResolveError(Exception):
    """No usable catalog data for a component."""


_tables = {}


def table(name, header=None):
    """Rows of tablez/<name> as dicts, [] if the file does not exist.

    Handles a UTF-8 BOM and, when header is given, files without a header row.
    """
    if name in _tables:
        return _tables[name]
    path = os.path.join(TABLES_DIR, name)
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as f:
            data = [r for r in csv.reader(f, delimiter=";") if r and any(c.strip() for c in r)]
        if data:
            if header is not None and data[0][0].strip().upper().startswith("DN"):
                keys = header
            else:
                keys, data = [k.strip() for k in data[0]], data[1:]
            rows = [dict(zip(keys, (c.strip() for c in r))) for r in data]
    _tables[name] = rows
    return rows


def num(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def find_row(name, **match):
    for row in table(name):
        if all(row.get(k) == v for k, v in match.items()):
            return row
    return None


def files_matching(pattern):
    rx = re.compile(pattern)
    return sorted(f for f in os.listdir(TABLES_DIR) if rx.match(f))


# --------------------------------------------------------------------------
# Rating hints from free text (attributes, material descriptions, spec)
# --------------------------------------------------------------------------


def guess_schedule(text):
    t = text.upper()
    m = re.search(r"SCH(?:EDULE)?[\s\-.]*(\d{1,3}S?|STD|XXS|XS)\b", t)
    candidates = []
    if m:
        candidates.append("SCH-" + m.group(1))
    for word in ("XXS", "XS", "STD"):
        if re.search(r"\b%s\b" % word, t):
            candidates.append("SCH-" + word)
    for c in candidates:
        if table("Pipe_%s.csv" % c):
            return c
    return None


def guess_class(text, allowed=pcf_map.FLANGED_CLASSES):
    t = text.upper()
    for m in re.finditer(r"(?:CLASS|CL|#)\s*(\d{3,4})|(\d{3,4})\s*(?:LB|#)", t):
        value = (m.group(1) or m.group(2)) + "lb"
        if value in allowed:
            return value
    return None


# --------------------------------------------------------------------------
# Geometry from PCF points
# --------------------------------------------------------------------------


def vec(p):
    return FreeCAD.Vector(p.x, p.y, p.z)


def dist(a, b):
    return (vec(a) - vec(b)).Length


def bend_angle_and_radius(comp):
    c = vec(comp.centre_point)
    v1 = vec(comp.end_points[0]) - c
    v2 = vec(comp.end_points[1]) - c
    between = math.degrees(v1.getAngle(v2))
    angle = 180.0 - between
    tangent = (v1.Length + v2.Length) / 2.0
    radius = tangent / math.tan(math.radians(angle) / 2.0) if angle > 1e-6 else 0.0
    return angle, radius, tangent


# --------------------------------------------------------------------------
# Resolver
# --------------------------------------------------------------------------


class Context:
    """Per-pipeline information the resolver needs."""

    def __init__(self, pcf_file, geometry=None):
        self.units_bore = pcf_file.units_bore
        self.geometry = geometry
        self.pcf_file = pcf_file
        spec = " ".join(v for _k, v in pcf_file.pipeline_attributes)
        self.pipeline_text = spec

    def text_for(self, comp):
        parts = [self.pipeline_text, comp.skey, comp.item_code]
        parts += [v for _k, v in comp.attributes]
        parts.append(self.pcf_file.materials.get(comp.item_code, ""))
        return " ".join(parts)

    def dn(self, point):
        dn = pcf_map.dn_for(point.bore, self.units_bore)
        if dn is None:
            raise ResolveError("missing bore")
        return dn


def _pipe_dims(dn, schedule):
    """(OD, thk, schedule) from the pipe tables, trying the given schedule first."""
    for sched in (schedule, DEFAULT_SCHEDULE, "SCH-40", "SCH-80"):
        row = find_row("Pipe_%s.csv" % sched, PSize=dn)
        if row:
            return num(row["OD"]), num(row["thk"]), sched
    raise ResolveError("no pipe data for %s" % dn)


def _schedule(comp, ctx):
    return guess_schedule(ctx.text_for(comp)) or DEFAULT_SCHEDULE


def _flange_class(comp, ctx):
    return guess_class(ctx.text_for(comp))


def _socket_class(comp, ctx):
    return guess_class(ctx.text_for(comp), SOCKET_CLASSES) or DEFAULT_SOCKET_CLASS


def _socket_table(family, comp, ctx):
    """(file name, class) of the socket-weld or, for a screwed SKEY, threaded
    table of a fitting family, e.g. ("Elbow_3000lb_TH.csv", "3000lb")."""
    if comp.skey[2:4].upper() == "SC":
        cls = guess_class(ctx.text_for(comp), THREADED_CLASSES) or DEFAULT_SOCKET_CLASS
        name = "%s_%s_TH.csv" % (family, cls)
        if os.path.exists(os.path.join(TABLES_DIR, name)):
            return name, cls
    cls = _socket_class(comp, ctx)
    return "%s_%s_SW.csv" % (family, cls), cls


def resolve(ptype, comp, ctx):
    fn = _RESOLVERS.get(ptype)
    if fn is None:
        raise ResolveError("no catalog lookup for %s" % ptype)
    props = fn(comp, ctx)
    props["PType"] = ptype
    return props


def _pipe(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    od, thk, sched = _pipe_dims(dn, _schedule(comp, ctx))
    return {"PSize": dn, "PRating": sched, "OD": od, "thk": thk,
            "Height": dist(comp.end_points[0], comp.end_points[1])}


def _elbow(comp, ctx):
    if comp.centre_point is None:
        raise ResolveError("elbow without CENTRE-POINT")
    dn = ctx.dn(comp.end_points[0])
    od, thk, sched = _pipe_dims(dn, _schedule(comp, ctx))
    angle, radius, _t = bend_angle_and_radius(comp)
    # Pick LR/SR by comparing the measured radius with the catalog rows.
    rating, best = sched, None
    for kind in ("LR", "SR"):
        for a in (90, 45):
            row = find_row("Elbow_%s_%s%d.csv" % (sched, kind, a), PSize=dn)
            if row:
                err = abs(num(row["BendRadius"]) - radius)
                if best is None or err < best:
                    best, rating = err, "%s_%s%d" % (sched, kind, 90 if angle > 67.5 else 45)
                break
    return {"PSize": dn, "PRating": rating, "OD": od, "thk": thk,
            "BendAngle": angle, "BendRadius": radius}


def _socket_elbow(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    fname, cls = _socket_table("Elbow", comp, ctx)
    angle = 90.0
    if comp.centre_point is not None:
        angle = bend_angle_and_radius(comp)[0]
    # nearest tabulated bend angle (the tables carry 90 and 45 rows)
    rows = [r for r in table(fname) if r.get("PSize") == dn]
    row = min(rows, key=lambda r: abs(num(r.get("BendAngle", 90)) - angle)) if rows else None
    if not row:
        raise ResolveError("no socket elbow data for %s %s" % (dn, cls))
    props = {k: num(row[k]) for k in ("OD", "A", "C", "D", "E", "G")}
    props.update(PSize=dn, PRating=cls, BendAngle=angle,
                 Conn=pcf_map.conn_from_skey(comp.skey))
    return props


def _tee_sizes(comp, ctx):
    if comp.centre_point is None or not comp.branch_points:
        raise ResolveError("tee without CENTRE-POINT/BRANCH1-POINT")
    return ctx.dn(comp.end_points[0]), ctx.dn(comp.branch_points[0])


def _tee(comp, ctx):
    dn, dn2 = _tee_sizes(comp, ctx)
    sched = _schedule(comp, ctx)
    row = find_row("Tee_%s.csv" % sched, PSize=dn, PSizeBranch=dn2)
    if row:
        props = {k: num(row[k]) for k in ("OD", "OD2", "thk", "thk2")}
    else:
        od, thk, sched = _pipe_dims(dn, sched)
        od2, thk2, _s = _pipe_dims(dn2, sched)
        props = {"OD": od, "OD2": od2, "thk": thk, "thk2": thk2}
    c = comp.centre_point
    props.update(PSize=dn, PSizeBranch=dn2, PRating=sched,
                 C=(dist(comp.end_points[0], c) + dist(comp.end_points[1], c)) / 2.0,
                 M=dist(comp.branch_points[0], c))
    return props


def _socket_tee(comp, ctx):
    dn, dn2 = _tee_sizes(comp, ctx)
    fname, cls = _socket_table("Tee", comp, ctx)
    row = find_row(fname, PSize=dn, PSizeBranch=dn2)
    if not row:
        raise ResolveError("no socket tee data for %s x %s %s" % (dn, dn2, cls))
    props = {k: num(row[k]) for k in ("OD", "OD2", "A", "C", "D", "E", "G")}
    props.update(PSize=dn, PSizeBranch=dn2, PRating=cls,
                 Conn=pcf_map.conn_from_skey(comp.skey))
    return props


def _reduct(comp, ctx):
    # Callers order the end points large end first.
    dn, dn2 = ctx.dn(comp.end_points[0]), ctx.dn(comp.end_points[1])
    sched = _schedule(comp, ctx)
    props = None
    for row in table("Reduct_%s.csv" % sched):
        if row.get("PSize") != dn:
            continue
        minors = row.get("PSize2", "").split(">")
        if dn2 in minors:
            i = minors.index(dn2)
            pick = lambda key: num(row[key].split(">")[min(i, len(row[key].split(">")) - 1)])
            props = {"OD": num(row["OD"]), "thk": num(row["thk"]),
                     "OD2": pick("OD2"), "thk2": pick("thk2")}
            break
    if props is None:
        od, thk, sched = _pipe_dims(dn, sched)
        od2, thk2, _s = _pipe_dims(dn2, sched)
        props = {"OD": od, "OD2": od2, "thk": thk, "thk2": thk2}
    length = dist(comp.end_points[0], comp.end_points[1])
    conc = comp.keyword != "REDUCER-ECCENTRIC"
    if not conc:
        offset = (props["OD"] - props["OD2"]) / 2.0
        length = math.sqrt(max(length * length - offset * offset, 0.0))
    props.update(PSize=dn, PSize2=dn2, PRating=sched, Height=length, conc=conc)
    return props


def _cap(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    sched = _schedule(comp, ctx)
    row = find_row("Cap_%s.csv" % sched, PSize=dn)
    if row:
        od, thk = num(row["OD"]), num(row["thk"])
    else:
        od, thk, sched = _pipe_dims(dn, sched)
    return {"PSize": dn, "PRating": sched, "OD": od, "thk": thk}


def _socket_cap(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    fname, cls = _socket_table("Cap", comp, ctx)
    row = find_row(fname, PSize=dn)
    if not row:
        raise ResolveError("no socket cap data for %s %s" % (dn, cls))
    props = {k: num(row[k]) for k in ("OD", "A", "C", "E")}
    props.update(PSize=dn, PRating=cls, Conn=pcf_map.conn_from_skey(comp.skey))
    return props


def _flange_port_distance(ftype, row):
    trf = num(row.get("trf"))
    if ftype == "WN":
        return num(row.get("T1")) + trf
    if ftype == "SW":
        return num(row.get("T1")) - num(row.get("Y"))
    if ftype == "BL":
        return num(row.get("t")) + trf
    if ftype == "SO":
        return 2 * trf
    return trf


def _class_of(filename):
    m = re.search(r"-(\d+lb|PN\d+)\.csv$", filename) or re.match(r"Flange_(?:DIN-)?(PN\d+)", filename)
    return m.group(1) if m else ""


def _flange(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    if comp.keyword == "FLANGE-BLIND":
        ftype = "BL"
    else:
        ftype = pcf_map.FLANGE_TYPES.get(comp.skey, "WN")
    length = dist(comp.end_points[0], comp.end_points[1]) if len(comp.end_points) > 1 else None
    hint = _flange_class(comp, ctx)
    classes = list(pcf_map.FLANGED_CLASSES)
    best = None
    for fname in files_matching(r"Flange_.*\.csv$"):
        row = find_row(fname, PSize=dn, FlangeType=ftype)
        if not row:
            continue
        cls = _class_of(fname)
        score = (
            0 if cls == hint else 1,
            abs(_flange_port_distance(ftype, row) - length) if length is not None else 0.0,
            0 if fname.startswith("Flange_ASME") else 1,
            classes.index(cls) if cls in classes else len(classes),
        )
        if best is None or score < best[0]:
            best = (score, fname, row, cls)
    if best is None:
        raise ResolveError("no %s flange data for %s" % (ftype, dn))
    _score, fname, row, cls = best
    sched = _schedule(comp, ctx)
    if ftype == "WN":
        od, thk, sched = _pipe_dims(dn, sched)
        bore = od - 2.0 * thk
    else:
        bore = num(row.get("d"))
    props = {"PSize": dn, "FlangeType": ftype, "FClass": cls,
             "PRating": sched if ftype == "WN" else "No rating", "d": bore}
    for key in ("D", "df", "f", "t", "trf", "drf", "twn", "dwn", "ODp", "R", "T1", "B2", "Y"):
        props[key] = num(row.get(key))
    props["n"] = int(num(row.get("n"), 4))
    if ftype in ("SO", "SW", "LJ"):
        if not props["ODp"]:
            import pFeatures
            props["ODp"] = pFeatures.pipe_OD.get(dn, 0.0)
        if not props["T1"]:
            props["T1"] = props["t"]
    return props


def _blind_flange_props(cls, dn):
    row = find_row("Flange_ASME-BL-RF-%s.csv" % cls, PSize=dn)
    if not row:
        raise ResolveError("no %s blind flange data for %s" % (cls, dn))
    return {"FlgD": num(row["D"]), "Flgt": num(row["t"]), "FlgF": num(row["f"]),
            "FlgN": int(num(row["n"])), "FlgDf": num(row["df"]),
            "FlgDrf": num(row["drf"]), "FlgTrf": num(row["trf"])}


def _valve(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    length = dist(comp.end_points[0], comp.end_points[1])
    end = comp.skey[2:4]
    family = pcf_map.valve_family_from_skey(comp.skey) or "Ball"

    if end in ("SW", "SC"):
        # A PCF SKEY carries one end type, so a socket x threaded gate or
        # globe valve comes back as socket x socket.
        if family in ("Gate", "Globe", "Check_Swing"):
            table = "Valve_%s-%s.csv" % (family.split("_")[0],
                                          "Socket" if end == "SW" else "Threaded")
        else:
            table = "Valve_Ball-Threaded.csv"
        row = find_row(table, PSize=dn)
        if row:
            # Ports sit E inside each end of the body.
            engagement = num(row["E"])
            return {"PSize": dn, "PRating": row.get("Vtype", "Ball_Threaded"),
                    "OD": num(row["OD"]), "ODBody": num(row["ODBody"]),
                    "Height": length + 2.0 * engagement, "E": engagement,
                    "Conn": pcf_map.conn_from_skey(comp.skey),
                    "Actuator": "Handwheel" if family in ("Gate", "Globe") else "Handle"}

    hint = _flange_class(comp, ctx)
    best = None
    for cls in pcf_map.FLANGED_CLASSES:
        row = find_row("Valve_%s_%sRF.csv" % (family, cls), PSize=dn)
        if not row:
            continue
        score = (0 if cls == hint else 1, abs(num(row["H"]) - length))
        if best is None or score < best[0]:
            best = (score, cls, row)
    if best is not None:
        _score, cls, row = best
        props = {"PSize": dn, "PRating": row.get("VType", family), "Height": length,
                 "Kv": num(row.get("Kv")), "Conn": cls, "BottomH": num(row.get("BottomH")),
                 "TopH": num(row.get("TopH")), "WheelD": num(row.get("WheelD")),
                 "Actuator": "Handwheel" if family in ("Gate", "Globe") else "Handle"}
        props.update(_blind_flange_props(cls, dn))
        return props

    # Generic two-cone valve (P&ID style) as a last resort.
    for fname in files_matching(r"Valve_.*generic\.csv$"):
        if family.lower().split("_")[0] in fname.lower():
            row = find_row(fname, PSize=dn)
            if row:
                return {"PSize": dn, "PRating": row["VType"], "ODBody": num(row["ODBody"]),
                        "ID": num(row["ID"]), "Height": length, "Kv": num(row.get("Kv"))}
    import pFeatures
    od = pFeatures.pipe_OD.get(dn)
    if not od:
        raise ResolveError("no valve data for %s" % dn)
    return {"PSize": dn, "PRating": family.lower(), "ODBody": od * 1.3, "ID": od * 0.9,
            "Height": length, "Kv": 0.0}


def _gasket_row(cls, dn):
    return find_row("Gasket_%s.csv" % cls, PSize=dn)


def _gasket(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    cls = _flange_class(comp, ctx) or DEFAULT_CLASS
    row = _gasket_row(cls, dn)
    if not row:
        raise ResolveError("no %s gasket data for %s" % (cls, dn))
    props = {k: num(row[k]) for k in ("IRID", "SEID", "SEOD", "CROD", "SEthk", "Rthk")}
    props.update(PSize=dn, PRating=cls, FClass=cls)
    return props


def _bolts(comp, ctx):
    dn = ctx.dn(comp.co_ords)
    cls = _flange_class(comp, ctx) or DEFAULT_CLASS
    row = find_row("Bolt_%s.csv" % cls, PSize=dn)
    if not row:
        raise ResolveError("no %s bolt data for %s" % (cls, dn))
    props = {k: num(row[k]) for k in ("dBolt", "dNut", "tNut", "df", "lBolt")}
    props["n"] = int(num(row["n"]))
    gasket = _gasket_row(cls, dn)
    props["SEthk"] = num(gasket["SEthk"]) if gasket else 4.5
    if comp.attr("BOLT-DIA"):
        props["dBolt"] = num(comp.attr("BOLT-DIA"), props["dBolt"])
    if comp.attr("BOLT-LENGTH"):
        props["lBolt"] = num(comp.attr("BOLT-LENGTH"), props["lBolt"])
    props.update(PSize=dn, PRating=cls, FClass=cls)
    return props


def _outlet(comp, ctx):
    if comp.centre_point is None or not comp.branch_points:
        raise ResolveError("olet without CENTRE-POINT/BRANCH1-POINT")
    dn = ctx.dn(comp.branch_points[0])
    conn = {"SW": "SW", "SC": "TH"}.get(comp.skey[2:4], "BW")
    if conn != "BW":
        rating = _socket_class(comp, ctx)
        fname = "Outlet_%s.csv" % rating
        if conn == "TH" and table("Outlet_%s_TH.csv" % rating):
            fname = "Outlet_%s_TH.csv" % rating
            rating += "_TH"
    else:
        sched = _schedule(comp, ctx).replace("SCH-", "Sch-")
        fname = "Outlet_%s.csv" % sched
        if not table(fname):
            fname = "Outlet_Sch-STD.csv"
        rating = fname[len("Outlet_"):-len(".csv")]
    row = find_row(fname, PSize=dn)
    if not row:
        raise ResolveError("no olet data for %s in %s" % (dn, fname))
    props = {k: num(row[k]) for k in ("OD", "thk", "A", "B")}
    props.update(PSize=dn, PRating=rating, EndType=row.get("Conn", conn),
                 Angle=int(num(row.get("Ang"))), E=num(row.get("E")))
    # Carrier OD from the header pipe the olet sits on, else from the points
    # (the carrier surface sits A below the branch end).
    header = ctx.geometry.run_through(vec(comp.centre_point), comp) if ctx.geometry else None
    if header is not None:
        props["CarrierOD"] = _pipe_dims(ctx.dn(header.end_points[0]), _schedule(header, ctx))[0]
    else:
        carrier_r = dist(comp.branch_points[0], comp.centre_point) - props["A"]
        props["CarrierOD"] = max(2.0 * carrier_r, 0.0)
    return props


def _coupling(comp, ctx):
    dn, dn2 = ctx.dn(comp.end_points[0]), ctx.dn(comp.end_points[1])
    fname, cls = _socket_table("Coupling", comp, ctx)
    row = find_row(fname, PSize=dn, PSize2=dn2)
    if not row:
        raise ResolveError("no coupling data for %s x %s %s" % (dn, dn2, cls))
    props = {k: num(row[k]) for k in ("OD", "OD2", "A", "C", "D", "E")}
    props.update(PSize=dn, PSize2=dn2, PRating=cls, Conn=pcf_map.conn_from_skey(comp.skey))
    return props


def _union(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    fname, cls = _socket_table("Union", comp, ctx)
    table(fname, header=UNION_COLUMNS)
    row = find_row(fname, PSize=dn)
    if not row:
        raise ResolveError("no union data for %s %s" % (dn, cls))
    props = {k: num(row[k]) for k in ("OD", "A", "C", "D", "E")}
    props.update(PSize=dn, PRating=cls, Conn=pcf_map.conn_from_skey(comp.skey))
    return props


def _hex_bushing(comp, ctx):
    dn, dn2 = ctx.dn(comp.end_points[0]), ctx.dn(comp.end_points[1])
    row = find_row("Bushing_B16.11.csv", PSize=dn, PSize2=dn2)
    if not row:
        raise ResolveError("no hex bushing data for %s x %s" % (dn, dn2))
    props = {k: num(row[k]) for k in ("OD", "OD2", "F", "C", "L", "L2", "D")}
    props.update(PSize=dn, PSize2=dn2, PRating="B16.11", Conn="TH")
    return props


def _hex_plug(comp, ctx):
    dn = ctx.dn(comp.end_points[0])
    row = find_row("Plug_B16.11.csv", PSize=dn)
    if not row:
        raise ResolveError("no hex plug data for %s" % dn)
    props = {k: num(row[k]) for k in ("OD", "F", "C", "L")}
    props.update(PSize=dn, PRating="B16.11", Conn="TH")
    return props


_RESOLVERS = {
    "Pipe": _pipe,
    "Elbow": _elbow,
    "SocketEll": _socket_elbow,
    "Tee": _tee,
    "SocketTee": _socket_tee,
    "Reduct": _reduct,
    "Cap": _cap,
    "SocketCap": _socket_cap,
    "Flange": _flange,
    "Valve": _valve,
    "Gasket": _gasket,
    "Bolts_Nuts": _bolts,
    "Outlet": _outlet,
    "SocketCoupling": _coupling,
    "SocketUnion": _union,
    "HexBushing": _hex_bushing,
    "HexPlug": _hex_plug,
}
