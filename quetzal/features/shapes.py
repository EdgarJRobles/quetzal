# SPDX-License-Identifier: LGPL-3.0-or-later
"""Small reusable shape primitives for feature builders."""

from __future__ import annotations

from math import cos, pi, sin

import FreeCAD
import Part


def make_regular_polygon(sides: int, radius: float):
    """Return a closed regular-polygon wire (circumscribed radius ``radius``)."""

    if sides < 3:
        raise ValueError("A polygon needs at least three sides")
    points = [
        FreeCAD.Vector(cos(2 * pi * index / sides) * radius, sin(2 * pi * index / sides) * radius)
        for index in range(sides + 1)
    ]
    return Part.makePolygon(points)
