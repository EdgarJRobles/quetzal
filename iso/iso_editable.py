# SPDX-License-Identifier: LGPL-3.0-or-later
"""Merge rules for the editable BOM and notes of an isometric (pure Python).

On a TechDraw page the BOM is a spreadsheet and the notes an annotation, both
editable by hand.  Regenerating must keep those edits:

BOM: PT, QTY and SIZE always follow the model (they must agree with the
  balloons).  A DESCRIPTION the user changed is kept; rows remember their item
  key and the generated text in hidden columns to tell the two apart.  Rows
  the user added (no key) are kept at the end under ADDITIONAL.
Notes: the generated block at the top is refreshed and the user's notes below
  it are kept.  If the user edited the generated block itself, nothing is
  changed.
"""

import textwrap
from dataclasses import dataclass

NOTES_TITLE = "NOTES:"


@dataclass
class Row:
    pt: str = ""
    qty: str = ""
    size: str = ""
    desc: str = ""
    key: str = ""  # "item:<bom key>", "cat:<name>", "header" or "" for user rows
    gen: str = ""  # generated description, to detect user edits

    @property
    def style(self):
        if self.key in ("header",) or self.key.startswith("cat:"):
            return "bold"
        return ""

    def is_blank(self):
        return not any((self.pt, self.qty, self.size, self.desc))


HEADER = Row("PT", "QTY", "SIZE", "DESCRIPTION", key="header")


def bom_rows(bom, previous=()):
    """Spreadsheet rows for bom (a list of iso_bom.BomItem), keeping the edits
    found in previous (rows read back from the sheet, header excluded).

    Returns (rows, lost): lost lists (key, description) of edited rows whose
    item is no longer in the model, so the caller can report them."""
    edited = {r.key: r.desc for r in previous if r.key.startswith("item:") and r.desc != r.gen}
    user = [r for r in previous if not r.key and not r.is_blank()]
    rows = [HEADER]
    category = None
    used = set()
    for item in bom:
        if item.category != category:
            category = item.category
            rows.append(Row(desc=category, key="cat:" + category))
        key = "item:" + item.key
        used.add(key)
        rows.append(Row(str(item.number), item.quantity, item.size,
                        edited.get(key, item.description), key, item.description))
    if user:
        rows.append(Row(desc="ADDITIONAL", key="cat:ADDITIONAL"))
        rows.extend(user)
    lost = [(k, text) for k, text in edited.items() if k not in used]
    return rows, lost


def note_lines(notes, chars):
    """Numbered notes wrapped to chars per line, continuation lines indented."""
    lines = []
    for i, note in enumerate(notes, 1):
        prefix = "%d. " % i
        wrapped = textwrap.wrap(note, max(10, chars - len(prefix))) or [""]
        lines.append(prefix + wrapped[0])
        lines.extend(" " * len(prefix) + w for w in wrapped[1:])
    return lines


def merge_notes(current, old_generated, new_generated):
    """(lines, refreshed): the annotation text after regenerating.

    current: the annotation's lines now; old_generated: the generated lines
    written last time.  The user's lines after the generated block are kept."""
    head = [NOTES_TITLE] + list(old_generated)
    if not current or list(current) == ["Default Text"]:
        return [NOTES_TITLE] + list(new_generated), True
    if list(current[:len(head)]) == head:
        return [NOTES_TITLE] + list(new_generated) + list(current[len(head):]), True
    return list(current), False
