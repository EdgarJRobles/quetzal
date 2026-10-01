# SPDX-License-Identifier: LGPL-3.0-or-later
"""Small 3D vector helpers on plain (x, y, z) tuples (no FreeCAD dependency)."""

import math


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def length(a):
    return math.sqrt(dot(a, a))


def dist(a, b):
    return length(sub(a, b))


def unit(a):
    n = length(a)
    return (0.0, 0.0, 0.0) if n < 1e-12 else scale(a, 1.0 / n)


def segment_param(point, a, b, tol):
    """Parameter t in [0, 1] of point on segment a-b, or None if point is
    farther than tol from the segment."""
    ab = sub(b, a)
    den = dot(ab, ab)
    if den < 1e-12:
        return None
    t = dot(sub(point, a), ab) / den
    if t < -1e-3 or t > 1 + 1e-3:
        return None
    if dist(add(a, scale(ab, t)), point) > tol:
        return None
    return min(max(t, 0.0), 1.0)
