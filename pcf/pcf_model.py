# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pure-Python model, parser and writer for PCF (Piping Component File).

A PCF is a line-based text format.  Top-level (non-indented) lines are
keywords that open a block: global header items, PIPELINE-REFERENCE,
MATERIALS, or a component (PIPE, ELBOW, TEE, ...).  Indented lines are
attributes of the block opened last.

This module has no FreeCAD dependency so it can be unit-tested with plain
Python.
"""

from dataclasses import dataclass, field

# Keywords that are attributes of a block even when they appear without
# indentation (some writers do not indent).
_ATTRIBUTE_KEYWORDS = {
    "END-POINT",
    "CENTRE-POINT",
    "CENTER-POINT",
    "BRANCH1-POINT",
    "BRANCH2-POINT",
    "CO-ORDS",
    "SKEY",
    "DESCRIPTION",
}

# Global header keywords written before PIPELINE-REFERENCE.
HEADER_KEYWORDS = (
    "ISOGEN-FILES",
    "UNITS-BORE",
    "UNITS-CO-ORDS",
    "UNITS-WEIGHT",
    "UNITS-BOLT-DIA",
    "UNITS-BOLT-LENGTH",
)

MM_PER_INCH = 25.4


@dataclass
class PcfPoint:
    """A point with optional bore and trailing tokens (end connection etc.)."""

    x: float
    y: float
    z: float
    bore: float = 0.0
    extra: list = field(default_factory=list)

    def xyz(self):
        return (self.x, self.y, self.z)


@dataclass
class PcfComponent:
    keyword: str
    end_points: list = field(default_factory=list)
    centre_point: PcfPoint = None
    branch_points: list = field(default_factory=list)
    co_ords: PcfPoint = None
    skey: str = ""
    item_code: str = ""
    # Every other attribute, in file order: list of (KEY, value-string).
    attributes: list = field(default_factory=list)

    def attr(self, key, default=None):
        """Return the first value of attribute key (case-insensitive)."""
        key = key.upper()
        for k, v in self.attributes:
            if k == key:
                return v
        return default


@dataclass
class PcfFile:
    """One pipeline worth of PCF data."""

    header: dict = field(default_factory=dict)
    pipeline_reference: str = ""
    pipeline_attributes: list = field(default_factory=list)
    materials: dict = field(default_factory=dict)  # item-code -> description
    components: list = field(default_factory=list)

    @property
    def units_bore(self):
        return self.header.get("UNITS-BORE", "MM").upper()

    @property
    def units_coords(self):
        return self.header.get("UNITS-CO-ORDS", "MM").upper()

    def pipeline_attr(self, key, default=None):
        key = key.upper()
        for k, v in self.pipeline_attributes:
            if k == key:
                return v
        return default


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def _parse_point(value, with_bore=True):
    tokens = value.split()
    if len(tokens) < 3:
        raise ValueError("expected at least 3 coordinates, got %r" % value)
    x, y, z = (float(t) for t in tokens[:3])
    bore = 0.0
    extra = tokens[3:]
    if with_bore and extra:
        try:
            bore = float(extra[0])
            extra = extra[1:]
        except ValueError:
            pass
    return PcfPoint(x, y, z, bore, list(extra))


def _split(line):
    stripped = line.strip()
    parts = stripped.split(None, 1)
    key = parts[0].upper()
    value = parts[1].strip() if len(parts) > 1 else ""
    return key, value


def _apply_component_attr(comp, key, value):
    if key == "END-POINT":
        comp.end_points.append(_parse_point(value))
    elif key in ("CENTRE-POINT", "CENTER-POINT"):
        comp.centre_point = _parse_point(value, with_bore=False)
    elif key in ("BRANCH1-POINT", "BRANCH2-POINT"):
        comp.branch_points.append(_parse_point(value))
    elif key == "CO-ORDS":
        comp.co_ords = _parse_point(value)
    elif key == "SKEY":
        comp.skey = value.upper()
    elif key == "ITEM-CODE":
        comp.item_code = value
    else:
        comp.attributes.append((key, value))


def parse(text):
    """Parse PCF text and return a list of PcfFile, one per pipeline.

    Header items that precede the first PIPELINE-REFERENCE are shared by all
    pipelines in the file.  Unknown keywords are kept as attributes, so no
    data is silently lost.  Coordinates and bores are returned exactly as
    written; see to_mm() for unit conversion.
    """
    files = []
    header = {}
    current_file = None
    block = None  # ("header"|"pipeline"|"materials"|"material"|"component", obj)
    in_materials = False
    material_code = None

    def ensure_file():
        nonlocal current_file
        if current_file is None:
            current_file = PcfFile(header=dict(header))
            files.append(current_file)
        return current_file

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith(("!", "#")):
            continue
        indented = line[:1] in (" ", "\t")
        key, value = _split(line)

        try:
            if indented or key in _ATTRIBUTE_KEYWORDS:
                kind = block[0] if block else None
                if kind == "component":
                    _apply_component_attr(block[1], key, value)
                elif kind == "pipeline":
                    block[1].pipeline_attributes.append((key, value))
                elif kind == "material" and key == "DESCRIPTION":
                    pf = ensure_file()
                    old = pf.materials.get(material_code, "")
                    pf.materials[material_code] = (old + " " + value).strip()
                # Attributes of other blocks (header items) are ignored.
                continue

            # ---- top-level keyword ----
            if key in HEADER_KEYWORDS and current_file is None:
                header[key] = value
                block = ("header", None)
            elif key in HEADER_KEYWORDS:
                current_file.header[key] = value
                block = ("header", None)
            elif key == "PIPELINE-REFERENCE":
                if current_file is not None and (
                    current_file.pipeline_reference or current_file.components
                ):
                    current_file = None
                pf = ensure_file()
                pf.pipeline_reference = value
                block = ("pipeline", pf)
                in_materials = False
            elif key == "MATERIALS":
                ensure_file()
                in_materials = True
                block = ("materials", None)
            elif key == "ITEM-CODE" and in_materials:
                material_code = value
                ensure_file().materials.setdefault(value, "")
                block = ("material", None)
            else:
                in_materials = False
                comp = PcfComponent(keyword=key)
                ensure_file().components.append(comp)
                block = ("component", comp)
        except ValueError as e:
            raise ValueError("PCF line %d: %s" % (lineno, e))

    return files


def to_mm(pcf_file):
    """Convert coordinates of pcf_file to millimetres in place.

    Bores are left untouched; interpret them with pcf_file.units_bore.
    """
    if pcf_file.units_coords not in ("INCH", "INCHES", "IN"):
        return pcf_file
    f = MM_PER_INCH
    for c in pcf_file.components:
        pts = list(c.end_points) + list(c.branch_points)
        pts += [p for p in (c.centre_point, c.co_ords) if p is not None]
        for p in pts:
            p.x, p.y, p.z = p.x * f, p.y * f, p.z * f
    pcf_file.header["UNITS-CO-ORDS"] = "MM"
    return pcf_file


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

_INDENT = "    "


def _fmt_num(v, decimals=4):
    return ("%%.%df" % decimals) % (round(v, decimals) + 0.0)  # + 0.0 drops "-0"


def _fmt_point(p, bore=True):
    s = " ".join(_fmt_num(v) for v in (p.x, p.y, p.z))
    if bore:
        s += " " + _fmt_bore(p.bore)
    if p.extra:
        s += " " + " ".join(p.extra)
    return s


def _fmt_bore(b):
    if abs(b - round(b)) < 1e-9:
        return "%d" % round(b)
    return ("%.4f" % b).rstrip("0").rstrip(".")


def write(pcf_file):
    """Return PCF text for one PcfFile."""
    out = []
    header = dict(pcf_file.header)
    header.setdefault("ISOGEN-FILES", "ISOGEN.FLS")
    header.setdefault("UNITS-BORE", "MM")
    header.setdefault("UNITS-CO-ORDS", "MM")
    for key in HEADER_KEYWORDS:
        if key in header:
            out.append("%s %s" % (key, header[key]))
    for key, value in header.items():
        if key not in HEADER_KEYWORDS:
            out.append("%s %s" % (key, value))

    out.append("PIPELINE-REFERENCE %s" % pcf_file.pipeline_reference)
    for key, value in pcf_file.pipeline_attributes:
        out.append(_INDENT + ("%s %s" % (key, value)).rstrip())

    if pcf_file.materials:
        out.append("MATERIALS")
        for code, desc in pcf_file.materials.items():
            out.append("ITEM-CODE %s" % code)
            if desc:
                out.append(_INDENT + "DESCRIPTION %s" % desc)

    for c in pcf_file.components:
        out.append(c.keyword)
        for p in c.end_points:
            out.append(_INDENT + "END-POINT " + _fmt_point(p))
        if c.centre_point is not None:
            out.append(_INDENT + "CENTRE-POINT " + _fmt_point(c.centre_point, bore=False))
        for i, p in enumerate(c.branch_points, 1):
            out.append(_INDENT + "BRANCH%d-POINT " % i + _fmt_point(p))
        if c.co_ords is not None:
            out.append(_INDENT + "CO-ORDS " + _fmt_point(c.co_ords))
        if c.skey:
            out.append(_INDENT + "SKEY " + c.skey)
        if c.item_code:
            out.append(_INDENT + "ITEM-CODE " + c.item_code)
        for key, value in c.attributes:
            out.append(_INDENT + ("%s %s" % (key, value)).rstrip())
    return "\n".join(out) + "\n"
