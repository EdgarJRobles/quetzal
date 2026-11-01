# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the isometric generator (no FreeCAD needed).

Run from the repository root with:
    python -m unittest discover -s iso/tests -t .
"""

import math
import os
import time
import unittest
import xml.etree.ElementTree as ET

from pcf import pcf_geom, pcf_model
from iso import iso_build, iso_format, iso_graph, iso_layout, iso_sheet, iso_symbols

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "pcf", "tests", "data")


def load(name, index=0):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return pcf_model.to_mm(pcf_model.parse(f.read())[index])


def zigzag_pcf(legs=20):
    """A long line turning through all three axes, with a valve on every leg."""
    text = ["UNITS-BORE MM", "UNITS-CO-ORDS MM", "PIPELINE-REFERENCE ZIGZAG"]
    axes = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0), (0, 0, -1)]
    p = (0.0, 0.0, 0.0)
    for i in range(legs):
        d = axes[i % len(axes)]
        length = 800 + 150 * (i % 5)
        q = tuple(p[k] + d[k] * length for k in range(3))
        v1 = tuple(p[k] + d[k] * 300 for k in range(3))
        v2 = tuple(p[k] + d[k] * 500 for k in range(3))
        for kw, a, b, skey in (("PIPE", p, v1, ""), ("VALVE", v1, v2, "VBFL"), ("PIPE", v2, q, "")):
            text.append(kw)
            text.append("    END-POINT %.1f %.1f %.1f 100" % a)
            text.append("    END-POINT %.1f %.1f %.1f 100" % b)
            if skey:
                text.append("    SKEY " + skey)
        p = q
    return pcf_model.parse("\n".join(text) + "\n")[0]


class FormatTests(unittest.TestCase):
    def test_ftin(self):
        self.assertEqual(iso_format.ftin(4036.65), "13'-2 15/16\"")
        self.assertEqual(iso_format.ftin(326.8), "1'-0 7/8\"")
        self.assertEqual(iso_format.ftin(300.45), "11 13/16\"")
        self.assertEqual(iso_format.ftin(1219.2), "4'-0\"")
        self.assertEqual(iso_format.ftin(6.35), "1/4\"")

    def test_sizes(self):
        self.assertEqual(iso_format.size_text(50, "MM", "NPS"), '2"')
        self.assertEqual(iso_format.size_text(32, "MM", "NPS"), '1-1/4"')
        self.assertEqual(iso_format.size_text(1.5, "INCH", "DN"), "DN40")
        self.assertEqual(iso_format.size_text(100, "MM", "DN"), "DN100")


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.pf = load("foreign.pcf")
        self.g = iso_graph.build(self.pf)

    def test_topology(self):
        self.assertEqual(len(self.g.nodes), 20)
        self.assertEqual(len(self.g.edges), 18)  # the header pipe is split at the olet
        self.assertEqual(self.g.skipped, [])
        self.assertTrue(all(e.axis in ("X", "Y", "Z") for e in self.g.edges))

    def test_welds_and_work_points(self):
        by_pos = {tuple(round(c, 1) for c in n.pos): n for n in self.g.nodes}
        self.assertEqual(by_pos[(1000.0, 0.0, 0.0)].weld, "BW")  # pipe to elbow
        self.assertEqual(by_pos[(1152.4, 0.0, 1668.1)].weld, "")  # flange face
        self.assertTrue(by_pos[(1152.4, 0.0, 1668.1)].work_point)
        self.assertFalse(by_pos[(1152.4, 0.0, 1671.1)].work_point)  # other gasket face
        self.assertEqual(by_pos[(500.0, 0.0, 0.0)].weld, "BW")  # olet on header

    def test_markers_snap(self):
        kinds = {m.kind: m for m in self.g.markers}
        self.assertGreaterEqual(kinds["bolt"].edge, 0)
        self.assertGreaterEqual(kinds["support"].edge, 0)  # given at the pipe bottom

    def test_connected(self):
        lay = iso_layout.place(iso_layout.Layout(self.g))
        # One piece for the line and one for the stand-alone instrument.
        roots = [n for n, (parent, _e) in lay.parent.items() if parent is None]
        self.assertEqual(len(roots), 2)


ECCENTRIC = """UNITS-BORE MM
UNITS-CO-ORDS MM
PIPELINE-REFERENCE ECC
PIPE
    END-POINT 0 0 25.4 200
    END-POINT 0 1000 25.4 200
REDUCER-ECCENTRIC
    END-POINT 0 1000 25.4 200
    END-POINT 0 1152 0 150
    SKEY REBW
PIPE
    END-POINT 0 1152 0 150
    END-POINT 0 2000 0 150
"""


class EccentricTests(unittest.TestCase):
    def setUp(self):
        self.pf = pcf_model.parse(ECCENTRIC)[0]
        self.g = iso_graph.build(self.pf)

    def test_snapped_and_flat_on_bottom(self):
        red = [e for e in self.g.edges if e.role == "inline"][0]
        self.assertEqual(red.axis, "Y")
        self.assertAlmostEqual(red.length, 152.0)
        # Small end dropped to keep the bottoms level: flat on bottom.
        for got, want in zip(red.flat, (0.0, 0.0, -1.0)):
            self.assertAlmostEqual(got, want)
        self.assertEqual(len(self.g.runs), 1)  # one straight run through the reducer

    def test_dimensions_to_both_reducer_ends(self):
        sheet = iso_build.build_sheet(self.pf)
        # Pipe to the large end, the reducer itself (a take-out the welder
        # checks against the real fitting) and pipe from the small end, all
        # along the run: the reducer's 25.4 mm centre offset does not count.
        self.assertEqual(sorted(round(d.value, 1) for d in sheet.dimensions), [152.0, 848.0, 1000.0])


VENT_AND_DRAIN = """UNITS-BORE MM
UNITS-CO-ORDS MM
PIPELINE-REFERENCE HEADER
PIPE
    END-POINT 0 0 0 200
    END-POINT 2000 0 0 200
OLET
    CENTRE-POINT 1000 0 0
    BRANCH1-POINT 1000 0 130 25
    SKEY WTBW
PIPE
    END-POINT 1000 0 130 25
    END-POINT 1000 0 280 25
OLET
    CENTRE-POINT 1000 0 0
    BRANCH1-POINT 1000 0 -150 50
    SKEY WTBW
ELBOW
    END-POINT 1000 0 -150 50
    END-POINT 1076 0 -226 50
    CENTRE-POINT 1000 0 -226
    SKEY ELBW
"""


class BranchStackTests(unittest.TestCase):
    def test_opposite_olets_are_separate_runs(self):
        pf = pcf_model.parse(VENT_AND_DRAIN)[0]
        sheet = iso_build.build_sheet(pf)
        values = sorted(round(d.value, 1) for d in sheet.dimensions)
        # Header 1000 + 1000 and the vent nipple (olet centre to its end, 280);
        # not the drain's olet + elbow (226), although the vent pipe is on the
        # same vertical line through the header.
        self.assertEqual(values, [280.0, 1000.0, 1000.0])


class KickerTests(unittest.TestCase):
    """A kicker rising 0.42 deg (1:134) to meet an eccentric reducer's offset:
    below the 1 deg drawing tolerance, so it is drawn level, but the slope must
    still be called out.  The elbow's 0.42 deg roll is what makes that slope,
    so the slope note is its only callout."""

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "data", "kicker.pcf")
        with open(path, encoding="utf-8") as f:
            self.pf = pcf_model.parse(f.read())[0]

    def test_slope_called_out_once(self):
        from iso import iso_dims
        g = iso_graph.build(self.pf)
        slopes = [iso_dims.slope_text(e.slope) for e in g.edges if e.slope and e.role == "pipe"]
        self.assertEqual(slopes, ["SLOPE 1:134"])
        elbow = [i for i, c in enumerate(self.pf.components) if c.keyword == "ELBOW"][0]
        self.assertAlmostEqual(iso_dims.roll_angle(g, elbow), 0.42, places=2)
        sheet = iso_build.build_sheet(self.pf)
        self.assertIn("SLOPE 1:134", sheet.svg)
        self.assertNotIn("ROLL", sheet.svg)

    def test_no_false_callouts_on_square_lines(self):
        for name in ("foreign.pcf", "sample.pcf"):
            sheet = iso_build.build_sheet(load(name))
            self.assertNotIn("ROLL", sheet.svg, name)
            self.assertNotIn("SLOPE", sheet.svg, name)


def rolled_tee_pcf(roll_deg):
    """Header along X with a tee whose branch is rolled roll_deg from vertical."""
    r = math.radians(roll_deg)
    by, bz = 150.0 * math.sin(r), 150.0 * math.cos(r)
    return pcf_model.parse("""UNITS-BORE MM
UNITS-CO-ORDS MM
PIPELINE-REFERENCE TEE
PIPE
    END-POINT 0 0 0 150
    END-POINT 1000 0 0 150
TEE
    END-POINT 1000 0 0 150
    END-POINT 1300 0 0 150
    CENTRE-POINT 1150 0 0
    BRANCH1-POINT 1150 %.4f %.4f 100
    SKEY TEBW
PIPE
    END-POINT 1150 %.4f %.4f 100
    END-POINT 1150 %.4f %.4f 100
""" % (by, bz, by, bz, by * 5, bz * 5))[0]


class RollTests(unittest.TestCase):
    def test_rolled_tee_called_out_at_a_run_weld(self):
        from iso import iso_dims
        pf = rolled_tee_pcf(1.0)
        g = iso_graph.build(pf)
        tee = [i for i, c in enumerate(pf.components) if c.keyword == "TEE"][0]
        info = iso_dims.roll_info(g, tee)
        self.assertAlmostEqual(info["angle"], 1.0, places=3)
        weld = g.nodes[info["weld"]].pos
        self.assertAlmostEqual(weld[1], 0.0)  # the (square) run, not the branch
        self.assertAlmostEqual(weld[2], 0.0)
        # The rolled branch pipe is out of plumb, and its note says so; a
        # roll callout would repeat it.
        svg = iso_build.build_sheet(pf).svg
        self.assertIn("OUT OF PLUMB 1.0", svg)
        self.assertNotIn("ROLL", svg)

    def test_small_roll_ignored(self):
        self.assertNotIn("ROLL", iso_build.build_sheet(rolled_tee_pcf(0.2)).svg)

    def test_roll_direction_follows_the_rolled_leg(self):
        from iso import iso_dims
        g_pos, g_neg = iso_graph.build(rolled_tee_pcf(1.0)), iso_graph.build(rolled_tee_pcf(-1.0))
        lay_p = iso_layout.place(iso_layout.Layout(g_pos))
        lay_n = iso_layout.place(iso_layout.Layout(g_neg))
        tee = 1
        arc_p = iso_dims.roll_symbol(lay_p, iso_dims.roll_info(g_pos, tee), 1.0)[0].points
        arc_n = iso_dims.roll_symbol(lay_n, iso_dims.roll_info(g_neg, tee), 1.0)[0].points
        # Opposite rolls draw the same arc in opposite directions.
        self.assertAlmostEqual(arc_p[0][0], arc_n[-1][0], places=6)
        self.assertAlmostEqual(arc_p[-1][0], arc_n[0][0], places=6)


def elbows_pcf():
    """A DN50 90 LR and 45 LR sharing one item code (as a schedule-only
    PRating makes them), and a DN100 45 degree 6D bend."""
    def elbow(cx, angle, radius, bore):
        # First leg along +X into the centre, second leg turned by angle.
        t = radius * math.tan(math.radians(angle) / 2)
        a = math.radians(angle)
        return [
            "ELBOW",
            "    END-POINT %.3f 0 0 %d" % (cx - t, bore),
            "    END-POINT %.3f %.3f 0 %d" % (cx + t * math.cos(a), t * math.sin(a), bore),
            "    CENTRE-POINT %.3f 0 0" % cx,
            "    SKEY ELBW",
            "    ITEM-CODE ELBOW-DN%d-SCH-XS" % bore,
        ]

    lines = ["UNITS-BORE MM", "UNITS-CO-ORDS MM", "PIPELINE-REFERENCE ELBOWS",
             "MATERIALS", "ITEM-CODE ELBOW-DN50-SCH-XS", "    DESCRIPTION ELBOW NPS 2 SCH-XS"]
    lines += elbow(0, 90, 76.2, 50) + elbow(1000, 45, 76.2, 50) + elbow(3000, 45, 685.8, 100)
    return pcf_model.parse("\n".join(lines) + "\n")[0]


class ElbowBomTests(unittest.TestCase):
    def test_elbows_split_by_angle_and_radius(self):
        rows = iso_build.build_sheet(elbows_pcf(), iso_build.Options(units="ftin")).bom
        descs = sorted(r.description for r in rows)
        self.assertEqual(descs, ["BEND 45° 6D, R 2'-3\"", "ELBOW 45° LR, NPS 2 SCH-XS",
                                 "ELBOW 90° LR, NPS 2 SCH-XS"])
        self.assertEqual(len({r.number for r in rows}), 3)


class CameraTests(unittest.TestCase):
    def test_freecad_isometric_is_rotation_0(self):
        self.assertEqual(iso_layout.rotation_for_camera((-0.577, 0.577, -0.577), (-0.408, 0.408, 0.816)), 0)

    def test_each_rotation_finds_itself(self):
        for r in range(4):
            turns = (4 - r) % 4
            look = iso_layout.rotate_xy(iso_layout.VIEW_DIR, turns)
            up = iso_layout.rotate_xy(iso_layout.VIEW_UP, turns)
            self.assertEqual(iso_layout.rotation_for_camera(look, up), r)
            # The camera's view direction collapses to a point in that rotation.
            x, y = iso_layout.project(look, r)
            self.assertAlmostEqual(x, 0.0)
            self.assertAlmostEqual(y, 0.0)

    def test_from_below_uses_the_same_heading(self):
        # Looking up from below, heading like rotation 3 from above.
        self.assertEqual(iso_layout.rotation_for_camera((-0.577, -0.577, 0.577), (0.408, 0.408, 0.816)), 3)


class LauncherTests(unittest.TestCase):
    """A pig launcher with a sloped kicker (1:42) and three drains/vents.

    It once sent the clash pass into runaway stretching (factors ~1e21) that
    collapsed the whole drawing."""

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "data", "launcher.pcf")
        with open(path, encoding="utf-8") as f:
            self.pf = pcf_model.parse(f.read())[0]

    def test_sloped_kicker_is_drawn_on_its_axis(self):
        g = iso_graph.build(self.pf)
        self.assertEqual([e.id for e in g.edges if not e.axis], [])
        sloped = [e for e in g.edges if e.slope]
        self.assertTrue(sloped)
        from iso import iso_dims
        self.assertEqual(iso_dims.slope_text(sloped[0].slope), "SLOPE 1:42")

    def test_layout_stays_sane_in_every_rotation(self):
        for rot in range(4):
            sheet = iso_build.build_sheet(self.pf, iso_build.Options(rotation=rot))
            lay = sheet.layout
            self.assertGreaterEqual(lay.zoom, iso_layout.ZOOM_MIN)
            self.assertTrue(all(v <= iso_layout.MAX_STRETCH for v in lay.stretch.values()))
            self.assertGreater(sheet.scale, 0.5)
            self.assertLessEqual(len(lay.clashes), 3)

    def test_best_rotation_is_clean(self):
        sheet = iso_build.build_sheet(self.pf)
        self.assertEqual(sheet.layout.clashes, [])
        self.assertIn("SLOPE 1:42", sheet.svg)


class LayoutTests(unittest.TestCase):
    def check(self, pf):
        g = iso_graph.build(pf)
        lay = iso_layout.layout_graph(g, 230, 225)
        self.assertEqual(lay.clashes, [])
        for e in g.edges:  # every edge keeps its iso direction
            p, q = lay.segment(e)
            d = iso_layout.unit2((q[0] - p[0], q[1] - p[1]))
            want = lay.screen_dir(e)
            self.assertAlmostEqual(d[0] * want[0] + d[1] * want[1], 1.0, places=6)
        return lay

    def test_foreign(self):
        self.check(load("foreign.pcf"))

    def test_sample_inches(self):
        self.check(load("sample.pcf"))

    def test_zigzag(self):
        start = time.time()
        self.check(zigzag_pcf(20))
        self.assertLess(time.time() - start, 30.0)


class SheetTests(unittest.TestCase):
    def setUp(self):
        self.pf = load("foreign.pcf")
        self.sheet = iso_build.build_sheet(self.pf, iso_build.Options(sheet=iso_sheet.ISO_A3))

    def test_svg_is_valid(self):
        root = ET.fromstring(self.sheet.svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertEqual(root.get("width"), "420mm")

    def test_dimensions_are_true_lengths(self):
        g = self.sheet.layout.graph
        for d in self.sheet.dimensions:
            true = pcf_geom.dist(g.nodes[d.a].pos, g.nodes[d.b].pos)
            self.assertAlmostEqual(d.value, true, places=6)
            self.assertEqual(d.text, "%d" % round(true))
        values = sorted(round(d.value, 1) for d in self.sheet.dimensions)
        # Spans with pipe, plus tee/reducer take-outs on runs with pipe
        # (tee centre to reducer 104.8, the reducer 101.6).  Not the valve
        # face to face (219), the olet + elbow branch stack (120, 25) or the
        # stand-alone instrument (200).
        self.assertEqual(values, [101.6, 104.8, 356.9, 447.6, 500.0, 652.4, 1104.8])

    def test_bom(self):
        rows = {r.description: r for r in self.sheet.bom}
        self.assertEqual(rows["PIPE SMLS SCH 40"].quantity, "1848")
        self.assertEqual(rows["PIPE SMLS SCH 40"].size, "DN100")
        self.assertEqual([r.number for r in self.sheet.bom], list(range(1, len(self.sheet.bom) + 1)))
        categories = [r.category for r in self.sheet.bom]
        self.assertEqual(categories[0], "PIPE")
        self.assertLess(categories.index("FLANGES"), categories.index("VALVES"))

    def test_every_component_has_a_symbol_anchor(self):
        _items, anchors = iso_symbols.draw(self.sheet.layout)
        drawn = set(anchors)
        for ci, c in enumerate(self.pf.components):
            self.assertIn(ci, drawn, c.keyword)

    def test_balloons_on_sheet_and_apart(self):
        x0, y0, x1, y1 = iso_sheet.ISO_A3.iso_area
        pts = [c for _n, c, _a in self.sheet.balloons]
        self.assertEqual(len(pts), len(self.pf.components))
        for x, y in pts:
            self.assertTrue(x0 <= x <= x1 and y0 <= y <= y1, (x, y))
        r = 3.0 * self.sheet.scale
        pts = list(dict.fromkeys(pts))  # a gasket and its bolts share one balloon
        closest = min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:])
        self.assertGreaterEqual(closest, 2 * r)

    def test_feet_inches(self):
        sheet = iso_build.build_sheet(self.pf, iso_build.Options(units="ftin", size_system="NPS"))
        texts = {d.text for d in sheet.dimensions}
        self.assertIn("1'-7 11/16\"", texts)  # 500 mm
        self.assertIn('4"', {r.size for r in sheet.bom})

    def test_rotation_override(self):
        for rot in range(4):
            sheet = iso_build.build_sheet(self.pf, iso_build.Options(rotation=rot))
            self.assertEqual(sheet.layout.rotation, rot)


if __name__ == "__main__":
    unittest.main()
