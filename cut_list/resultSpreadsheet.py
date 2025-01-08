# Heavily Inspired Code from
# https://github.com/furti/FreeCAD-Reporting/blob/master/report.py

import FreeCAD
import FreeCADGui
import string


COLUMN_NAMES = list(string.ascii_uppercase)


def literalText(text):
    return "'%s" % (text)


def lineRange(startColumn, endColumn, lineNumber):
    return cellRange(startColumn, lineNumber, endColumn, lineNumber)


def cellRange(startColumn, startLine, endColumn, endLine):
    return "%s%s:%s%s" % (startColumn, startLine, endColumn, endLine)


def nextColumnName(actualColumnName):
    if actualColumnName is None:
        return COLUMN_NAMES[0]

    nextIndex = COLUMN_NAMES.index(actualColumnName) + 1

    if nextIndex >= len(COLUMN_NAMES):
        nextIndex -= len(COLUMN_NAMES)

    return COLUMN_NAMES[nextIndex]


class ResultSpreadsheet(object):

    def __init__(self, spreadsheet, columnLabels):

        self.spreadsheet = spreadsheet
        self.lineNumber = 1
        self.maxColumn = None
        self.columnLabels = columnLabels

    def getColumnName(self, label):
        if label is None:
            return COLUMN_NAMES[0]

        nextIndex = self.columnLabels.index(label)

        if nextIndex >= len(COLUMN_NAMES):
            nextIndex -= len(COLUMN_NAMES)

        return COLUMN_NAMES[nextIndex]

    def clearAll(self):
        self.spreadsheet.clearAll()

    def printEmptyLine(self):
        self.lineNumber += 1

    def printHeader(self, header="HAEADER"):
        spreadsheet = self.spreadsheet

        if header is None or header == "":
            return

        headerCell = "A%s" % (self.lineNumber)

        self.setCellValue(headerCell, header)
        spreadsheet.setStyle(headerCell, "bold|underline", "add")

        spreadsheet.mergeCells(
            lineRange("A", COLUMN_NAMES[len(self.columnLabels) - 1], self.lineNumber)
        )

        self.lineNumber += 1
        self.updateMaxColumn("A")

        self.clearLine(self.lineNumber)

    def printColumnLabels(self):
        spreadsheet = self.spreadsheet

        columnName = None

        for columnLabel in self.columnLabels:
            columnName = self.getColumnName(columnLabel)
            cellName = f"{columnName}{self.lineNumber}"

            self.setCellValue(cellName, columnLabel)

        spreadsheet.setStyle(lineRange("A", columnName, self.lineNumber), "bold", "add")

        self.lineNumber += 1
        self.updateMaxColumn(columnName)

        self.clearLine(self.lineNumber)

    def printRows(self, rows):
        lineNumberBefore = self.lineNumber

        columnName = "A"
        for row in rows:
            columnName = None

            for columnlabel, value in row.items():
                if columnlabel in self.columnLabels:
                    columnName = self.getColumnName(columnlabel)
                    cellName = f"{columnName}{self.lineNumber}"

                    self.setCellValue(cellName, value)

            self.lineNumber += 1

        # if printResultInBold:
        #    self.spreadsheet.setStyle(
        #        cellRange('A', lineNumberBefore, columnName, self.lineNumber), 'bold', 'add')

        self.clearLine(self.lineNumber)

        self.updateMaxColumn(columnName)

    def setCellValue(self, cell, value):
        if value is None:
            convertedValue = ""
        elif isinstance(value, FreeCAD.Units.Quantity):
            convertedValue = value.UserString
        else:
            convertedValue = str(value)

        convertedValue = literalText(convertedValue)

        self.spreadsheet.set(cell, convertedValue)

    def recompute(self):
        self.spreadsheet.recompute()

    def updateMaxColumn(self, columnName):
        if self.maxColumn is None:
            self.maxColumn = columnName
        else:
            actualIndex = COLUMN_NAMES.index(self.maxColumn)
            columnIndex = COLUMN_NAMES.index(columnName)

            if actualIndex < columnIndex:
                self.maxColumn = columnName

    def clearUnusedCells(self, column, line):
        if line is not None and line > self.lineNumber:
            for lineNumberToDelete in range(line, self.lineNumber, -1):
                self.clearLine(lineNumberToDelete)

        if column is not None:
            columnIndex = COLUMN_NAMES.index(column)
            maxColumnIndex = COLUMN_NAMES.index(self.maxColumn)

            if columnIndex > maxColumnIndex:
                for columnIndexToDelete in range(columnIndex, maxColumnIndex, -1):
                    self.clearColumn(COLUMN_NAMES[columnIndexToDelete], line)

    def clearLine(self, lineNumberToDelete):

        column = None

        while column is None or column != self.maxColumn:
            column = nextColumnName(column)
            cellName = f"{column}{lineNumberToDelete}"

            self.spreadsheet.clear(cellName)

    def clearColumn(self, columnToDelete, maxLineNumber):

        for lineNumber in range(1, maxLineNumber):
            cellName = f"{columnToDelete}{lineNumber + 1}"

            self.spreadsheet.clear(cellName)
