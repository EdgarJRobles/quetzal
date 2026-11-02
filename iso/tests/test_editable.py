# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tests for keeping hand edits to the BOM and notes (no FreeCAD needed)."""

import unittest

from iso import iso_editable
from iso.iso_bom import BomItem
from iso.iso_editable import HEADER, Row


def bom(qty="1848"):
    return [
        BomItem(1, "PIPE", "4\"", "PIPE NPS 4 SCH-40", qty, key="P4"),
        BomItem(2, "FLANGES", "4\"", "FLANGE NPS 4 WN 600lb", "2", key="F4"),
    ]


class BomTests(unittest.TestCase):
    def test_fresh(self):
        rows, lost = iso_editable.bom_rows(bom())
        self.assertEqual(rows[0], HEADER)
        self.assertEqual([r.desc for r in rows[1:]],
                         ["PIPE", "PIPE NPS 4 SCH-40", "FLANGES", "FLANGE NPS 4 WN 600lb"])
        self.assertEqual(lost, [])

    def test_keeps_edited_description_and_regenerates_quantity(self):
        rows, _ = iso_editable.bom_rows(bom())
        previous = rows[1:]
        previous[1].desc = "PIPE NPS 4 SCH-40 A106 GR B SMLS BE"  # user spec
        previous[1].qty = "999"  # quantities are not user data
        rows, lost = iso_editable.bom_rows(bom(qty="2000"), previous)
        pipe = [r for r in rows if r.key == "item:P4"][0]
        self.assertEqual(pipe.desc, "PIPE NPS 4 SCH-40 A106 GR B SMLS BE")
        self.assertEqual(pipe.qty, "2000")
        self.assertEqual(pipe.gen, "PIPE NPS 4 SCH-40")  # still knows it was edited
        self.assertEqual(lost, [])

    def test_unedited_description_follows_the_model(self):
        rows, _ = iso_editable.bom_rows(bom())
        changed = bom()
        changed[1].description = "FLANGE NPS 4 WN 900lb"
        rows, _ = iso_editable.bom_rows(changed, rows[1:])
        self.assertIn("FLANGE NPS 4 WN 900lb", [r.desc for r in rows])

    def test_user_rows_kept_at_the_end(self):
        rows, _ = iso_editable.bom_rows(bom())
        previous = rows[1:] + [Row("", "1", "", "PAINT PER SPEC P-2"), Row()]
        rows, _ = iso_editable.bom_rows(bom(), previous)
        self.assertEqual([r.desc for r in rows[-2:]], ["ADDITIONAL", "PAINT PER SPEC P-2"])
        # Regenerating again does not duplicate the ADDITIONAL heading.
        rows, _ = iso_editable.bom_rows(bom(), rows[1:])
        self.assertEqual([r.desc for r in rows].count("ADDITIONAL"), 1)

    def test_lost_edit_is_reported(self):
        rows, _ = iso_editable.bom_rows(bom())
        previous = rows[1:]
        previous[3].desc = "FLANGE, EDITED"
        rows, lost = iso_editable.bom_rows(bom()[:1], previous)
        self.assertEqual(lost, [("item:F4", "FLANGE, EDITED")])


class NotesTests(unittest.TestCase):
    def test_numbering_and_wrapping(self):
        lines = iso_editable.note_lines(["NOT TO SCALE.", "A B C D E F G H I J K L M N O P"], 20)
        self.assertEqual(lines[0], "1. NOT TO SCALE.")
        self.assertTrue(lines[1].startswith("2. "))
        self.assertTrue(lines[2].startswith("   "))  # hanging indent
        self.assertTrue(all(len(line) <= 20 for line in lines))

    def test_user_notes_kept(self):
        gen = ["1. NOT TO SCALE.", "2. DIMENSIONS IN MILLIMETRES."]
        current = ["NOTES:"] + gen + ["3. HYDROTEST TO 1.5 x DESIGN PRESSURE."]
        new = ["1. NOT TO SCALE.", "2. DIMENSIONS IN FEET AND INCHES."]
        lines, ok = iso_editable.merge_notes(current, gen, new)
        self.assertTrue(ok)
        self.assertEqual(lines, ["NOTES:"] + new + ["3. HYDROTEST TO 1.5 x DESIGN PRESSURE."])

    def test_edited_generated_notes_left_alone(self):
        gen = ["1. NOT TO SCALE."]
        current = ["NOTES:", "1. NOT TO SCALE. FIELD VERIFY ALL."]
        lines, ok = iso_editable.merge_notes(current, gen, ["1. SOMETHING ELSE."])
        self.assertFalse(ok)
        self.assertEqual(lines, current)

    def test_first_write(self):
        lines, ok = iso_editable.merge_notes([], [], ["1. NOT TO SCALE."])
        self.assertEqual(lines, ["NOTES:", "1. NOT TO SCALE."])


if __name__ == "__main__":
    unittest.main()
