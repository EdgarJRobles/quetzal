# SPDX-License-Identifier: LGPL-3.0-or-later
"""Isometric symbols for a laid-out IsoGraph (pure Python).

draw(layout) returns (items, anchors): drawing primitives in paper mm (Y up)
and, per component index, the paper point a balloon should point at.
"""

import math

from pcf import pcf_geom as g

from . import iso_format, iso_layout
from .iso_draw import (CHAR_W, TEXT, W_PIPE, W_SYMBOL, W_THIN, Circle, Line, Poly, Text, add,
                       lerp, mul, sub, unit)

H = 3.0  # half-height of flanges, valves and reducers
WELD_R = 0.8

VALVE_MARKS = {"VB": "ball", "VG": "globe", "VC": "check", "VP": "plug", "VY": "butterfly",
               "VT": "gate"}


def draw(layout, units="mm"):
    """units sizes the skew triangles to their offset labels (mm or ftin)."""
    graph = layout.graph
    comps = graph.pcf.components
    z = layout.zoom
    items = []
    anchors = {}

    def pos(nid):
        return layout.pos[nid]

    for e in graph.edges:
        comp = comps[e.comp]
        P, Q = pos(e.a), pos(e.b)
        n = layout.across(e)
        mid = lerp(P, Q, 0.5)
        kw = comp.keyword
        if e.role in ("pipe", "leg", "branch"):
            items.append(Line(P, Q, W_PIPE))
            if e.role == "pipe":
                anchors.setdefault(e.comp, mid)
            else:
                anchors.setdefault(e.comp, P if e.role == "branch" else _centre(graph, layout, e))
        elif e.role == "olet":
            # The olet keeps its size when its edge is stretched to clear a
            # clash; the rest is drawn as line.
            full = math.hypot(Q[0] - P[0], Q[1] - P[1])
            R = Q
            if full > iso_layout.OLET_LEN * z * 1.05:
                R = add(P, mul(unit(sub(Q, P)), iso_layout.OLET_LEN * z))
                items.append(Line(R, Q, W_PIPE))
            items.append(Poly([add(P, mul(n, 2.2 * z)), add(R, mul(n, 1.4 * z)),
                               add(R, mul(n, -1.4 * z)), add(P, mul(n, -2.2 * z))], W_SYMBOL))
            anchors[e.comp] = lerp(P, R, 0.5)
        else:
            items.extend(_inline(layout, e, comp, P, Q, n, z))
            anchors[e.comp] = mid
    for mark in skew_marks(layout, units):
        items.extend(mark["items"])

    for m in graph.markers:
        comp = comps[m.comp]
        if m.kind == "cap" and m.node >= 0:
            items.extend(_cap(layout, m.node, z))
            anchors[m.comp] = pos(m.node)
        elif m.edge >= 0:
            e = graph.edges[m.edge]
            at = lerp(pos(e.a), pos(e.b), m.t)
            if m.kind == "support":
                items.extend(_support(layout, e, at, comp, z))
            anchors[m.comp] = at
        elif m.kind == "point" and m.node in layout.pos:
            items.extend(_point_item(layout, m.node, comp, z))
            anchors[m.comp] = pos(m.node)

    for node in graph.nodes:
        if node.id not in layout.pos:
            continue
        if node.weld in ("BW", "SW"):
            items.append(Circle(pos(node.id), WELD_R * z, W_THIN, fill=True))
        elif node.weld == "SC":
            e = graph.edges_at(node.id)[0]
            n = layout.across(e)
            d = layout.screen_dir(e)
            for s in (-0.6, 0.6):
                c = add(pos(node.id), mul(d, s * z))
                items.append(Line(add(c, mul(n, 1.3 * z)), add(c, mul(n, -1.3 * z)), W_THIN))
    return items, anchors


def _centre(graph, layout, edge):
    """Paper position of the centre node of an elbow/tee leg."""
    for nid in (edge.a, edge.b):
        if graph.nodes[nid].centre:
            return layout.pos[nid]
    return lerp(layout.pos[edge.a], layout.pos[edge.b], 0.5)


def _face_node(graph, edge):
    """(face node, other node) of a flange edge."""
    for nid in (edge.a, edge.b):
        if (edge.comp, "FACE") in graph.nodes[nid].ends:
            return nid, (edge.b if nid == edge.a else edge.a)
    return edge.a, edge.b


def _across_line(c, n, h, width=W_SYMBOL):
    return Line(add(c, mul(n, h)), add(c, mul(n, -h)), width)


def _inline(layout, e, comp, P, Q, n, z):
    graph = layout.graph
    kw = comp.keyword
    h = H * z
    out = []
    if kw in ("FLANGE", "FLANGE-BLIND"):
        fnode, wnode = _face_node(graph, e)
        F, Wd = layout.pos[fnode], layout.pos[wnode]
        out.append(Line(F, Wd, W_PIPE))
        out.append(_across_line(F, n, h, W_PIPE))
        if kw == "FLANGE-BLIND" or comp.skey == "FLBL":
            out.append(Poly([add(F, mul(n, h)), add(Wd, mul(n, h)), add(Wd, mul(n, -h)),
                             add(F, mul(n, -h))], W_SYMBOL, fill=True))
        elif comp.skey in ("FLWN", ""):
            out.append(Poly([add(F, mul(n, 0.55 * h)), Wd, add(F, mul(n, -0.55 * h))],
                            W_SYMBOL, closed=False))
        else:  # slip-on, socket-weld, lap joint: a second, shorter line
            out.append(_across_line(lerp(F, Wd, 0.6), n, 0.6 * h))
    elif kw == "GASKET":
        out.append(Line(P, Q, W_PIPE))
        out.append(_across_line(lerp(P, Q, 0.5), n, 0.8 * h, W_THIN))
    elif kw == "VALVE":
        M = lerp(P, Q, 0.5)
        out.append(Poly([add(P, mul(n, h)), add(P, mul(n, -h)), M], W_SYMBOL))
        out.append(Poly([add(Q, mul(n, h)), add(Q, mul(n, -h)), M], W_SYMBOL,
                        fill=VALVE_MARKS.get(comp.skey[:2]) == "check"))
        mark = VALVE_MARKS.get(comp.skey[:2])
        if mark == "ball":
            out.append(Circle(M, 1.2 * z, W_SYMBOL))
        elif mark == "globe":
            out.append(Circle(M, 1.2 * z, W_SYMBOL, fill=True))
        elif mark == "plug":
            s = 1.0 * z
            out.append(Poly([(M[0] - s, M[1] - s), (M[0] + s, M[1] - s), (M[0] + s, M[1] + s),
                             (M[0] - s, M[1] + s)], W_SYMBOL))
        elif mark == "butterfly":
            out.append(_across_line(M, n, h, W_SYMBOL))
        if mark != "check":
            stem = _stem_dir(layout, e)
            top = add(M, mul(stem, 5.0 * z))
            d = layout.screen_dir(e)
            out.append(Line(M, top, W_SYMBOL))
            out.append(Line(add(top, mul(d, 2.5 * z)), add(top, mul(d, -2.5 * z)), W_SYMBOL))
        if comp.skey[2:4] in ("FL", ""):
            out.append(_across_line(P, n, 1.15 * h, W_PIPE))
            out.append(_across_line(Q, n, 1.15 * h, W_PIPE))
    elif kw.startswith("REDUCER"):
        big, small = (P, Q) if _bore_at(comp, graph.nodes[e.a].pos) >= _bore_at(
            comp, graph.nodes[e.b].pos) else (Q, P)
        h2 = 0.55 * h
        if kw == "REDUCER-ECCENTRIC":
            # Flat side drawn along the reducer's real flat direction (e.g. down for FOB).
            f = unit(iso_layout.project(e.flat, layout.rotation)) if e.flat else mul(n, -1.0)
            out.append(Poly([add(big, mul(f, h)), add(small, mul(f, h)),
                             add(small, mul(f, h - 2 * h2)), add(big, mul(f, -h))], W_SYMBOL))
        else:
            out.append(Poly([add(big, mul(n, h)), add(small, mul(n, h2)),
                             add(small, mul(n, -h2)), add(big, mul(n, -h))], W_SYMBOL))
    elif kw in ("COUPLING", "UNION"):
        hh = 0.75 * h
        out.append(Poly([add(P, mul(n, hh)), add(Q, mul(n, hh)), add(Q, mul(n, -hh)),
                         add(P, mul(n, -hh))], W_SYMBOL))
        if kw == "UNION":
            out.append(_across_line(lerp(P, Q, 0.5), n, hh))
    else:  # anything else: a box with its SKEY
        hh = 0.8 * h
        out.append(Poly([add(P, mul(n, hh)), add(Q, mul(n, hh)), add(Q, mul(n, -hh)),
                         add(P, mul(n, -hh))], W_SYMBOL))
        label = comp.skey or kw[:4]
        out.append(Text(add(lerp(P, Q, 0.5), mul(n, hh + 1.2 * z)), label, 1.8 * z))
    return out


def _bore_at(comp, point):
    for p in comp.end_points:
        if g.dist(p.xyz(), point) <= 1.0:
            return p.bore
    return 0.0


def _stem_dir(layout, e):
    """Valve stem: up for horizontal lines, north for vertical ones."""
    if abs(e.direction[2]) > 0.99:
        return layout.perpendicular(e, (0.0, 1.0, 0.0))
    return layout.perpendicular(e, (0.0, 0.0, 1.0))


def _point_item(layout, node_id, comp, z):
    """An inline item of zero length (e.g. a lap-joint flange without its stub
    end): drawn across the line at its node."""
    edges = layout.graph.edges_at(node_id)
    if not edges:
        return []
    e = edges[0]
    C = layout.pos[node_id]
    n = layout.across(e)
    d = layout.screen_dir(e)
    h = H * z
    if comp.keyword in ("FLANGE", "FLANGE-BLIND"):
        return [_across_line(add(C, mul(d, -0.5 * z)), n, h, W_PIPE),
                _across_line(add(C, mul(d, 0.5 * z)), n, h, W_PIPE)]
    return [_across_line(C, n, 0.8 * h, W_SYMBOL)]


def _cap(layout, node_id, z):
    graph = layout.graph
    edges = graph.edges_at(node_id)
    if not edges:
        return []
    e = edges[0]
    C = layout.pos[node_id]
    other = layout.pos[graph.other(e, node_id)]
    out_dir = unit(sub(C, other))
    n = layout.across(e)
    r = 2.2 * z
    arc = [add(add(C, mul(n, r * math.cos(t))), mul(out_dir, r * math.sin(t)))
           for t in [i * math.pi / 12 for i in range(13)]]
    return [Poly(arc, W_SYMBOL, closed=True)]


def _support(layout, e, at, comp, z):
    down = layout.perpendicular(e, (0.0, 0.0, -1.0))
    if abs(e.direction[2]) > 0.99:
        down = layout.perpendicular(e, (-1.0, 0.0, 0.0))
    d = layout.screen_dir(e)
    base = add(at, mul(down, 3.0 * z))
    out = [Poly([at, add(base, mul(d, 1.8 * z)), add(base, mul(d, -1.8 * z))], W_SYMBOL, fill=True)]
    name = comp.attr("NAME") or comp.skey
    if name:
        out.append(Text(add(base, mul(down, 3.0 * z)), name, 1.8 * z))
    return out


SKEW_TRI_LEN = 14.0  # paper mm along the pipe covered by a skew triangle
SKEW_LEG_MIN = 6.0  # paper mm: the triangle grows (up to 80% of its pipe) to give short legs room
SKEW_MIN_OFFSET = 1.0  # mm; a smaller offset along an axis is not a skew in that axis


def skew_text_size(layout):
    return max(1.8, TEXT * layout.zoom * 0.8)


def skew_marks(layout, units="mm"):
    """One hatched skew triangle per skewed run, on its longest pipe.

    Its legs follow the world axes the run is offset along, and each carries
    the run's true offset between its end work points (labelled by
    iso_dims.place_skew_offsets).  A run offset in all three axes gets a plan
    triangle and a rise triangle standing on its diagonal.  Returns
    [{"items": [...], "legs": [(p, q, offset mm, triangle centroid)]}]."""
    graph = layout.graph
    z = layout.zoom
    out = []
    for run in graph.runs:
        if run["axis"]:
            continue
        edges = [graph.edges[i] for i in run["edges"] if graph.edges[i].a in layout.pos]
        if not edges:
            continue
        pipes = [e for e in edges if e.role == "pipe"] or edges
        e = max(pipes, key=lambda f: g.dist(*[(p[0], p[1], 0.0) for p in layout.segment(f)]))
        P, Q = layout.segment(e)
        length = math.hypot(Q[0] - P[0], Q[1] - P[1])
        if length < 1e-6:
            continue
        nodes = run["nodes"]
        V = g.sub(graph.nodes[nodes[-1]].pos, graph.nodes[nodes[0]].pos)
        if g.dot(V, e.direction) < 0:
            V = g.scale(V, -1.0)
        parts = []
        for i in range(3):
            if abs(V[i]) >= SKEW_MIN_OFFSET:
                v = [0.0, 0.0, 0.0]
                v[i] = V[i]
                parts.append(tuple(v))
        if len(parts) < 2:
            continue
        full = iso_layout.project(V, layout.rotation)
        size = math.hypot(full[0], full[1])
        if size < 1e-9:
            continue
        steps = [iso_layout.project(part, layout.rotation) for part in parts]
        # Each leg at least as long as its label (ft-in offsets run to 11 characters).
        text = skew_text_size(layout)
        tri = SKEW_TRI_LEN * z
        for part, st in zip(parts, steps):
            share = math.hypot(*st) / size  # leg length per paper mm of triangle
            label = CHAR_W * text * len(iso_format.length_text(max(abs(c) for c in part), units))
            tri = max(tri, max(SKEW_LEG_MIN * z, label + 1.5 * z) / max(share, 1e-6))
        tri = min(tri, (0.6 if tri <= SKEW_TRI_LEN * z else 0.8) * length)
        k = tri / size
        start = lerp(P, Q, 0.2 if length > 2 * tri else 0.5 * (1 - tri / length))
        pts = [start]
        for step in steps:
            pts.append(add(pts[-1], mul(step, k)))
        items, legs = [], []
        for a, b, part in zip(pts, pts[1:], parts):
            items.append(Line(a, b, W_THIN))
        if len(parts) == 2:
            tris = [(pts[0], pts[1], pts[2])]
        else:  # plan triangle, then the rise standing on its diagonal (not hatched)
            items.append(Line(pts[0], pts[2], W_THIN))
            tris = [(pts[0], pts[1], pts[2]), (pts[0], pts[2], pts[3])]
        A, B, C = tris[0]  # hatch parallel to the first leg
        for t in (0.3, 0.55, 0.8):
            items.append(Line(lerp(A, C, t), lerp(B, C, t), W_THIN))
        for (a, b), part, tri_pts in zip(zip(pts, pts[1:]), parts, (tris[0], tris[0], tris[-1])):
            centroid = mul(add(add(tri_pts[0], tri_pts[1]), tri_pts[2]), 1.0 / 3.0)
            legs.append((a, b, max(abs(c) for c in part), centroid))
        out.append({"items": items, "legs": legs, "run": run})
    return out
