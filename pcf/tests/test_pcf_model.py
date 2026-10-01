# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for pcf_model (no FreeCAD needed).

Run from the repository root with:
    python -m unittest discover -s pcf/tests -t .
"""

import os
import unittest

from pcf import pcf_model

DATA = os.path.join(os.path.dirname(__file__), "data", "sample.pcf")


def _load():
    with open(DATA, encoding="utf-8") as f:
        return pcf_model.parse(f.read())


class ParseTests(unittest.TestCase):
    def test_pipelines_and_header(self):
        files = _load()
        self.assertEqual([f.pipeline_reference for f in files], ["100-P-001", "100-P-002"])
        for f in files:
            self.assertEqual(f.units_bore, "INCH")
            self.assertEqual(f.units_coords, "INCH")
        self.assertEqual(files[0].pipeline_attr("PIPING-SPEC"), "A1A")

    def test_materials(self):
        f = _load()[0]
        self.assertEqual(f.materials["P2"], "PIPE SMLS ASTM A106-B")
        self.assertEqual(f.materials["E2"], "ELBOW 90 LR")

    def test_components(self):
        f = _load()[0]
        kws = [c.keyword for c in f.components]
        self.assertEqual(kws, ["PIPE", "ELBOW", "TEE", "REDUCER-ECCENTRIC", "INSTRUMENT"])
        pipe, elbow, tee, red, _ = f.components
        self.assertEqual(pipe.item_code, "P2")
        self.assertEqual(pipe.attr("FABRICATION-ITEM"), "")
        self.assertEqual(pipe.end_points[1].xyz(), (40.0, 0.0, 0.0))
        self.assertEqual(pipe.end_points[1].bore, 2.0)
        self.assertEqual(elbow.centre_point.xyz(), (43.0, 0.0, 0.0))
        self.assertEqual(elbow.skey, "ELBW")
        self.assertEqual(tee.branch_points[0].bore, 1.5)
        # Non-indented attribute lines still belong to the component.
        self.assertEqual(len(red.end_points), 2)
        self.assertEqual(red.skey, "REBW")
        self.assertEqual(red.attr("flat-direction"), "DOWN")

    def test_end_connection_token(self):
        pipe = _load()[1].components[0]
        self.assertEqual(pipe.end_points[0].bore, 1.0)
        self.assertEqual(pipe.end_points[0].extra, ["BW"])

    def test_to_mm(self):
        f = pcf_model.to_mm(_load()[0])
        self.assertAlmostEqual(f.components[0].end_points[1].x, 1016.0)
        self.assertEqual(f.units_coords, "MM")
        self.assertEqual(f.components[0].end_points[1].bore, 2.0)

    def test_bad_point(self):
        with self.assertRaises(ValueError):
            pcf_model.parse("PIPE\n    END-POINT 1 2\n")


class WriteTests(unittest.TestCase):
    def test_roundtrip_stable(self):
        for f in _load():
            text = pcf_model.write(f)
            again = pcf_model.write(pcf_model.parse(text)[0])
            self.assertEqual(text, again)

    def test_written_format(self):
        comp = pcf_model.PcfComponent(
            keyword="PIPE",
            end_points=[pcf_model.PcfPoint(0, 0, 0, 50), pcf_model.PcfPoint(1000, 0, 0, 50)],
            item_code="X1",
            attributes=[("COMPONENT-ATTRIBUTE1", "abc")],
        )
        pf = pcf_model.PcfFile(pipeline_reference="L1", components=[comp],
                               materials={"X1": "PIPE DN50"})
        text = pcf_model.write(pf)
        self.assertIn("UNITS-BORE MM\n", text)
        self.assertIn("PIPELINE-REFERENCE L1\n", text)
        self.assertIn("MATERIALS\nITEM-CODE X1\n    DESCRIPTION PIPE DN50\n", text)
        self.assertIn("    END-POINT 1000.0000 0.0000 0.0000 50\n", text)
        self.assertIn("    COMPONENT-ATTRIBUTE1 abc\n", text)


if __name__ == "__main__":
    unittest.main()
