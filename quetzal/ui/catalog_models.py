# SPDX-License-Identifier: LGPL-3.0-or-later
"""Qt list models backed by the catalogue presenters."""

from __future__ import annotations

from typing import Sequence

from PySide.QtCore import QAbstractListModel, QModelIndex, Qt

from ..application.catalog_presenter import RatingOption, SizeOption
from ..application.section_catalog import SectionSize


class RatingListModel(QAbstractListModel):
    CodeRole = Qt.UserRole + 1

    def __init__(self, options: Sequence[RatingOption], parent=None) -> None:
        super().__init__(parent)
        self._options = tuple(options)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._options)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._options):
            return None
        option = self._options[index.row()]
        if role == Qt.DisplayRole:
            return option.code
        if role == self.CodeRole:
            return option.code
        if role == Qt.ToolTipRole:
            return f"{option.institution} / {option.standard}"
        return None


class SizeListModel(QAbstractListModel):
    RowRole = Qt.UserRole + 1

    def __init__(self, options: Sequence["SizeOption | SectionSize"], parent=None) -> None:
        super().__init__(parent)
        self._options = tuple(options)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._options)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._options):
            return None
        option = self._options[index.row()]
        if role == Qt.DisplayRole:
            return option.label
        if role == self.RowRole:
            return option.row
        return None
