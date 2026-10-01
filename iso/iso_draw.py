# SPDX-License-Identifier: LGPL-3.0-or-later
"""Drawing primitives in paper millimetres (Y up) and 2D collision tests."""

import math
from dataclasses import dataclass, field

W_PIPE = 0.6
W_SYMBOL = 0.35
W_THIN = 0.18
TEXT = 2.5
CHAR_W = 0.62  # average glyph width / font size for sans-serif capitals and digits


@dataclass
class Line:
    p1: tuple
    p2: tuple
    width: float = W_SYMBOL
    dash: bool = False


@dataclass
class Poly:
    points: list
    width: float = W_SYMBOL
    fill: bool = False
    closed: bool = True


@dataclass
class Circle:
    centre: tuple
    r: float
    width: float = W_SYMBOL
    fill: bool = False


@dataclass
class Text:
    pos: tuple  # anchor point on the baseline
    text: str
    size: float = TEXT
    angle: float = 0.0  # degrees, counter-clockwise, readable (-90, 90]
    anchor: str = "middle"  # start | middle | end
    bold: bool = False


@dataclass
class Drawing:
    items: list = field(default_factory=list)

    def add(self, *items):
        self.items.extend(items)


# --------------------------------------------------------------------------
# Vectors
# --------------------------------------------------------------------------


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def norm(a):
    return math.hypot(a[0], a[1])


def unit(a):
    n = norm(a)
    return (0.0, 0.0) if n < 1e-12 else (a[0] / n, a[1] / n)


def perp(a):
    return (-a[1], a[0])


def readable_angle(direction):
    """Text angle (degrees) along direction, flipped so it never reads upside down."""
    ang = math.degrees(math.atan2(direction[1], direction[0]))
    if ang > 90.0:
        ang -= 180.0
    elif ang <= -90.0:
        ang += 180.0
    return ang


# --------------------------------------------------------------------------
# Collision geometry
# --------------------------------------------------------------------------


def text_box(t, pad=0.4):
    """Corners of the rotated rectangle a Text occupies."""
    w = CHAR_W * t.size * len(t.text) + 2 * pad
    h = t.size + 2 * pad
    u = (math.cos(math.radians(t.angle)), math.sin(math.radians(t.angle)))
    v = perp(u)
    shift = {"start": 0.0, "middle": -w / 2, "end": -w}[t.anchor]
    o = add(add(t.pos, mul(u, shift)), mul(v, -pad - 0.25 * t.size))
    return [o, add(o, mul(u, w)), add(add(o, mul(u, w)), mul(v, h)), add(o, mul(v, h))]


def circle_box(c, r):
    return [(c[0] - r, c[1] - r), (c[0] + r, c[1] - r), (c[0] + r, c[1] + r), (c[0] - r, c[1] + r)]


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def segments_cross(p1, p2, q1, q2):
    d1, d2 = _cross(q1, q2, p1), _cross(q1, q2, p2)
    d3, d4 = _cross(p1, p2, q1), _cross(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def point_in_poly(p, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        a, b = poly[i], poly[j]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if p[0] < x:
                inside = not inside
        j = i
    return inside


def segment_hits_poly(p1, p2, poly):
    if point_in_poly(p1, poly) or point_in_poly(p2, poly):
        return True
    n = len(poly)
    return any(segments_cross(p1, p2, poly[i], poly[(i + 1) % n]) for i in range(n))


def polys_overlap(a, b):
    """Separating-axis test for two convex polygons."""
    for poly in (a, b):
        n = len(poly)
        for i in range(n):
            e = sub(poly[(i + 1) % n], poly[i])
            axis = perp(e)
            pa = [axis[0] * p[0] + axis[1] * p[1] for p in a]
            pb = [axis[0] * p[0] + axis[1] * p[1] for p in b]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return False
    return True


class Obstacles:
    """Segments and boxes already on the sheet, for placing annotations."""

    def __init__(self):
        self.segments = []
        self.boxes = []

    def add_drawing(self, items):
        for it in items:
            if isinstance(it, Line):
                self.segments.append((it.p1, it.p2))
            elif isinstance(it, Poly):
                pts = it.points
                rng = range(len(pts)) if it.closed else range(len(pts) - 1)
                self.segments.extend((pts[i], pts[(i + 1) % len(pts)]) for i in rng)
            elif isinstance(it, Circle):
                self.boxes.append(circle_box(it.centre, it.r))
            elif isinstance(it, Text):
                self.boxes.append(text_box(it))

    def hits_box(self, box, ignore_segments=()):
        for s in self.segments:
            if s in ignore_segments:
                continue
            if segment_hits_poly(s[0], s[1], box):
                return True
        return any(polys_overlap(box, b) for b in self.boxes)

    def hits_segment(self, p1, p2):
        if any(segments_cross(p1, p2, s[0], s[1]) for s in self.segments):
            return True
        return any(segment_hits_poly(p1, p2, b) for b in self.boxes)
