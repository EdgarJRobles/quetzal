# SPDX-License-Identifier: LGPL-3.0-or-later
"""SVG output of drawing primitives in page coordinates (mm, Y down).

Only elements the Qt SVG renderer (SVG Tiny 1.2) draws reliably are used:
line, polyline, polygon, circle and text with a transform.
"""

from xml.sax.saxutils import escape

from .iso_draw import Circle, Line, Poly, Text

FONT = "sans-serif"


def _f(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def _pts(points):
    return " ".join("%s,%s" % (_f(x), _f(y)) for x, y in points)


def element(it):
    if isinstance(it, Line):
        dash = ' stroke-dasharray="3,1.5"' if it.dash else ""
        return '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#000" stroke-width="%s" stroke-linecap="round"%s/>' % (
            _f(it.p1[0]), _f(it.p1[1]), _f(it.p2[0]), _f(it.p2[1]), _f(it.width), dash)
    if isinstance(it, Poly):
        tag = "polygon" if it.closed else "polyline"
        fill = "#000" if it.fill else "none"
        return '<%s points="%s" fill="%s" stroke="#000" stroke-width="%s" stroke-linejoin="round"/>' % (
            tag, _pts(it.points), fill, _f(it.width))
    if isinstance(it, Circle):
        fill = "#000" if it.fill else "#fff"
        return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#000" stroke-width="%s"/>' % (
            _f(it.centre[0]), _f(it.centre[1]), _f(it.r), fill, _f(it.width))
    if isinstance(it, Text):
        weight = ' font-weight="bold"' if it.bold else ""
        transform = "translate(%s,%s)" % (_f(it.pos[0]), _f(it.pos[1]))
        if abs(it.angle) > 1e-6:
            transform += " rotate(%s)" % _f(-it.angle)  # page Y is down
        return '<text x="0" y="0" transform="%s" font-family="%s" font-size="%s" text-anchor="%s"%s>%s</text>' % (
            transform, FONT, _f(it.size), it.anchor, weight, escape(it.text))
    raise TypeError(it)


def render(items, width, height):
    """A complete SVG document of the given page size."""
    body = "\n".join(element(it) for it in items)
    return ('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="%smm" height="%smm" '
            'viewBox="0 0 %s %s">\n%s\n</svg>\n') % (_f(width), _f(height), _f(width), _f(height), body)


def to_page(items, transform, scale=1.0):
    """Map paper items (Y up) through transform(point) -> page point (Y down).
    scale is the uniform factor transform applies, for radii and text sizes."""
    out = []
    for it in items:
        if isinstance(it, Line):
            out.append(Line(transform(it.p1), transform(it.p2), it.width, it.dash))
        elif isinstance(it, Poly):
            out.append(Poly([transform(p) for p in it.points], it.width, it.fill, it.closed))
        elif isinstance(it, Circle):
            out.append(Circle(transform(it.centre), it.r * scale, it.width, it.fill))
        elif isinstance(it, Text):
            out.append(Text(transform(it.pos), it.text, it.size * scale, it.angle, it.anchor, it.bold))
    return out
