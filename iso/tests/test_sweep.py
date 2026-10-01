# SPDX-License-Identifier: LGPL-3.0-or-later
"""Regression tests from the component sweep (no FreeCAD needed).

The sweep_*.pcf files were exported by pcf_export from Quetzal models built
in FreeCAD: every piping component type, square and skewed, and one launcher
from the AI_Piping_Design examples with a closed loop (sweep_loop.pcf).

Run from the repository root with:
    python -m unittest discover -s iso/tests -t .
"""

import math
import os
import unittest
import xml.etree.ElementTree as ET

from pcf import pcf_geom, pcf_model
from iso import iso_bom, iso_build, iso_graph, iso_sheet, iso_symbols
from iso.iso_draw import W_PIPE, W_THIN, Line

DATA = os.path.join(os.path.dirname(__file__), "data")
FIXTURES = ("sweep_plan_skew.pcf", "sweep_compound_skew.pcf", "sweep_near_axis.pcf",
            "sweep_lap_joint.pcf", "sweep_offset_support.pcf", "sweep_plan_45.pcf",
            "sweep_sw_coupling.pcf", "sweep_header.pcf", "sweep_flange_stack.pcf", "sweep_loop.pcf")
OPTIONS = (iso_build.Options(units="mm", size_system="DN", sheet=iso_sheet.ISO_A3),
           iso_build.Options(units="ftin", size_system="NPS", sheet=iso_sheet.ANSI_B))


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return pcf_model.to_mm(pcf_model.parse(f.read())[0])


def mm_sheet(name, rotation=None):
    return iso_build.build_sheet(load(name), iso_build.Options(sheet=iso_sheet.ISO_A3, rotation=rotation))


def lost_components(pf):
    """Components neither drawn nor reported in graph.skipped."""
    g = iso_graph.build(pf)
    sheet = iso_build.build_sheet(pf)
    _items, anchors = iso_symbols.draw(sheet.layout)
    skipped = {ci for ci, _why in g.skipped}
    return [c.keyword for ci, c in enumerate(pf.components) if ci not in anchors and ci not in skipped]


def collinear_overlap(s, t, tol=0.3):
    """Length (mm) over which segment s lies on segment t."""
    (a, b), (c, d) = s, t
    L = math.dist(c, d)
    if L < 1e-9:
        return 0.0
    u = ((d[0] - c[0]) / L, (d[1] - c[1]) / L)
    off = [abs((p[0] - c[0]) * u[1] - (p[1] - c[1]) * u[0]) for p in (a, b)]
    if max(off) > tol:
        return 0.0
    ta, tb = sorted(((p[0] - c[0]) * u[0] + (p[1] - c[1]) * u[1]) for p in (a, b))
    return max(0.0, min(tb, L) - max(ta, 0.0))


class SweepSheetTests(unittest.TestCase):
    def test_every_fixture_builds_in_every_rotation(self):
        for name in FIXTURES:
            pf = load(name)
            for opt in OPTIONS:
                for rot in (None, 0, 1, 2, 3):
                    opt.rotation = rot
                    sheet = iso_build.build_sheet(pf, opt)
                    ET.fromstring(sheet.svg)
                    x0, y0, x1, y1 = opt.sheet.iso_area
                    for _n, (x, y), _a in sheet.balloons:
                        self.assertTrue(x0 <= x <= x1 and y0 <= y <= y1, (name, rot, x, y))
                opt.rotation = None

    def test_header_dimensions(self):
        """Olets, a sockolet, a tee branch through a gate valve to a blind, an
        eccentric reducer and a flanged end, all square."""
        sheet = mm_sheet("sweep_header.pcf")
        self.assertEqual(sorted(d.text for d in sheet.dimensions),
                         sorted(["270", "360", "413", "593", "450", "140", "678",
                                 "318", "204", "495", "347", "322"]))
        self.assertEqual(sheet.warnings, [])

    def test_flange_stack_bom(self):
        rows = {(r.category, r.description) for r in mm_sheet("sweep_flange_stack.pcf").bom}
        self.assertIn(("VALVES", "VALVE NPS 4 Ball_LongPatternRF 150lb"), rows)
        self.assertIn(("VALVES", "VALVE NPS 4 Check_Swing_FullPortRF 150lb"), rows)
        self.assertIn(("FLANGES", "FLANGE-BLIND NPS 4 BL 150lb"), rows)

    def test_near_axis_slopes_without_duplicate_rolls(self):
        svg = mm_sheet("sweep_near_axis.pcf").svg
        for text in ("SLOPE 1:19", "SLOPE 1:143", "OUT OF PLUMB 3.0"):
            self.assertIn(text, svg)
        self.assertNotIn("ROLL", svg)  # every rolled leg is a sloped pipe

    def test_plan_skew_has_no_roll_callouts(self):
        self.assertNotIn("ROLL", mm_sheet("sweep_plan_skew.pcf").svg)

    def test_skewed_legs_keep_their_direction(self):
        for name, skewed in (("sweep_plan_skew.pcf", 10), ("sweep_compound_skew.pcf", 13)):
            g = iso_graph.build(load(name))
            self.assertEqual(sum(1 for e in g.edges if not e.axis), skewed, name)

    def test_lap_joint_flanges_are_drawn(self):
        # Quetzal's LJ flange has both ports at one point: a zero-length item,
        # drawn at its node.
        pf = load("sweep_lap_joint.pcf")
        self.assertEqual(lost_components(pf), [])
        sheet = iso_build.build_sheet(pf)
        flanges = [r.number for r in sheet.bom if r.category == "FLANGES"]
        self.assertTrue(set(flanges) <= {n for n, _c, _a in sheet.balloons})

    def test_offset_support_is_drawn(self):
        # A beam clamp 80 mm below the pipe axis, sized by a product code (bore 0).
        pf = load("sweep_offset_support.pcf")
        g = iso_graph.build(pf)
        self.assertEqual([m.edge >= 0 for m in g.markers if m.kind == "support"], [True])
        self.assertEqual(lost_components(pf), [])

    def test_support_off_every_line_is_reported(self):
        text = open(os.path.join(DATA, "sweep_offset_support.pcf"), encoding="utf-8").read()
        pf = pcf_model.parse(text.replace("CO-ORDS 750.0000 0.0000 -80.1625", "CO-ORDS 750.0000 0.0000 -900"))[0]
        self.assertEqual([why for _ci, why in iso_graph.build(pf).skipped],
                         ["support is not on any line of this pipeline"])

    def test_sloped_runs_are_dimensioned_true_length(self):
        sheet = mm_sheet("sweep_near_axis.pcf")
        g = sheet.layout.graph
        for d in sheet.dimensions:
            self.assertAlmostEqual(d.value, pcf_geom.dist(g.nodes[d.a].pos, g.nodes[d.b].pos), delta=0.5)

    def test_dimension_lines_clear_of_the_pipe(self):
        # A horizontal leg at 45 deg in plan projects parallel to "up" in
        # rotations 1 and 3, so the dimension offset collapses onto the pipe.
        for rot in (1, 3):
            sheet = mm_sheet("sweep_plan_45.pcf", rot)
            pipes = [it for it in sheet.items if isinstance(it, Line) and it.width >= W_PIPE * sheet.scale * 0.99]
            dims = [it for it in sheet.items if isinstance(it, Line) and not it.dash
                    and it.width <= W_THIN * sheet.scale * 1.01]
            for d in dims:
                on_pipe = max(collinear_overlap((d.p1, d.p2), (p.p1, p.p2)) for p in pipes)
                self.assertLess(on_pipe, 1.0, (rot, d))

    def test_socket_weld_coupling_is_located(self):
        # 300 pipe + coupling + 300 pipe: each pipe to its socket, not just
        # the 626 overall.
        texts = [d.text for d in mm_sheet("sweep_sw_coupling.pcf").dimensions]
        self.assertEqual(texts, ["300", "300"])

    def test_loop_is_closed_in_true_direction(self):
        pf = load("sweep_loop.pcf")
        for rot in range(4):
            sheet = iso_build.build_sheet(pf, iso_build.Options(rotation=rot))
            lay = sheet.layout
            self.assertTrue(lay.loops)
            self.assertEqual(lay.open_loops, [], rot)
            self.assertFalse([w for w in sheet.warnings if "loop" in w], rot)
            for e in lay.graph.edges:
                p, q = lay.segment(e)
                d = (q[0] - p[0], q[1] - p[1])
                w = lay.screen_dir(e)
                self.assertGreater((d[0] * w[0] + d[1] * w[1]) / math.hypot(*d), 0.9999, (rot, e.id))

    def test_plan_skew_triangle_carries_its_offsets(self):
        # 752 at 30 degrees in plan: 652 and 376.
        svg = mm_sheet("sweep_plan_skew.pcf").svg
        self.assertIn(">652<", svg)
        self.assertIn(">376<", svg)
        g = iso_graph.build(load("sweep_plan_skew.pcf"))
        skewed_runs = [r for r in g.runs if not r["axis"]]
        sheet = mm_sheet("sweep_plan_skew.pcf")
        self.assertEqual(len(iso_symbols.skew_marks(sheet.layout)), len(skewed_runs))

    def test_compound_skew_gives_all_three_offsets(self):
        sheet = mm_sheet("sweep_compound_skew.pcf")
        marks = iso_symbols.skew_marks(sheet.layout)
        legs = [len(m["legs"]) for m in marks]
        self.assertIn(3, legs)
        for m in marks:  # the offsets add back up to the run
            g = sheet.layout.graph
            nodes = m["run"]["nodes"]
            true = pcf_geom.dist(g.nodes[nodes[0]].pos, g.nodes[nodes[-1]].pos)
            self.assertAlmostEqual(math.sqrt(sum(v * v for _a, _b, v, _c in m["legs"])), true, delta=1.5)

    def test_gasket_and_bolts_share_a_balloon(self):
        sheet = mm_sheet("sweep_flange_stack.pcf")
        gasket = next(r.number for r in sheet.bom if r.category == "GASKETS")
        bolts = next(r.number for r in sheet.bom if r.category == "BOLTS")
        centres = {}
        for n, c, _a in sheet.balloons:
            centres.setdefault(c, set()).add(n)
        shared = [ns for ns in centres.values() if ns == {gasket, bolts}]
        self.assertEqual(len(shared), 8)  # eight joints, one oblong balloon each
        self.assertIn(iso_bom.PAIR_SPACES.join([str(gasket), str(bolts)]), sheet.svg)


if __name__ == "__main__":
    unittest.main()
