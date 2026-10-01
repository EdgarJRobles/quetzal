# SPDX-License-Identifier: LGPL-3.0-or-later
"""Import PCF files as Quetzal piping objects.

FreeCAD calls open(filename) / insert(filename, docname) from File > Open
and File > Import.

Components written by Quetzal carry a round-trip record (see
pcf_map.QUETZAL_ATTRIBUTE) and are rebuilt exactly.  Other components are
matched against the tablez catalogs (pcf_catalog) and sized from the PCF
points.  Every object is then placed so its ports land on the PCF points.
"""

import builtins
import os

import FreeCAD

import pCmd
import pFeatures

from . import pcf_catalog, pcf_geom, pcf_map, pcf_model

translate = FreeCAD.Qt.translate
V = FreeCAD.Vector

PORT_TOLERANCE = 0.5  # mm
NEIGHBOUR_TOLERANCE = 1.0  # mm


def _log(msg):
    FreeCAD.Console.PrintMessage("PCF import: " + msg + "\n")


def _warn(msg):
    FreeCAD.Console.PrintWarning("PCF import: " + msg + "\n")


# --------------------------------------------------------------------------
# Builders: create an object from a property dict (record or catalog)
# --------------------------------------------------------------------------


def _g(props, key, default=0.0):
    value = props.get(key, default)
    return default if value is None else value


def _build_pipe(p):
    return pCmd.makePipe(p["PRating"], [p["PSize"], _g(p, "OD"), _g(p, "thk"), _g(p, "Height")])


def _build_elbow(p):
    return pCmd.makeElbow([p["PSize"], _g(p, "OD"), _g(p, "thk"), _g(p, "BendAngle", 90),
                           _g(p, "BendRadius")], rating=p["PRating"])


def _build_socket_elbow(p):
    return pCmd.makeSocketElbow([p["PSize"], _g(p, "OD"), _g(p, "BendAngle", 90), _g(p, "A"),
                                 _g(p, "C"), _g(p, "D"), _g(p, "E"), _g(p, "G"),
                                 _g(p, "Conn", "SW")], rating=p["PRating"])


def _build_tee(p):
    return pCmd.makeTee([p["PSize"], _g(p, "OD"), _g(p, "OD2"), _g(p, "thk"), _g(p, "thk2"),
                         _g(p, "C"), _g(p, "M"), _g(p, "PSizeBranch", "")], rating=p["PRating"])


def _build_socket_tee(p):
    return pCmd.makeSocketTee([p["PSize"], _g(p, "PSizeBranch", p["PSize"]), _g(p, "OD"),
                               _g(p, "OD2"), _g(p, "A"), _g(p, "C"), _g(p, "D"), _g(p, "E"),
                               _g(p, "G"), _g(p, "Conn", "SW")], rating=p["PRating"])


def _build_reduct(p):
    props = [p["PSize"], _g(p, "OD"), _g(p, "OD2"), _g(p, "thk"), _g(p, "thk2"), _g(p, "Height")]
    if p.get("PSize2"):
        props.append(p["PSize2"])
    return pCmd.makeReduct(props, conc=bool(p.get("conc", True)), rating=p["PRating"])


def _build_cap(p):
    return pCmd.makeCap([p["PSize"], _g(p, "OD"), _g(p, "thk")], rating=p["PRating"])


def _build_socket_cap(p):
    return pCmd.makeSocketCap([p["PSize"], _g(p, "OD"), _g(p, "A"), _g(p, "C"), _g(p, "E"),
                               _g(p, "Conn", "SW")])


def _build_flange(p):
    keys = ("D", "d", "df", "f", "t", "n", "trf", "drf", "twn", "dwn", "ODp", "R", "T1", "B2", "Y")
    props = [p["PSize"], p.get("FlangeType", "WN")] + [_g(p, k) for k in keys]
    props[7] = int(props[7])  # n
    return pCmd.makeFlange(props, doOffset=True, rating=p["PRating"], fclass=p.get("FClass", ""))


def _build_valve(p):
    conn = str(p.get("Conn", "") or "")
    if conn in pcf_map.FLANGED_CLASSES:
        flg = [p["PSize"], "BL", _g(p, "FlgD"), _g(p, "Flgt"), _g(p, "FlgF"), int(_g(p, "FlgN", 0)),
               _g(p, "FlgDf"), _g(p, "FlgDrf"), _g(p, "FlgTrf")]
        return pCmd.makeValve(
            [p["PSize"], p["PRating"], _g(p, "Height"), _g(p, "Kv"), conn,
             _g(p, "BottomH"), _g(p, "TopH"), _g(p, "WheelD")],
            flgPropList=flg, actuator=p.get("Actuator", "Handle") or "Handle")
    if conn in ("SW", "TH"):
        return pCmd.makeValve([p["PSize"], p["PRating"], _g(p, "OD"), _g(p, "ODBody"),
                               _g(p, "Height"), _g(p, "E"), conn, _g(p, "Kv"),
                               _g(p, "E2", _g(p, "E")), p.get("Conn2") or conn],
                              actuator=p.get("Actuator", "Handle") or "Handle")
    return pCmd.makeValve([p["PSize"], p["PRating"], _g(p, "ODBody"), _g(p, "ID"),
                           _g(p, "Height"), _g(p, "Kv")])


def _build_gasket(p):
    cls = p.get("FClass") or p.get("PRating")
    return pCmd.makeGasket([p["PSize"], cls, _g(p, "IRID"), _g(p, "SEID"), _g(p, "SEOD"),
                            _g(p, "CROD"), _g(p, "SEthk"), _g(p, "Rthk")])


def _build_bolts(p):
    cls = p.get("FClass") or p.get("PRating")
    return pCmd.makeBolts_Nuts([p["PSize"], cls, _g(p, "dBolt"), _g(p, "dNut"), _g(p, "tNut"),
                                _g(p, "df"), int(_g(p, "n", 4)), _g(p, "lBolt"), _g(p, "SEthk")])


def _build_outlet(p):
    return pCmd.makeOutlet([p["PRating"], p["PSize"], _g(p, "OD"), _g(p, "thk"), _g(p, "A"),
                            _g(p, "B"), _g(p, "EndType", "BW"), int(_g(p, "Angle", 0)), _g(p, "E")],
                           carrierOD=_g(p, "CarrierOD"))


def _build_socket_coupling(p):
    return pCmd.makeSocketCoupling([p["PSize"], _g(p, "PSize2", p["PSize"]), _g(p, "OD"),
                                    _g(p, "OD2"), _g(p, "A"), _g(p, "C"), _g(p, "D"), _g(p, "E"),
                                    _g(p, "Conn", "SW")])


def _build_socket_union(p):
    return pCmd.makeSocketUnion([p["PSize"], _g(p, "OD"), _g(p, "A"), _g(p, "C"), _g(p, "D"),
                                 _g(p, "E"), _g(p, "Conn", "SW")])


def _build_hex_bushing(p):
    return pCmd.makeHexBushing([p["PSize"], _g(p, "PSize2", p["PSize"]), _g(p, "OD"), _g(p, "OD2"),
                                _g(p, "F"), _g(p, "C"), _g(p, "L"), _g(p, "L2"), _g(p, "D"),
                                _g(p, "Conn", "TH")])


def _build_hex_plug(p):
    return pCmd.makeHexPlug([p["PSize"], _g(p, "OD"), _g(p, "F"), _g(p, "C"), _g(p, "L"),
                             _g(p, "Conn", "TH")])


def _build_clamp(p):
    if p.get("ClampType", "") and "Beam" in p.get("ClampType", ""):
        raise pcf_catalog.ResolveError("beam clamps are not imported")
    return pCmd.makeUbolt([p["PSize"], p.get("ClampType", "DIN-UBolt"), _g(p, "C"), _g(p, "H"),
                           _g(p, "d")])


BUILDERS = {
    "Pipe": _build_pipe,
    "Elbow": _build_elbow,
    "SocketEll": _build_socket_elbow,
    "Tee": _build_tee,
    "SocketTee": _build_socket_tee,
    "Reduct": _build_reduct,
    "Cap": _build_cap,
    "SocketCap": _build_socket_cap,
    "Flange": _build_flange,
    "Valve": _build_valve,
    "Gasket": _build_gasket,
    "Bolts_Nuts": _build_bolts,
    "Outlet": _build_outlet,
    "SocketCoupling": _build_socket_coupling,
    "SocketUnion": _build_socket_union,
    "HexBushing": _build_hex_bushing,
    "HexPlug": _build_hex_plug,
    "Clamp": _build_clamp,
}


def _set_prop(obj, name, value):
    """Set obj.name to value, coercing to the property's current type."""
    if name in ("PType", "Rot") or not hasattr(obj, name):
        return
    current = getattr(obj, name)
    try:
        if isinstance(current, bool):
            value = value in (True, 1, "1", "True", "true")
        elif isinstance(current, int):
            value = int(float(value))
        elif isinstance(current, str):
            value = str(value)
        else:  # float or Quantity
            value = float(value)
            if abs(float(getattr(current, "Value", current)) - value) < 1e-9:
                return
        if current != value:
            setattr(obj, name, value)
    except (TypeError, ValueError) as e:
        _warn("%s.%s: cannot set %r (%s)" % (obj.Label, name, value, e))


# --------------------------------------------------------------------------
# Placement
# --------------------------------------------------------------------------


def _vec(p):
    return V(p.x, p.y, p.z)


def _frame(x, y):
    """Orthonormal (x, y, z) with x along x and y in the x-y plane."""
    x = V(x).normalize()
    z = x.cross(y)
    if z.Length < 1e-6:
        helper = V(0, 0, 1) if abs(x.z) < 0.9 else V(0, 1, 0)
        z = x.cross(helper)
    z.normalize()
    y = z.cross(x)
    return x, y, z


def _matrix(cols):
    x, y, z = cols
    return FreeCAD.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)


def rotation_between(local_x, local_y, world_x, world_y):
    """Rotation taking local_x onto world_x and the local x-y plane onto the world one."""
    ml = _matrix(_frame(local_x, local_y))
    mw = _matrix(_frame(world_x, world_y))
    ml.transpose()
    return FreeCAD.Rotation(mw.multiply(ml))


def _up_for(axis):
    """Default roll reference: world Z, or world Y for (near) vertical axes."""
    axis = V(axis).normalize()
    return V(0, 1, 0) if abs(axis.z) > 0.99 else V(0, 0, 1)


class PipelineGeometry:
    """End points of all components of one pipeline, for neighbour lookups."""

    def __init__(self, components):
        self.ends = []  # (component, point Vector, outward direction)
        for comp in components:
            centre = _vec(comp.centre_point) if comp.centre_point else None
            pts = [_vec(p) for p in comp.end_points]
            if centre is None and len(pts) == 2:
                centre = (pts[0] + pts[1]) * 0.5
            for p in pts + [_vec(b) for b in comp.branch_points]:
                if centre is not None and (p - centre).Length > 1e-6:
                    self.ends.append((comp, p, (p - centre).normalize()))
        self.straights = [c for c in components if len(c.end_points) == 2 and not c.branch_points]

    def _end_at(self, point, exclude):
        for comp, p, d in self.ends:
            if comp is not exclude and (p - point).Length <= NEIGHBOUR_TOLERANCE:
                return comp, d
        return None, None

    def outward_at(self, point, exclude):
        """Outward direction of another component's end at point, or None."""
        return self._end_at(point, exclude)[1]

    def neighbour_at(self, point, exclude):
        """The other component with an end at point, or None."""
        return self._end_at(point, exclude)[0]

    def run_through(self, point, exclude):
        """A straight component whose segment contains point, or None."""
        p = (point.x, point.y, point.z)
        for comp in self.straights:
            if comp is not exclude and pcf_geom.segment_param(
                    p, comp.end_points[0].xyz(), comp.end_points[1].xyz(),
                    NEIGHBOUR_TOLERANCE) is not None:
                return comp
        return None

    def run_axis_through(self, point, exclude):
        """Axis of a straight component whose segment contains point, or None."""
        comp = self.run_through(point, exclude)
        if comp is None:
            return None
        a, b = (_vec(p) for p in comp.end_points)
        return (b - a).normalize()


def correspondences(obj, ptype, comp):
    """[(local point, world point)] that must coincide; the first is the anchor."""
    ports = list(obj.Ports)
    ep = [_vec(p) for p in comp.end_points]
    if ptype in ("Bolts_Nuts", "Clamp"):
        return [(V(), _vec(comp.co_ords))]
    if ptype == "Outlet":
        carrier_centre = V(0, 0, -float(obj.CarrierOD) / 2.0)
        return [(ports[0], _vec(comp.branch_points[0])), (carrier_centre, _vec(comp.centre_point))]
    if ptype in ("Tee", "SocketTee"):
        return [(ports[0], ep[0]), (ports[1], ep[1]), (ports[2], _vec(comp.branch_points[0]))]
    if ptype in ("Cap", "SocketCap", "HexPlug"):
        return [(ports[0], ep[0])]
    return [(ports[0], ep[0]), (ports[1], ep[1])]


def solve_rotation(obj, ptype, comp, geometry):
    """Rotation for a component without a stored one (third-party files)."""
    ports = list(obj.Ports)
    ep = [_vec(p) for p in comp.end_points]

    if ptype in ("Elbow", "SocketEll"):
        c = _vec(comp.centre_point)
        return rotation_between(ports[0], ports[1], ep[0] - c, ep[1] - c)

    if ptype in ("Tee", "SocketTee"):
        bp = _vec(comp.branch_points[0])
        return rotation_between(ports[1] - ports[0], ports[2] - ports[0], ep[1] - ep[0], bp - ep[0])

    if ptype == "Outlet":
        c, bp = _vec(comp.centre_point), _vec(comp.branch_points[0])
        carrier_centre = V(0, 0, -float(obj.CarrierOD) / 2.0)
        axis = bp - c
        header = geometry.run_axis_through(c, comp) or _up_for(axis)
        return rotation_between(ports[0] - carrier_centre, V(0, 1, 0), axis, header)

    if ptype in ("Cap", "SocketCap", "HexPlug", "Bolts_Nuts") or (len(ep) == 2 and (ep[1] - ep[0]).Length < 1e-6):
        if ptype == "Bolts_Nuts":
            # Bolts sit mid-joint: take the axis of the gasket/flange spanning them.
            neighbour = geometry.run_axis_through(_vec(comp.co_ords), comp)
        else:
            neighbour = geometry.outward_at(ep[0], comp)
        if neighbour is None:
            raise pcf_catalog.ResolveError("cannot find the connected component to orient it")
        if ptype == "Bolts_Nuts":
            local_axis, world_axis = V(0, 0, 1), neighbour
        else:
            local_axis, world_axis = obj.PortDirections[0], -neighbour
        return rotation_between(local_axis, V(0, 1, 0), world_axis, _up_for(world_axis))

    # Straight two-port items: axis from the end points, stem/roll reference up.
    axis = ep[1] - ep[0]
    return rotation_between(ports[1] - ports[0], V(0, 1, 0), axis, _up_for(axis))


def place(obj, ptype, comp, rotation, geometry):
    """Place obj on the PCF points; return the largest remaining mismatch (mm)."""
    obj.Document.recompute()  # Ports are computed in execute()
    if rotation is None:
        rotation = solve_rotation(obj, ptype, comp, geometry)
    pairs = correspondences(obj, ptype, comp)
    local, world = pairs[0]
    obj.Placement = FreeCAD.Placement(world - rotation.multVec(local), rotation)
    return max((obj.Placement.multVec(l) - w).Length for l, w in pairs)


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


def _order_reducer(comp):
    """Quetzal reducers have the large end at port 0; PCF may list either end first."""
    if len(comp.end_points) == 2 and comp.end_points[0].bore < comp.end_points[1].bore:
        comp.end_points.reverse()


_FACE_NEIGHBOURS = {"GASKET", "FLANGE", "FLANGE-BLIND", "VALVE"}


def _order_flange(comp, geometry):
    """Quetzal flanges have the raised face at port 0.  PCF does not fix the
    order, so use an explicit FL/RF end token if present, otherwise put the
    end that meets a gasket/flange/valve (rather than pipe) first."""
    if len(comp.end_points) != 2:
        return

    def face_score(point):
        score = 2 if point.extra and point.extra[0].upper() in ("FL", "RF", "FF") else 0
        other = geometry.neighbour_at(_vec(point), comp)
        if other is not None:
            score += 1 if other.keyword in _FACE_NEIGHBOURS else -1
        return score

    if face_score(comp.end_points[1]) > face_score(comp.end_points[0]):
        comp.end_points.reverse()


def _make_pypeline(doc, pf, first_props):
    label = pf.pipeline_reference or os.path.splitext(doc.Label)[0]
    obj = doc.addObject("Part::FeaturePython", "PypeLine")
    pFeatures.PypeLine2(obj, first_props.get("PSize", "DN50"), first_props.get("PRating", ""),
                        float(first_props.get("OD", 60.3) or 60.3),
                        float(first_props.get("thk", 3.0) or 3.0), None, label)
    if FreeCAD.GuiUp:
        pFeatures.ViewProviderPypeLine(obj.ViewObject)
    return obj.getParentGroup()


class ImportReport:
    def __init__(self):
        self.created = 0
        self.skipped = {}  # reason -> count
        self.misplaced = []

    def skip(self, comp, reason):
        key = "%s: %s" % (comp.keyword, reason)
        self.skipped[key] = self.skipped.get(key, 0) + 1


def import_pipeline(doc, pf, report):
    pcf_model.to_mm(pf)
    geometry = PipelineGeometry(pf.components)
    ctx = pcf_catalog.Context(pf, geometry)
    group = None
    for n, comp in enumerate(pf.components, 1):
        ptype = pcf_map.ptype_for(comp)
        record = pcf_map.decode_record(comp)
        if record:
            ptype = record.get("PType", ptype)
        if ptype not in BUILDERS:
            report.skip(comp, "no Quetzal equivalent")
            continue
        try:
            if record:
                props = record
                rotation = FreeCAD.Rotation(*record["Rot"]) if "Rot" in record else None
            else:
                if ptype in ("Reduct", "HexBushing"):
                    _order_reducer(comp)
                elif ptype == "Flange":
                    _order_flange(comp, geometry)
                props = pcf_catalog.resolve(ptype, comp, ctx)
                rotation = None
            obj = BUILDERS[ptype](props)
        except (pcf_catalog.ResolveError, KeyError, IndexError, ValueError) as e:
            report.skip(comp, str(e))
            continue
        for name, value in props.items():
            _set_prop(obj, name, value)
        try:
            worst = place(obj, ptype, comp, rotation, geometry)
        except (pcf_catalog.ResolveError, IndexError, AttributeError) as e:
            doc.removeObject(obj.Name)
            report.skip(comp, str(e))
            continue
        if worst > PORT_TOLERANCE:
            report.misplaced.append("#%d %s %s (%.1f mm)" % (n, comp.keyword, obj.Label, worst))
        if group is None:
            group = _make_pypeline(doc, pf, props)
        group.addObject(obj)
        report.created += 1


def insert(filename, docname):
    """Import filename into document docname (FreeCAD importer API)."""
    doc = FreeCAD.getDocument(docname)
    FreeCAD.setActiveDocument(docname)
    with builtins.open(filename, encoding="utf-8", errors="replace") as f:
        files = pcf_model.parse(f.read())
    report = ImportReport()
    doc.openTransaction(translate("Transaction", "Import PCF"))
    try:
        for pf in files:
            import_pipeline(doc, pf, report)
    finally:
        doc.commitTransaction()
        doc.recompute()
    _log("%d components created from %s" % (report.created, os.path.basename(filename)))
    for reason, count in sorted(report.skipped.items()):
        _warn("skipped %d x %s" % (count, reason))
    for item in report.misplaced:
        _warn("ports off the PCF points by more than %.1f mm: %s" % (PORT_TOLERANCE, item))
    return report


def open(filename):
    """Open filename in a new document (FreeCAD importer API)."""
    name = os.path.splitext(os.path.basename(filename))[0]
    doc = FreeCAD.newDocument(name)
    insert(filename, doc.Name)
    return doc
