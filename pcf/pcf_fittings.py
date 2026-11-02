# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pipe size tables and fitting designations (pure Python, no FreeCAD)."""

from dataclasses import dataclass

# Nominal pipe size in inches for each DN (ASME B36.10 / ISO 6708).
DN_INCH = {
    6: 0.125, 8: 0.25, 10: 0.375, 15: 0.5, 20: 0.75, 25: 1, 32: 1.25, 40: 1.5,
    50: 2, 65: 2.5, 80: 3, 90: 3.5, 100: 4, 125: 5, 150: 6, 200: 8, 250: 10,
    300: 12, 350: 14, 400: 16, 450: 18, 500: 20, 550: 22, 600: 24, 650: 26,
    700: 28, 750: 30, 800: 32, 850: 34, 900: 36, 1000: 40, 1050: 42, 1200: 48,
}

# Outside diameter in inches (ASME B36.10; from NPS 14 up the OD equals the NPS).
_OD_INCH = {
    6: 0.405, 8: 0.540, 10: 0.675, 15: 0.840, 20: 1.050, 25: 1.315, 32: 1.660,
    40: 1.900, 50: 2.375, 65: 2.875, 80: 3.5, 90: 4.0, 100: 4.5, 125: 5.563,
    150: 6.625, 200: 8.625, 250: 10.75, 300: 12.75,
}

MM_PER_INCH = 25.4
RADIUS_TOL = 0.01  # a radius within 1 % of a standard one is that standard


def nearest_dn(dn_or_bore_mm):
    """Nearest standard DN number to a DN number or a bore in mm."""
    return min(DN_INCH, key=lambda d: abs(d - dn_or_bore_mm))


def nominal_mm(dn):
    return DN_INCH[nearest_dn(dn)] * MM_PER_INCH


def od_mm(dn):
    d = nearest_dn(dn)
    return _OD_INCH.get(d, DN_INCH[d]) * MM_PER_INCH


@dataclass
class ElbowDesignation:
    angle: float  # degrees, rounded to 0.1
    radius: float  # mm
    radius_class: str  # "LR", "SR", "3D", "6D", ... or "" for a custom radius

    @property
    def angle_text(self):
        """'90', '45', '22.5'"""
        return ("%.1f" % self.angle).rstrip("0").rstrip(".")

    @property
    def is_bend(self):
        """Not a standard LR/SR elbow: a pipe bend, which needs its radius stated."""
        return self.radius_class not in ("LR", "SR")

    @property
    def code(self):
        """Item-code suffix, e.g. '90-LR', '45-6D', '30-R500'."""
        return "%s-%s" % (self.angle_text, self.radius_class or "R%d" % round(self.radius))


def _multiple(ratio):
    """(relative error, step) for ratio rounded to a whole or half multiple,
    or None if it is not one within RADIUS_TOL."""
    step = round(ratio * 2) / 2
    error = abs(ratio - step) / step if step else 1.0
    if step >= 1 and error <= RADIUS_TOL:
        return error, step
    return None


def elbow_designation(angle_deg, radius_mm, dn):
    """Classify an elbow by its bend radius.

    LR = 1.5 x NPS and SR = 1.0 x NPS (butt-weld elbows).  Anything else is a
    pipe bend: 'nD' where the radius is a whole or half multiple of the
    nominal size or of the pipe OD, whichever fits more closely (both
    conventions are in use: a DN200 6D bend is 6 x 8.625" OD = 1314.45 mm,
    which is 6.47 x nominal); otherwise a custom radius."""
    nominal = nominal_mm(dn)
    ratio = radius_mm / nominal if nominal else 0.0
    if abs(ratio - 1.5) <= 1.5 * RADIUS_TOL:
        cls = "LR"
    elif abs(ratio - 1.0) <= RADIUS_TOL:
        cls = "SR"
    else:
        fits = [m for m in (_multiple(ratio), _multiple(radius_mm / od_mm(dn))) if m]
        cls = ("%gD" % min(fits)[1]) if fits else ""
    return ElbowDesignation(round(angle_deg, 1), radius_mm, cls)
