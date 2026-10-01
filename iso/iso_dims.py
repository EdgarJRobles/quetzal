# SPDX-License-Identifier: LGPL-3.0-or-later
"""Isometric dimensions between work points (pure Python).

Along each straight run the work points (elbow/tee/olet centres, reducer
ends, flange and valve faces, open ends) are chained.  A span is dimensioned
when it contains pipe, or when it lies on a run that has pipe and includes a
tee, reducer or elbow: the welder places what follows from those take-outs
(e.g. olets measured from a flange face through a reducer), and real fittings
vary from the catalog.  Spans made only of other fittings - valve face to
face, or a branch stack such as olet + flange - are left to the catalog.
Each dimension states the true length along the run; its line is offset along
the run's iso "across" axis, on the side and lane where it collides with the
least.
"""

import math
from dataclasses import dataclass

from pcf import pcf_geom as g

from . import iso_format, iso_layout
from .iso_draw import (TEXT, W_THIN, Line, Obstacles, Poly, Text, add, lerp, mul, perp,
                       readable_angle, sub, text_box, unit)

FIRST_LANE = 8.0  # mm from the line work to the first dimension line
LANE_STEP = 6.0
LANES = 4
EXT_GAP = 1.5  # gap between the line work and an extension line
EXT_OVER = 1.5  # extension line beyond the dimension line
ARROW_L, ARROW_W = 2.2, 0.55
MIN_VALUE = 0.5  # mm; shorter distances are not dimensioned


@dataclass
class Dimension:
    a: int  # node ids
    b: int
    value: float  # true distance, mm
    text: str


def place_dimensions(layout, units, obstacles):
    """Add dimension items for every run; returns (items, [Dimension])."""
    graph = layout.graph
    z = layout.zoom
    size = max(2.0, TEXT * z)
    all_items, dims = [], []
    placed = Obstacles()  # dimensions so far: crossing one is worse than crossing a pipe
    # Short runs (branches) first: they have little room to move, while a
    # long header can step out a lane to let a branch dimension sit beside it.
    for run in sorted(graph.runs, key=lambda r: _run_length(graph, r)):
        pairs = _spans(graph, layout, run)
        if not pairs:
            continue
        edge = graph.edges[run["edges"][0]]
        n = layout.across(edge)
        best = None
        for lane in range(LANES):
            for side in (-1.0, 1.0):
                off = side * (FIRST_LANE + lane * LANE_STEP) * z
                items, texts, lines = _chain(layout, pairs, n, off, size, units)
                hits = sum(obstacles.hits_segment(p, q) + 2 * placed.hits_segment(p, q) for p, q in lines)
                hits += sum(obstacles.hits_box(text_box(t)) + 2 * placed.hits_box(text_box(t)) for t in texts)
                if best is None or hits < best[0]:
                    best = (hits, items)
                if hits == 0:
                    break
            if best[0] == 0:
                break
        solid = [it for it in best[1] if not (isinstance(it, Line) and it.dash)]
        obstacles.add_drawing(solid)
        placed.add_drawing(solid)
        all_items.extend(best[1])
        dims.extend(Dimension(a, b, value, iso_format.length_text(value, units))
                    for a, b, value in pairs)
    return all_items, dims


def _run_length(graph, run):
    return g.dist(graph.nodes[run["nodes"][0]].pos, graph.nodes[run["nodes"][-1]].pos)


def slope_text(direction):
    """'SLOPE 1:42' for a line falling 1 in 42; the angle off its axis otherwise."""
    i = max(range(3), key=lambda k: abs(direction[k]))
    if i == 2:
        return "OUT OF PLUMB %.1f°" % math.degrees(math.acos(min(1.0, abs(direction[2]))))
    fall = abs(direction[2])
    run = math.hypot(direction[0], direction[1])
    if fall > 1e-4:
        return "SLOPE 1:%d" % round(run / fall)
    return "%.1f° OFF AXIS" % math.degrees(math.acos(min(1.0, abs(direction[i]))))


def place_slopes(layout, obstacles):
    """A slope note with a downhill arrow beside the longest sloped pipe of each run."""
    graph = layout.graph
    z = layout.zoom
    size = max(2.0, TEXT * z)
    items = []
    for run in graph.runs:
        sloped = [graph.edges[i] for i in run["edges"]
                  if graph.edges[i].slope is not None and graph.edges[i].role == "pipe"]
        if not sloped:
            continue
        e = max(sloped, key=lambda f: f.length)
        A, B = layout.pos[e.a], layout.pos[e.b]
        u = unit(sub(B, A))
        downhill = u if e.slope[2] < 0 else mul(u, -1.0)
        n = layout.across(e)
        best = None
        for side in (1.0, -1.0):
            # A third of the way along: the pipe's balloon points at its middle.
            mid = add(lerp(A, B, 0.3), mul(n, side * 3.0 * z))
            text = Text(add(mid, mul(n, side * 1.2 * z)), slope_text(e.slope), size * 0.9,
                        readable_angle(u))
            if side < 0:
                text.pos = add(text.pos, mul(n, -size))  # glyphs grow away from the line
            tail, tip = add(mid, mul(downhill, -5.0 * z)), add(mid, mul(downhill, 5.0 * z))
            base = add(tip, mul(downhill, -ARROW_L * z))
            w = mul(perp(downhill), ARROW_W * z)
            group = [text, Line(tail, tip, W_THIN), Poly([tip, add(base, w), sub(base, w)], W_THIN, fill=True)]
            hits = obstacles.hits_box(text_box(text)) + obstacles.hits_segment(tail, tip)
            if best is None or hits < best[0]:
                best = (hits, group)
        obstacles.add_drawing(best[1])
        items.extend(best[1])
    return items


ROLL_MIN_DEG = 0.33  # rolls smaller than this are within what a fitter can set
ROLL_R = 3.5  # radius of the roll symbol, mm
ROLL_GAP_DEG = 60.0  # open part of the roll symbol, centred on the rolled leg


def _true_dir(edge, start):
    """True (unsnapped) unit direction of edge, pointing away from node start."""
    d = edge.slope or edge.direction
    return d if edge.a == start else g.scale(d, -1.0)


def _off_axis(d):
    return math.degrees(math.acos(min(1.0, max(abs(c) for c in d))))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def roll_info(graph, comp_index):
    """How an elbow or tee is rolled, or None if it is not.

    The fitting's plane holds its two directions (elbow legs; tee run and
    branch).  Its tilt from the nearest principal plane is the roll.  The roll
    is set by turning the fitting about its squarest direction (the
    reference) at that direction's weld; the other direction then moves from
    square to its true position.  Returns a dict: angle (deg), centre and weld
    node ids, axis (weld -> centre, true), rolled (true direction of the other
    leg from the centre)."""
    comp = graph.pcf.components[comp_index]
    edges = [graph.edges[i] for i in graph.comp_edges.get(comp_index, [])]
    legs = [e for e in edges if e.role == "leg"]
    branch = [e for e in edges if e.role == "branch"]
    if comp.keyword in ("ELBOW", "BEND") and len(legs) == 2:
        options = legs
    elif comp.keyword == "TEE" and len(legs) == 2 and branch:
        options = [legs[0], branch[0]]  # the run (either half) and the branch
    else:
        return None
    centre = next((n for e in options for n in (e.a, e.b) if graph.nodes[n].centre), None)
    if centre is None:
        return None
    outward = [_true_dir(e, centre) for e in options]
    normal = _cross(outward[0], outward[1])
    size = g.length(normal)
    if size < 1e-9:
        return None
    angle = math.degrees(math.acos(min(1.0, max(abs(c) for c in normal) / size)))
    ref = min(range(2), key=lambda i: _off_axis(outward[i]))
    weld = graph.other(options[ref], centre)
    return {"angle": angle, "centre": centre, "weld": weld,
            "axis": g.scale(outward[ref], -1.0), "rolled": outward[1 - ref],
            "rolled_edge": options[1 - ref].id}


def roll_angle(graph, comp_index):
    info = roll_info(graph, comp_index)
    return info["angle"] if info else 0.0


def roll_symbol(layout, info, z):
    """Open circular arrow around the reference pipe at its weld, in the plane
    square to that pipe, turning the way that takes the rolled leg from square
    to its true position.  The opening faces the rolled leg."""
    a = info["axis"]
    to = g.unit(g.sub(info["rolled"], g.scale(a, g.dot(info["rolled"], a))))
    k = max(range(3), key=lambda i: abs(to[i]))
    square = [0.0, 0.0, 0.0]
    square[k] = 1.0 if to[k] > 0 else -1.0
    u = g.unit(g.sub(tuple(square), g.scale(a, g.dot(tuple(square), a))))
    w = _cross(a, u)  # u -> w turns positively about a
    sense = 1.0 if g.dot(a, _cross(tuple(square), to)) >= 0 else -1.0
    W = layout.pos[info["weld"]]
    r = ROLL_R * z

    def at(t):
        v = g.add(g.scale(u, math.cos(t)), g.scale(w, math.sin(t)))
        p = iso_layout.project(v, layout.rotation)
        return (W[0] + r * p[0], W[1] + r * p[1])

    half_gap = math.radians(ROLL_GAP_DEG / 2.0)
    steps = 28
    ts = [half_gap + (2 * math.pi - 2 * half_gap) * i / steps for i in range(steps + 1)]
    if sense < 0:
        ts.reverse()
    pts = [at(t) for t in ts]
    tip, before = pts[-1], pts[-2]
    d = unit(sub(tip, before))
    base = add(tip, mul(d, -ARROW_L * 1.2 * z))
    wv = mul(perp(d), ARROW_W * 1.6 * z)
    return [Poly(pts, W_THIN * 1.6, closed=False), Poly([tip, add(base, wv), sub(base, wv)], W_THIN, fill=True)]


def place_rolls(layout, obstacles):
    """A roll symbol at the weld where each rolled elbow or tee is turned,
    with 'ROLL x.xx°' beside it."""
    graph = layout.graph
    z = layout.zoom
    size = max(2.0, TEXT * z) * 0.9
    items = []
    for ci, comp in enumerate(graph.pcf.components):
        if comp.keyword not in ("ELBOW", "BEND", "TEE"):
            continue
        info = roll_info(graph, ci)
        if info is None or info["angle"] < ROLL_MIN_DEG or _shown_elsewhere(graph, info["rolled_edge"]):
            continue
        symbol = roll_symbol(layout, info, z)
        obstacles.add_drawing(symbol)
        items.extend(symbol)
        W, C = layout.pos[info["weld"]], layout.pos[info["centre"]]
        away = unit(sub(W, C)) if sub(W, C) != (0.0, 0.0) else (1.0, 0.0)
        best = None
        for dist in (ROLL_R + 5.0, ROLL_R + 9.0, ROLL_R + 14.0):
            for d in (perp(away), mul(perp(away), -1.0), away):
                text = Text(add(W, mul(d, dist * z)), "ROLL %.2f\u00b0" % info["angle"], size)
                hits = obstacles.hits_box(text_box(text))
                if best is None or hits < best[0]:
                    best = (hits, text)
            if best[0] == 0:
                break
        obstacles.add_drawing([best[1]])
        items.append(best[1])
    return items


def _shown_elsewhere(graph, edge_id):
    """True when the rolled leg's deviation is already on the drawing: its run
    is skewed (skew triangle) or carries a sloped pipe (slope note)."""
    for run in graph.runs:
        if edge_id in run["edges"]:
            edges = [graph.edges[i] for i in run["edges"]]
            return not run["axis"] or any(e.slope is not None and e.role == "pipe" for e in edges)
    return False


def place_skew_offsets(layout, units, obstacles):
    """The true offset beside each leg of every skew triangle."""
    from . import iso_symbols
    z = layout.zoom
    size = iso_symbols.skew_text_size(layout)
    items = []
    for mark in iso_symbols.skew_marks(layout, units):
        legs = mark["legs"]
        for i, (a, b, value, centroid) in enumerate(legs):
            u = unit(sub(b, a))
            # The first leg starts on the pipe and the last ends on it: keep
            # their labels towards the far end.
            mid = lerp(a, b, 0.62 if i == 0 else 0.38 if i == len(legs) - 1 else 0.5)
            out = unit(sub(mid, centroid))
            n = perp(u)
            if n[0] * out[0] + n[1] * out[1] < 0:
                n = mul(n, -1.0)
            best = None
            # Outside the triangle first; inside (over the hatching) only if that is clearer.
            for side, gap in ((1.0, 0.8), (1.0, 2.5), (1.0, 5.0), (-1.0, 0.8), (-1.0, 2.5), (1.0, 8.0)):
                m = mul(n, side)
                text = Text(add(mid, mul(m, gap * z)), iso_format.length_text(value, units), size,
                            readable_angle(u))
                up = _text_up(text.angle)
                if up[0] * m[0] + up[1] * m[1] < 0:
                    text.pos = add(text.pos, mul(m, size))  # glyphs grow away from the leg
                hits = obstacles.hits_box(text_box(text))
                if best is None or hits < best[0]:
                    best = (hits, text)
                if hits == 0:
                    break
            obstacles.add_drawing([best[1]])
            items.append(best[1])
    return items


TAKE_OUT_FITTINGS = {"TEE", "REDUCER-CONCENTRIC", "REDUCER-ECCENTRIC", "ELBOW", "BEND"}


def _spans(graph, layout, run):
    """(a, b, length) for the consecutive work points on run worth dimensioning."""
    order = {nid: i for i, nid in enumerate(run["nodes"])}
    edges = [(sorted((order[e.a], order[e.b])), e) for e in (graph.edges[i] for i in run["edges"])]
    run_has_pipe = any(e.role == "pipe" for _span, e in edges)
    along = _true_run_direction(run, [e for _span, e in edges])
    wps = [nid for nid in run["nodes"] if graph.nodes[nid].work_point and nid in layout.pos]
    spans = []
    for a, b in zip(wps, wps[1:]):
        lo, hi = order[a], order[b]
        inside = [e for (p0, p1), e in edges if lo <= p0 and p1 <= hi]
        has_pipe = any(e.role == "pipe" for e in inside)
        take_out = run_has_pipe and any(
            graph.pcf.components[e.comp].keyword in TAKE_OUT_FITTINGS for e in inside)
        if not (has_pipe or take_out):
            continue  # valves or a branch stack: their catalog dimensions fix this span
        # Measured along the run, so an eccentric reducer's offset does not count;
        # along its true direction, so a sloped run gets its true length.
        value = abs(g.dot(g.sub(graph.nodes[b].pos, graph.nodes[a].pos), along))
        if value >= MIN_VALUE:
            spans.append((a, b, value))
    return spans


def _true_run_direction(run, edges):
    """Direction of a run as built: a sloped run is drawn on its axis, but its
    pipe keeps the true direction in edge.slope."""
    d = run["direction"]
    for e in sorted(edges, key=lambda e: -e.length):
        if e.slope is not None and e.role == "pipe":
            s = e.slope if g.dot(e.slope, e.direction) > 0 else g.scale(e.slope, -1.0)
            return s if g.dot(e.direction, d) > 0 else g.scale(s, -1.0)
    return d


def _chain(layout, pairs, n, off, size, units):
    z = layout.zoom
    away = unit(mul(n, off))
    items, texts, lines = [], [], []
    extended = set()
    for a, b, value in pairs:
        A, B = layout.pos[a], layout.pos[b]
        A2, B2 = add(A, mul(n, off)), add(B, mul(n, off))
        for P, P2, nid in ((A, A2, a), (B, B2, b)):
            if nid not in extended:
                extended.add(nid)
                items.append(Line(add(P, mul(away, EXT_GAP * z)), add(P2, mul(away, EXT_OVER * z)),
                                  W_THIN, dash=True))
        items.append(Line(A2, B2, W_THIN))
        lines.append((A2, B2))
        u = unit(sub(B2, A2))
        for tip, direction in ((A2, u), (B2, mul(u, -1.0))):
            base = add(tip, mul(direction, ARROW_L * z))
            w = mul(perp(direction), ARROW_W * z)
            items.append(Poly([tip, add(base, w), sub(base, w)], W_THIN, fill=True))
        angle = readable_angle(u)
        text = Text(lerp(A2, B2, 0.5), iso_format.length_text(value, units), size, angle)
        # Put the text on the far side of the dimension line from the pipe.
        up = _text_up(angle)
        if up[0] * away[0] + up[1] * away[1] > 0:
            text.pos = add(text.pos, mul(away, 0.8 * z))
        else:
            text.pos = add(text.pos, mul(away, size + 0.8 * z))
        items.append(text)
        texts.append(text)
    return items, texts, lines


def _text_up(angle):
    r = math.radians(angle)
    return (-math.sin(r), math.cos(r))
