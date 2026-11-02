# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tests for elbow designations (no FreeCAD needed)."""

import unittest

from pcf.pcf_fittings import elbow_designation


class ElbowDesignationTests(unittest.TestCase):
    def check(self, angle, radius, dn, code, bend):
        des = elbow_designation(angle, radius, dn)
        self.assertEqual(des.code, code)
        self.assertEqual(des.is_bend, bend)

    def test_standard_elbows(self):
        self.check(90, 76.2, 50, "90-LR", False)  # 1.5 x 2"
        self.check(45, 76.2, 50, "45-LR", False)
        self.check(90, 50.8, 50, "90-SR", False)  # 1.0 x 2"

    def test_bends_by_od_or_nominal(self):
        self.check(45, 685.8, 100, "45-6D", True)  # 6 x 4.5" OD
        self.check(45, 1314.45, 200, "45-6D", True)  # 6 x 8.625" OD, not 6.47 x nominal
        self.check(45, 304.8, 100, "45-3D", True)  # 3 x 4" nominal
        self.check(22.5, 609.6, 100, "22.5-6D", True)

    def test_custom_radius(self):
        self.check(30, 500, 100, "30-R500", True)  # 4.92 x nominal: not 5D


if __name__ == "__main__":
    unittest.main()
