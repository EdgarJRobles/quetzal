# SPDX-License-Identifier: LGPL-3.0-or-later
"""Mapping between Quetzal objects and PCF keywords / SKEYs.

SKEYs follow the common Isogen conventions: two letters for the component
family followed by two letters for the end connection (BW = butt weld,
SW = socket weld, SC = screwed, FL = flanged).  Families without a widely
agreed SKEY use a generic code; edit the tables below to suit a particular
Isogen/CAESAR II configuration.
"""

import json
import re

import quetzal_units

# Attribute holding the Quetzal round-trip record (PType, sizes, dimensions and
# rotation) as compact JSON.  A high attribute number keeps clear of the low
# numbers stress packages map to pressure, temperature, material, etc.
QUETZAL_ATTRIBUTE = "COMPONENT-ATTRIBUTE99"
QUETZAL_TAG = "QUETZAL"

FLANGED_CLASSES = ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb")

# Quetzal objects that are exported, and their PCF keyword.
KEYWORDS = {
    "Pipe": "PIPE",
    "Elbow": "ELBOW",
    "SocketEll": "ELBOW",
    "Tee": "TEE",
    "SocketTee": "TEE",
    "Reduct": "REDUCER-CONCENTRIC",  # REDUCER-ECCENTRIC when conc is False
    "Cap": "CAP",
    "SocketCap": "CAP",
    "Flange": "FLANGE",  # FLANGE-BLIND for FlangeType BL
    "Valve": "VALVE",
    "Gasket": "GASKET",
    "Bolts_Nuts": "BOLT",
    "Outlet": "OLET",
    "SocketCoupling": "COUPLING",
    "SocketUnion": "UNION",
    "HexBushing": "REDUCER-CONCENTRIC",
    "HexPlug": "CAP",
    "Clamp": "SUPPORT",
}

# PCF keyword -> Quetzal PType for butt-weld / default ends.
PTYPES = {
    "PIPE": "Pipe",
    "ELBOW": "Elbow",
    "BEND": "Elbow",
    "TEE": "Tee",
    "REDUCER-CONCENTRIC": "Reduct",
    "REDUCER-ECCENTRIC": "Reduct",
    "CAP": "Cap",
    "FLANGE": "Flange",
    "FLANGE-BLIND": "Flange",
    "VALVE": "Valve",
    "GASKET": "Gasket",
    "BOLT": "Bolts_Nuts",
    "OLET": "Outlet",
    "COUPLING": "SocketCoupling",
    "UNION": "SocketUnion",
    "SUPPORT": "Clamp",
}

# Socket-weld / screwed variants of the butt-weld PTypes.
SOCKET_PTYPES = {"Elbow": "SocketEll", "Tee": "SocketTee", "Cap": "SocketCap"}

# SKEY family prefix -> PType, for families that share a PCF keyword with
# another Quetzal object (a bushing is a reducer, a plug is a cap).
SKEY_PTYPES = {("REDUCER-CONCENTRIC", "BU"): "HexBushing", ("CAP", "PL"): "HexPlug"}

FLANGE_SKEYS = {"WN": "FLWN", "SO": "FLSO", "SW": "FLSW", "LJ": "FLLJ", "BL": "FLBL"}
FLANGE_TYPES = {v: k for k, v in FLANGE_SKEYS.items()}
FLANGE_TYPES["FLLP"] = "LJ"
FLANGE_TYPES["FLRF"] = "WN"

# Valve family: (substring of Quetzal VType/PRating, SKEY prefix, catalog family)
VALVE_FAMILIES = (
    ("check", "VC", "Check_Swing"),
    ("gate", "VT", "Gate"),
    ("plug", "VP", "Plug"),
    ("globe", "VG", "Globe"),
    ("butterfly", "VY", "Butterfly"),
    ("ball", "VB", "Ball"),
)
VALVE_GENERIC_SKEY = "VV"

OLET_SKEYS = {"BW": "WTBW", "SW": "SKSW", "TH": "THSC"}

_CONN_TO_END = {"SW": "SW", "TH": "SC", "BW": "BW"}
_END_TO_CONN = {"SW": "SW", "SC": "TH", "TH": "TH", "BW": "BW"}


def end_type(obj):
    """Return the PCF end-connection code (BW/SW/SC/FL) of a Quetzal object."""
    conn = str(getattr(obj, "Conn", "") or getattr(obj, "EndType", "")).strip()
    if conn in FLANGED_CLASSES:
        return "FL"
    if conn in _CONN_TO_END:
        return _CONN_TO_END[conn]
    if conn in ("SocketWeld",):
        return "SW"
    if obj.PType == "Valve":
        return "FL"
    return "BW"


def conn_from_skey(skey, default="SW"):
    """Map the end part of an SKEY to a Quetzal Conn value (SW/TH/BW)."""
    return _END_TO_CONN.get(skey[2:4].upper(), default) if len(skey) >= 4 else default


def keyword_and_skey(obj):
    """Return (PCF keyword, SKEY) for a Quetzal object, or (None, None)."""
    ptype = obj.PType
    kw = KEYWORDS.get(ptype)
    if kw is None:
        return None, None
    end = end_type(obj)
    if ptype in ("Elbow", "SocketEll"):
        return kw, "EL" + end
    if ptype in ("Tee", "SocketTee"):
        return kw, "TE" + end
    if ptype == "Reduct":
        if getattr(obj, "conc", True):
            return kw, "RCBW"
        return "REDUCER-ECCENTRIC", "REBW"
    if ptype in ("Cap", "SocketCap"):
        return kw, "KA" + end
    if ptype == "Flange":
        ftype = str(obj.FlangeType).upper()
        if ftype == "BL":
            return "FLANGE-BLIND", "FLBL"
        return kw, FLANGE_SKEYS.get(ftype, "FLWN")
    if ptype == "Valve":
        return kw, valve_skey_prefix(obj.PRating) + end
    if ptype == "Outlet":
        return kw, OLET_SKEYS.get(str(obj.EndType), "WTBW")
    if ptype == "SocketCoupling":
        return kw, "CP" + end
    if ptype == "SocketUnion":
        return kw, "UN" + end
    if ptype == "HexBushing":
        return kw, "BU" + end
    if ptype == "HexPlug":
        return kw, "PL" + end
    return kw, ""


def valve_skey_prefix(vtype):
    v = str(vtype).lower()
    for key, prefix, _family in VALVE_FAMILIES:
        if key in v:
            return prefix
    return VALVE_GENERIC_SKEY


def valve_family_from_skey(skey):
    prefix = skey[:2].upper()
    for _key, p, family in VALVE_FAMILIES:
        if p == prefix:
            return family
    return None


def ptype_for(comp):
    """Quetzal PType a PCF component should become, or None if unsupported."""
    special = SKEY_PTYPES.get((comp.keyword, comp.skey[:2].upper()))
    if special:
        return special
    ptype = PTYPES.get(comp.keyword)
    if ptype in SOCKET_PTYPES and comp.skey[2:4] in ("SW", "SC"):
        return SOCKET_PTYPES[ptype]
    return ptype


# --------------------------------------------------------------------------
# Bore <-> nominal size
# --------------------------------------------------------------------------


def _nps_to_inch(nps):
    """'1-1/4' -> 1.25, '2' -> 2.0, '3/4' -> 0.75"""
    total = 0.0
    for part in nps.split("-"):
        if "/" in part:
            num, den = part.split("/")
            total += float(num) / float(den)
        else:
            total += float(part)
    return total


_DN_TO_INCH = {dn: _nps_to_inch(nps) for dn, nps in quetzal_units._DN_TO_NPS.items()}


def dn_number(psize):
    """'DN50' -> 50, or None when psize is not a DN designation."""
    m = re.match(r"^\s*DN\s*(\d+)\s*$", str(psize), re.IGNORECASE)
    return int(m.group(1)) if m else None


def bore_for(psize, units_bore):
    """Nominal bore of a Quetzal PSize in the PCF bore unit (0 if unknown)."""
    n = dn_number(psize)
    if n is None:
        return 0.0
    if units_bore == "INCH":
        return _DN_TO_INCH.get("DN%d" % n, n / 25.0)
    return float(n)


def dn_for(bore, units_bore):
    """Nearest standard DN for a PCF bore value, e.g. 2 (INCH) -> 'DN50'."""
    if bore <= 0:
        return None
    if units_bore in ("INCH", "INCHES", "IN"):
        return min(_DN_TO_INCH, key=lambda dn: abs(_DN_TO_INCH[dn] - bore))
    return min(_DN_TO_INCH, key=lambda dn: abs(dn_number(dn) - bore))


# --------------------------------------------------------------------------
# Round-trip record
# --------------------------------------------------------------------------

_SKIP_GROUPS = {"", "Base", "PBase", "Attachment"}
_SIMPLE_TYPES = {
    "App::PropertyLength",
    "App::PropertyDistance",
    "App::PropertyFloat",
    "App::PropertyInteger",
    "App::PropertyAngle",
    "App::PropertyString",
    "App::PropertyBool",
}
_DERIVED = {"Profile"}


def _plain(value):
    if hasattr(value, "Value"):  # Quantity
        value = value.Value
    if isinstance(value, float):
        return round(value, 6)
    return value


def quetzal_record(obj):
    """Dimensions needed to rebuild obj exactly, as a dict.

    Collects PType/PRating/PSize/Kv plus every simple property the object's
    own class added (its non-base property groups), and the rotation.
    """
    rec = {"PType": obj.PType, "PSize": obj.PSize}
    for name in ("PRating", "Kv"):
        if hasattr(obj, name):
            rec[name] = _plain(getattr(obj, name))
    for name in obj.PropertiesList:
        if name in rec or name in _DERIVED:
            continue
        if obj.getGroupOfProperty(name) in _SKIP_GROUPS:
            continue
        if obj.getTypeIdOfProperty(name) not in _SIMPLE_TYPES:
            continue
        if name == "ID" and hasattr(obj, "thk"):
            continue  # derived from OD and thk
        rec[name] = _plain(getattr(obj, name))
    rec["Rot"] = [round(q, 9) for q in obj.getGlobalPlacement().Rotation.Q]
    return rec


def encode_record(rec):
    return QUETZAL_TAG + json.dumps(rec, separators=(",", ":"), sort_keys=True)


def decode_record(comp):
    """Return the Quetzal record stored on a PCF component, or None."""
    value = comp.attr(QUETZAL_ATTRIBUTE)
    if not value or not value.startswith(QUETZAL_TAG):
        return None
    try:
        return json.loads(value[len(QUETZAL_TAG):])
    except ValueError:
        return None
