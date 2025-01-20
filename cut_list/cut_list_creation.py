import FreeCAD

from dataclasses import dataclass
from typing import List

from . import resultSpreadsheet


@dataclass
class Cut:
    """Store the Information about the cut Piece and provide Helper Functions"""

    label: str
    profil: str
    length: object
    cutwidth: object
    position: int = 0

    def getKey(self):
        """Provide a Key to generate the Position Number"""
        return self.profil + "|" + str(round(self.length.getValueAs("mm"), 2))

    def totalLength(self):
        return self.length + self.cutwidth

    def getRow(self):
        """Provide the Information from the Cut Piece in the form of a dict"""
        return {
            "Label": self.label,
            "Profil": self.profil,
            "Length": self.length,
            "CutWidth": self.cutwidth,
            "Pos.": self.position,
        }


@dataclass
class Beam:
    """Store the Information about the Stock Material Beam and provide Helper Functions"""

    number: int
    length: object
    lengthLeft: object
    cuts: List[Cut]

    def addCut(self, cut):
        """Try to fit the cut piece on the Beam and provide a status if it fits"""
        if self.length.getValueAs("mm") > 0.1 and self.lengthLeft < cut.totalLength():
            # Cut is not Possible on this Beam
            # Ignore if Beam has no length
            return False

        self.cuts.append(cut)
        self.lengthLeft -= cut.totalLength()
        return True

    def getCutsAsDict(self):
        """Get a easy to work with Dict List of the Beams / Cuts"""
        return [x.getRow() for x in self.cuts]

    def lengthUsed(self):
        return self.length - self.lengthLeft


def queryStructures(profiles: list, rootObjs=None):
    """Find all Structure Elements that use one of the selected profiles"""

    resultObjs = []

    if rootObjs is None:
        rootObjs = FreeCAD.ActiveDocument.Objects

    for obj in rootObjs:
        # Follow Link Groups
        if obj.TypeId == "App::LinkGroup":
            resultObjs = resultObjs + queryStructures(profiles, obj.ElementList)

        # Get the base Profile Used for the Structure
        base = getattr(obj, "Base", None)
        computedLength = getattr(obj, "ComputedLength", None)

        # Check if the Object is a valid Structure
        if base is None or computedLength is None:
            continue

        if base.Label in profiles:
            resultObjs.append(obj)

    return resultObjs


def nestCuts(profiles: list, beamLength, cutwidth):
    """Nest a List of Cuts on a Standard Beam length to estimate the needed Beams."""

    allStructures = queryStructures(profiles)

    # Sort Cuts Big to Small
    sortedStructures = sorted(allStructures, key=lambda x: x.ComputedLength, reverse=True)

    allCuts = []
    beams = []  # List of Lists to reference what is together in one beam [beamLength,[Cut1,Cut2...]]
    beam = Beam(1, beamLength, beamLength, [])
    beams.append(beam)

    # Go through all Structure Objects and try to fit them onto the Beams
    for obj in sortedStructures:
        # Create Cut Object to hold all Attributes
        label = obj.Label
        profile = obj.Base.Label
        length = round(obj.ComputedLength, 2)
        cutObj = Cut(label, profile, length, cutwidth)

        cutKey = cutObj.getKey()

        # Use the Key to define the Position Number of the Cut
        if cutKey not in allCuts:
            allCuts.append(cutKey)
            cutObj.position = len(allCuts)
        else:
            cutObj.position = allCuts.index(cutKey) + 1

        # Try to fit the Object on existing Beam
        nofit = True
        for beam in beams:
            if beam.addCut(cutObj):
                nofit = False
                break

        # Add new Beam and add the Cut to it
        if nofit:
            beam = Beam(len(beams) + 1, beamLength, beamLength, [])
            beams.append(beam)
            if not beam.addCut(cutObj):
                raise ValueError("Cut longer than beam!")

    return beams


def createSpreadSheetReport(beams, name="Result_Nest_Profile"):
    """Create a Spreadsheet as the Result of the Cut list Generation.
    Each Piece will be displayed as One Row
    """
    result = FreeCAD.ActiveDocument.addObject("Spreadsheet::Sheet", name)

    columnLabels = ["Pos.", "Profil", "Label", "Length"]
    result = resultSpreadsheet.ResultSpreadsheet(result, columnLabels)

    for beam in beams:
        result.printHeader(f"Beam No. {beam.number}")

        # Print the Used Length if a maximum Stock Value is given
        beamLength = round(beam.length, 2)
        if beamLength.getValueAs("mm") <= 0.1:
            result.printHeader(f"Used {round(beam.lengthUsed(), 2)}")
        else:
            result.printHeader(f"Used {round(beam.lengthUsed(), 2)} of {beamLength}")

        result.printColumnLabels()
        result.printRows(beam.getCutsAsDict())
        result.printEmptyLine()

    result.recompute()


def createSpreadSheetReportGrouped(beams, name="Result_Nest_Profile"):
    """Create a Spreadsheet as the Result of the Cut list Generation.
    The Pieces will be grouped by the Length and Profile.
    """

    result = FreeCAD.ActiveDocument.addObject("Spreadsheet::Sheet", name)

    columnLabels = ["Pos.", "Profil", "Length", "Quantity"]
    result = resultSpreadsheet.ResultSpreadsheet(result, columnLabels)

    for beam in beams:
        result.printHeader(f"Beam No. {beam.number}")

        # Print the Used Length if a maximum Stock Value is given
        beamLength = round(beam.length, 2)
        if beamLength.getValueAs("mm") <= 0.1:
            result.printHeader(f"Used {round(beam.lengthUsed(), 2)}")
        else:
            result.printHeader(f"Used {round(beam.lengthUsed(), 2)} of {beamLength}")

        result.printColumnLabels()

        resultRows = []
        usedKeys = []

        for cut in beam.cuts:
            # Add only one Row for each Key on the Beam
            currentCutKey = cut.getKey()
            if currentCutKey not in usedKeys:
                roWDict = cut.getRow()
                # Calculate the Number of the same pieces
                roWDict["Quantity"] = len([x for x in beam.cuts if x.getKey() == currentCutKey])

                resultRows.append(roWDict)
                usedKeys.append(cut.getKey())

        result.printRows(resultRows)
        result.printEmptyLine()

    result.recompute()


def createCutlist(profiles, maxBeamLength, cutWidth, GroupByLength=False):
    """Nest the Cuts to the Beams and create the Report Spreadsheet"""

    profilesLabel = "_".join(profiles)
    tableName = f"Cut_List_{profilesLabel}"

    beams = nestCuts(profiles, maxBeamLength, cutWidth)

    if GroupByLength:
        createSpreadSheetReportGrouped(beams, tableName)
    else:
        createSpreadSheetReport(beams, tableName)
