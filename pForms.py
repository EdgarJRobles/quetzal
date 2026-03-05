# SPDX-License-Identifier: LGPL-3.0-or-later

__license__ = "LGPL 3"

import csv
from math import degrees
from os import listdir
from os.path import abspath, dirname, join

import FreeCAD
import FreeCADGui
import Part
from DraftVecUtils import rounded
from PySide.QtCore import *
from PySide.QtGui import *

import dodoDialogs
import fCmd
import pCmd
from PySide.QtWidgets import QCheckBox

pq = FreeCAD.Units.parseQuantity
translate = FreeCAD.Qt.translate

try:
    import quetzal_units as qu
except Exception:
    qu = None

mw = FreeCADGui.getMainWindow()
x = mw.x() + int(mw.width() / 20)  # 100
y = max(300, int(mw.height() / 3))  # 350


class redrawDialog(QDialog):
    def __init__(self):
        super(redrawDialog, self).__init__()
        self.setWindowTitle("Redraw PypeLines")
        self.resize(200, 350)
        self.verticalLayout = QVBoxLayout(self)
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 190, 338))
        self.formLayout = QFormLayout(self.scrollAreaWidgetContents)
        self.checkBoxes = list()
        self.pypelines = list()
        try:
            self.pypelines = [
                o.Label
                for o in FreeCAD.activeDocument().Objects
                if hasattr(o, "PType") and o.PType == "PypeLine"
            ]
            for pl in self.pypelines:
                self.checkBoxes.append(QCheckBox(self.scrollAreaWidgetContents))
                self.checkBoxes[-1].setText(pl)
                self.formLayout.layout().addWidget(self.checkBoxes[-1])
        except:
            None
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.scrollArea)
        self.btn1 = QPushButton("Redraw")
        self.verticalLayout.addWidget(self.btn1)
        self.btn1.clicked.connect(self.redraw)
        self.brn2 = QPushButton("Select all")
        self.verticalLayout.addWidget(self.brn2)
        self.brn2.clicked.connect(self.selectAll)
        self.btn3 = QPushButton("Clear all")
        self.verticalLayout.addWidget(self.btn3)
        self.btn3.clicked.connect(self.clearAll)
        self.show()

    def redraw(self):
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Redraw pipe-lines"))
        i = 0
        for cb in self.checkBoxes:
            if cb.isChecked():
                pl = FreeCAD.ActiveDocument.getObjectsByLabel(cb.text())[0]
                if pl.Base:
                    pl.Proxy.purge(pl)
                    pl.Proxy.update(pl)
                    i += 1
                else:
                    FreeCAD.Console.PrintError("%s has no Base: nothing to redraw\n" % cb.text())
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.Console.PrintMessage("Redrawn %i pipelines.\n" % i)
        FreeCAD.activeDocument().commitTransaction()

    def selectAll(self):
        for cb in self.checkBoxes:
            cb.setChecked(True)

    def clearAll(self):
        for cb in self.checkBoxes:
            cb.setChecked(False)


class insertPipeForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert tubes.
    For position and orientation you can select
      - one or more straight edges (centerlines)
      - one or more curved edges (axis and origin across the center)
      - one or more vertexes
      - nothing
    Default length = 200 mm.
    Available one button to reverse the orientation of the last or selected tubes.
    """

    def __init__(self):
        super(insertPipeForm, self).__init__(
            translate("insertPipeForm", "Insert pipes"),
            "Pipe",
            "SCH-STD",
            "pipe.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.btn1.clicked.connect(self.insert)
        self.edit1 = QLineEdit()
        _unit_hint = qu.get_length_unit() if qu else "mm"
        self.edit1.setPlaceholderText(
            translate("insertPipeForm", "<length> (") + _unit_hint + ")")
        self.edit1.setAlignment(Qt.AlignHCenter)
        self.edit1.editingFinished.connect(lambda: self.sli.setValue(100))
        self.secondCol.layout().addWidget(self.edit1)
        self.btn2 = QPushButton(translate("insertPipeForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.reverse)
        self.btn3 = QPushButton(translate("insertPipeForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.apply)
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.sli = QSlider(Qt.Vertical)
        self.sli.setMaximum(200)
        self.sli.setMinimum(1)
        self.sli.setValue(100)
        self.mainHL.addWidget(self.sli)
        self.sli.valueChanged.connect(self.changeL)

        #auto-select pipe size and rating if available
        pCmd.autoSelectInPipeForm(self)

        self.show()
        self.lastPipe = None
        self.H = 200

    def reverse(self):  # revert orientation of selected or last inserted pipe
        selPipes = [
            p
            for p in FreeCADGui.Selection.getSelection()
            if hasattr(p, "PType") and p.PType == "Pipe"
        ]
        if len(selPipes):
            for p in selPipes:
                pCmd.rotateTheTubeAx(p, FreeCAD.Vector(1, 0, 0), 180)
        else:
            pCmd.rotateTheTubeAx(self.lastPipe, FreeCAD.Vector(1, 0, 0), 180)

    def insert(self):  # insert the pipe
        self.lastPipe = None
        pipe_size_selected = self.pipeDictList[self.sizeList.currentRow()]
        rating = self.ratingList.currentItem().text()
        if self.edit1.text():
            self.H = float(pq(self.edit1.text()))
        self.sli.setValue(100)
        # DEFINE PROPERTIES
        """ Do not automatically choose rating, use only what is selected
        selex = FreeCADGui.Selection.getSelectionEx()
        if selex:
            for objex in selex:
                o = objex.Object
                if hasattr(o, "PSize") and hasattr(o, "OD") and hasattr(o, "thk"):
                    if (
                        o.PType == "Reduct"
                        and o.Proxy.nearestPort(objex.SubObjects[0].CenterOfMass)[0] == 1
                    ):  # props of a reduction
                        propList = [o.PSize, o.OD2, o.thk2, self.H]
                        break
                    else:
                        propList = [
                            o.PSize,
                            o.OD,
                            o.thk,
                            self.H,
                        ]  # props of other pypes
                        break
                else:
                    propList = [
                        pipe_size_selected["PSize"],
                        float(pq(pipe_size_selected["OD"])),
                        float(pq(pipe_size_selected["thk"])),
                        self.H,
                    ]  # props of the dialog
                    break
        else:
        """
        propList = [pipe_size_selected["PSize"], float(pq(pipe_size_selected["OD"])), float(pq(pipe_size_selected["thk"])), self.H]
        # INSERT PIPES
        self.lastPipe = pCmd.doPipes(rating,propList, FreeCAD.__activePypeLine__)[-1]
        self.H = float(self.lastPipe.Height)
        self.edit1.setText(str(float(self.H)))
        # TODO: SET PRATING
        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.lastPipe)

    def apply(self):
        self.lastPipe = None
        if self.edit1.text():
            self.H = float(pq(self.edit1.text()))
        else:
            self.H = 200.0
        self.sli.setValue(100)
        for obj in FreeCADGui.Selection.getSelection():
            d = self.pipeDictList[self.sizeList.currentRow()]
            if hasattr(obj, "PType") and obj.PType == self.PType:
                obj.PSize = d["PSize"]
                obj.OD = pq(d["OD"])
                obj.thk = pq(d["thk"])
                obj.PRating = self.PRating
                if self.edit1.text():
                    obj.Height = self.H
                FreeCAD.activeDocument().recompute()

    def changeL(self):
        if self.edit1.text():
            newL = self.H * self.sli.value() / 100
            self.edit1.setText(str(newL))
            if self.lastPipe:
                self.lastPipe.Height = newL
            FreeCAD.ActiveDocument.recompute()


class insertElbowForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert one elbow (butt-weld) or socket/threaded elbow.

    Butt-weld ratings (CSV has no "Conn" column, or Conn == "BW"):
      - sizeList shows PSize + OD x thk
      - edit1 = bend angle override, edit2 = bend radius override
      - Insert calls pCmd.doElbow; Apply updates BW-specific properties.

    Socket-weld / threaded ratings (CSV has Conn == "SW" or "TH"):
      - sizeList shows PSize + BendAngle° (one row per PSize+angle combination)
      - edit2 (bend radius) is hidden
      - Insert calls pCmd.doSocketElbow; Apply updates SW/TH-specific properties.
    """

    def __init__(self):
        super(insertElbowForm, self).__init__(
            translate("insertElbowForm", "Insert elbows"),
            "Elbow",
            "SCH-STD",
            "eilbow.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)

        # Disconnect base changeRating and reconnect to our handler so the
        # layout is refreshed whenever the rating type changes.
        try:
            self.ratingList.itemClicked.disconnect(self.changeRating)
        except Exception:
            pass
        self.ratingList.itemClicked.connect(self._changeRating)

        self.btn1.clicked.connect(self.insert)

        self.edit1 = QLineEdit()
        self.edit1.setPlaceholderText(translate("insertElbowForm", "<bend angle>"))
        self.edit1.setAlignment(Qt.AlignHCenter)
        self.edit1.setValidator(QDoubleValidator())
        self.secondCol.layout().addWidget(self.edit1)

        self.edit2 = QLineEdit()
        _unit_hint = qu.get_length_unit() if qu else "mm"
        self.edit2.setPlaceholderText(
            translate("insertElbowForm", "<bend radius> (") + _unit_hint + ")")
        self.edit2.setAlignment(Qt.AlignHCenter)
        self.secondCol.layout().addWidget(self.edit2)

        self.btn2 = QPushButton(translate("insertElbowForm", "Trim/Extend"))
        self.btn2.clicked.connect(self.trim)
        self.secondCol.layout().addWidget(self.btn2)
        self.btn3 = QPushButton(translate("insertElbowForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.reverse)
        self.btn4 = QPushButton(translate("insertElbowForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn4)
        self.btn4.clicked.connect(self.apply)
        self.btn1.setDefault(True)
        self.btn1.setFocus()

        self.screenDial = QWidget()
        self.screenDial.setLayout(QHBoxLayout())
        self.dial = QDial()
        self.dial.setMaximumSize(80, 80)
        self.dial.setWrapping(True)
        self.dial.setMaximum(180)
        self.dial.setMinimum(-180)
        self.dial.setNotchTarget(15)
        self.dial.setNotchesVisible(True)
        self.dial.setMaximumSize(70, 70)
        self.screenDial.layout().addWidget(self.dial)
        self.lab = QLabel(translate("insertElbowForm", "0 deg"))
        self.lab.setAlignment(Qt.AlignCenter)
        self.dial.valueChanged.connect(self.rotatePort)
        self.screenDial.layout().addWidget(self.lab)
        self.firstCol.layout().addWidget(self.screenDial)

        pCmd.autoSelectInPipeForm(self)
        self._refreshLayout()

        self.show()
        self.lastElbow = None
        self.lastAngle = 0

    # ── helper: detect SW/TH rating ──────────────────────────────────────────

    def _isSocketConn(self):
        """Return True when the loaded CSV is a SW or TH (socket/threaded) table."""
        for row in self.pipeDictList:
            if row.get("Conn", "").strip().upper() in ("SW", "TH"):
                return True
        return False

    # ── fillSizes override ───────────────────────────────────────────────────

    def fillSizes(self):
        """Load the CSV for the current rating and populate sizeList.

        Butt-weld CSVs (no Conn or Conn == "BW"):
            label = PSize  OD x thk       (standard Elbow display)

        Socket/threaded CSVs (Conn == "SW" or "TH"):
            label = PSize  <BendAngle>°   (angle shown because multiple rows
                                           per PSize are common, e.g. 90° / 45°)
        """
        self.sizeList.clear()
        self.pipeDictList = []
        fname = "Elbow_" + self.PRating + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r") as fh:
                self.pipeDictList = list(csv.DictReader(fh, delimiter=";"))
        except Exception:
            return

        if self._isSocketConn():
            # SW/TH: one list entry per row (PSize + bend angle)
            for row in self.pipeDictList:
                ang_str = row.get("BendAngle", "")
                if qu:
                    label = qu.format_psize(row["PSize"]) + "  " + ang_str + "°"
                else:
                    label = row["PSize"] + "  " + ang_str + "°"
                self.sizeList.addItem(label)
        else:
            # BW: standard PSize + OD x thk
            for row in self.pipeDictList:
                if qu:
                    label = qu.format_size_label(row)
                else:
                    label = row["PSize"] + "  " + row.get("OD", "") + "x" + row.get("thk", "")
                self.sizeList.addItem(label)

        self._refreshLayout()

    # ── rating-change handler ────────────────────────────────────────────────

    def _changeRating(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # ── layout refresh ───────────────────────────────────────────────────────

    def _refreshLayout(self):
        """Show/hide edit2 (bend radius) based on whether the CSV is SW/TH."""
        if self._isSocketConn():
            self.edit2.hide()
            self.edit2.setPlaceholderText("")
        else:
            _unit_hint = qu.get_length_unit() if qu else "mm"
            self.edit2.setPlaceholderText(
                translate("insertElbowForm", "<bend radius> (") + _unit_hint + ")")
            self.edit2.show()

    # ── insert ───────────────────────────────────────────────────────────────

    def insert(self):
        self.lastAngle = 0
        self.dial.setValue(0)
        d = self.pipeDictList[self.sizeList.currentRow()]

        try:
            ang = float(self.edit1.text())
            if ang > 180:
                ang = 180
                self.edit1.setText("180")
        except (ValueError, AttributeError):
            ang = float(pq(d["BendAngle"]))

        if self._isSocketConn():
            propList = [
                d["PSize"],
                float(pq(d["OD"])),
                ang,
                float(pq(d["A"])),
                float(pq(d["C"])),
                float(pq(d["D"])),
                float(pq(d["E"])),
                float(pq(d["G"])),
                d.get("Conn", "SW"),
            ]
            rating = self.ratingList.currentItem().text()
            self.lastElbow = pCmd.doSocketElbow(
                rating, propList, FreeCAD.__activePypeLine__)[-1]
        else:
            propList = [
                d["PSize"],
                float(pq(d["OD"])),
                float(pq(d["thk"])),
                ang,
                float(d["BendRadius"]),
            ]
            if self.edit2.text():
                propList[-1] = float(pq(self.edit2.text()))
            rating = self.ratingList.currentItem().text()
            self.lastElbow = pCmd.doElbow(
                rating, propList, FreeCAD.__activePypeLine__)[-1]

        FreeCAD.activeDocument().recompute()

    # ── trim ─────────────────────────────────────────────────────────────────

    def trim(self):
        if len(fCmd.beams()) == 1:
            pipe = fCmd.beams()[0]
            comPipeEdges = [e.CenterOfMass for e in pipe.Shape.Edges]
            eds = [e for e in fCmd.edges() if e.CenterOfMass not in comPipeEdges]
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Trim pipes"))
            for edge in eds:
                fCmd.extendTheBeam(fCmd.beams()[0], edge)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
        else:
            FreeCAD.Console.PrintError(translate("insertElbowForm", "Wrong selection\n"))

    # ── rotatePort ───────────────────────────────────────────────────────────

    def rotatePort(self):
        if self.lastElbow:
            pCmd.rotateTheElbowPort(self.lastElbow, 0, self.lastAngle * -1)
            self.lastAngle = self.dial.value()
            pCmd.rotateTheElbowPort(self.lastElbow, 0, self.lastAngle)
            self.lab.setText(str(self.dial.value()) + translate("insertElbowForm", " deg"))

    # ── apply ────────────────────────────────────────────────────────────────

    def apply(self):
        d = self.pipeDictList[self.sizeList.currentRow()]
        try:
            ang = float(self.edit1.text())
        except (ValueError, AttributeError):
            ang = float(pq(d["BendAngle"]))

        for obj in FreeCADGui.Selection.getSelection():
            if not hasattr(obj, "PType"):
                continue
            if obj.PType == "SocketEll" and self._isSocketConn():
                obj.PSize     = d["PSize"]
                obj.OD        = pq(d["OD"])
                obj.BendAngle = ang
                obj.A         = pq(d["A"])
                obj.C         = pq(d["C"])
                obj.D         = pq(d["D"])
                obj.E         = pq(d["E"])
                obj.G         = pq(d["G"])
                obj.Conn      = d.get("Conn", "SW")
                obj.PRating   = self.PRating
                FreeCAD.activeDocument().recompute()
            elif obj.PType == "Elbow" and not self._isSocketConn():
                obj.PSize = d["PSize"]
                obj.OD    = pq(d["OD"])
                obj.thk   = pq(d["thk"])
                obj.BendAngle = ang
                if self.edit2.text():
                    obj.BendRadius = float(pq(self.edit2.text()))
                else:
                    obj.BendRadius = pq(d["BendRadius"])
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()

    # ── reverse ──────────────────────────────────────────────────────────────

    def reverse(self):
        if self.lastElbow is None:
            return
        port = 0
        initial_port_pos = self.lastElbow.Placement.multVec(self.lastElbow.Ports[port])
        crossVector1 = FreeCAD.Vector(0, 0, 1)
        crossVector2 = FreeCAD.Vector(self.lastElbow.Ports[port])
        if crossVector2 == FreeCAD.Vector(0, 0, 0):
            crossVector2 = FreeCAD.Vector(0, 1, 0)
        crossVector2.normalize()
        if crossVector2 == crossVector1:
            crossVector1 = FreeCAD.Vector(0, 1, 0)
        pCmd.rotateTheTubeAx(self.lastElbow, crossVector1.cross(crossVector2), angle=180)
        final_port_pos = self.lastElbow.Placement.multVec(self.lastElbow.Ports[port])
        self.lastElbow.Placement.move(initial_port_pos - final_port_pos)

class insertTeeForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert one tee (butt-weld) or socket/threaded tee.

    Butt-weld ratings (CSV has no "Conn" column, or Conn == "BW"):
      - Primary sizeList   : unique run PSize values, labelled PSize + OD x thk
      - Secondary branchList: branch sizes for the selected run (OD2 x thk2)
      - Insert calls pCmd.doTees; Apply updates BW Tee properties.

    Socket-weld / threaded ratings (CSV has Conn == "SW" or "TH"):
      - Primary sizeList   : unique run PSize values, labelled PSize + OD
      - Secondary branchList: branch sizes for the selected run (PSizeBranch + OD2)
      - Insert calls pCmd.doSocketTee; Apply updates SW/TH SocketTee properties.
    """

    def __init__(self):
        super(insertTeeForm, self).__init__(
            translate("insertTeeForm", "Insert tee"),
            "Tee",
            "SCH-STD",
            "Tee.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)

        # Disconnect base changeRating and reconnect to our handler so the
        # branch list format is refreshed when the rating type changes.
        try:
            self.ratingList.itemClicked.disconnect(self.changeRating)
        except Exception:
            pass
        self.ratingList.itemClicked.connect(self._changeRating)

        # Branch size list
        self._branchDictList = []
        self._branchList = QListWidget()
        self._branchList.setMaximumHeight(100)
        branchLabel = QLabel(translate("insertTeeForm", "Branch size:"))
        self.secondCol.layout().addWidget(branchLabel)
        self.secondCol.layout().addWidget(self._branchList)

        self.insertModeGroup = QButtonGroup()
        self.runRadio    = QRadioButton(translate("insertTeeForm", "Insert on Run"))
        self.branchRadio = QRadioButton(translate("insertTeeForm", "Insert on Branch"))
        self.runRadio.setChecked(True)
        self.insertModeGroup.addButton(self.runRadio)
        self.insertModeGroup.addButton(self.branchRadio)
        self.secondCol.layout().addWidget(self.runRadio)
        self.secondCol.layout().addWidget(self.branchRadio)

        self.btn1.clicked.connect(self.insert)
        self.btn3 = QPushButton(translate("insertTeeForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.reverse)
        self.btn4 = QPushButton(translate("insertTeeForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn4)
        self.btn4.clicked.connect(self.apply)
        self.btn1.setDefault(True)
        self.btn1.setFocus()

        # Branch rotation dial
        self.screenDial = QWidget()
        self.screenDial.setLayout(QHBoxLayout())
        self.dial = QDial()
        self.dial.setWrapping(True)
        self.dial.setMaximum(180)
        self.dial.setMinimum(-180)
        self.dial.setNotchTarget(15)
        self.dial.setNotchesVisible(True)
        self.dial.setMaximumSize(70, 70)
        self.screenDial.layout().addWidget(self.dial)
        self.lab = QLabel(translate("insertTeeForm", "0 deg"))
        self.lab.setAlignment(Qt.AlignCenter)
        self.dial.valueChanged.connect(self.rotatePort)
        self.screenDial.layout().addWidget(self.lab)
        self.firstCol.layout().addWidget(self.screenDial)

        self.sizeList.currentItemChanged.connect(self.fillBranch)

        pCmd.autoSelectInPipeForm(self)

        self.show()
        self.lastTee   = None
        self.lastAngle = 0

    # ── helper: detect SW/TH rating ──────────────────────────────────────────

    def _isSocketConn(self):
        """Return True when the loaded CSV is a SW or TH (socket/threaded) table."""
        for row in self.pipeDictList:
            if row.get("Conn", "").strip().upper() in ("SW", "TH"):
                return True
        return False

    # ── fillSizes override ───────────────────────────────────────────────────

    def fillSizes(self):
        """Load Tee_<PRating>.csv and populate the run sizeList.

        BW : label = PSize  OD x thk  (deduplicated by PSize)
        SW/TH: label = PSize  OD       (no thk column; deduplicated by PSize)
        """
        self.sizeList.clear()
        self.pipeDictList = []
        fname = "Tee_" + self.PRating + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r") as fh:
                self.pipeDictList = list(csv.DictReader(fh, delimiter=";"))
        except Exception:
            return

        seen_psize = []
        for row in self.pipeDictList:
            ps = row["PSize"]
            if ps not in seen_psize:
                seen_psize.append(ps)
                if self._isSocketConn():
                    # SW/TH: no thk column
                    if qu:
                        label = qu.format_psize(ps) + "  " + qu.format_dim(row["OD"])
                    else:
                        label = ps + "  " + row.get("OD", "")
                else:
                    if qu:
                        label = qu.format_size_label(row)
                    else:
                        label = ps + "  " + row.get("OD", "") + "x" + row.get("thk", "")
                self.sizeList.addItem(label)

        if hasattr(self, "_branchList"):
            self.fillBranch()

    # ── fillBranch ───────────────────────────────────────────────────────────

    def fillBranch(self):
        """Populate _branchList from rows matching the currently selected run PSize."""
        self._branchList.clear()
        self._branchDictList = []
        if not self.pipeDictList:
            return

        seen = []
        for row in self.pipeDictList:
            if row["PSize"] not in seen:
                seen.append(row["PSize"])
        row_idx = self.sizeList.currentRow()
        if row_idx < 0:
            row_idx = 0
        if row_idx >= len(seen):
            return
        run_psize = seen[row_idx]

        for row in self.pipeDictList:
            if row["PSize"] != run_psize:
                continue
            self._branchDictList.append(row)
            branch_psize = row.get("PSizeBranch", "")
            if self._isSocketConn():
                # SW/TH: no thk2 — show PSizeBranch + OD2
                if qu:
                    label = qu.format_psize(branch_psize) + "  " + qu.format_dim(row["OD2"])
                else:
                    label = branch_psize + "  " + row.get("OD2", "")
            else:
                # BW: show PSizeBranch + OD2 x thk2
                if qu:
                    branch_row = {"PSize": branch_psize, "OD": row["OD2"], "thk": row["thk2"]}
                    label = qu.format_size_label(branch_row)
                else:
                    label = branch_psize + "  " + row["OD2"] + "x" + row["thk2"]
            self._branchList.addItem(label)

        self._branchList.setCurrentRow(0)

    # ── rating-change handler ────────────────────────────────────────────────

    def _changeRating(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # ── insert ───────────────────────────────────────────────────────────────

    def insert(self):
        self.lastAngle = 0
        self.dial.setValue(0)
        insertOnBranch = self.branchRadio.isChecked()

        branch_idx = self._branchList.currentRow()
        if branch_idx < 0 or branch_idx >= len(self._branchDictList):
            FreeCAD.Console.PrintWarning("insertTeeForm: no branch size selected\n")
            return
        d = self._branchDictList[branch_idx]

        if self._isSocketConn():
            # ── Socket / threaded tee ────────────────────────────────────
            propList = [
                d["PSize"],
                d.get("PSizeBranch", d["PSize"]),
                float(pq(d["OD"])),
                float(pq(d["OD2"])),
                float(pq(d["A"])),
                float(pq(d["C"])),
                float(pq(d["D"])),
                float(pq(d["E"])),
                float(pq(d["G"])),
                d.get("Conn", "SW"),
            ]
            rating = self.ratingList.currentItem().text()
            self.lastTee = pCmd.doSocketTee(
                rating, propList, FreeCAD.__activePypeLine__, insertOnBranch)[-1]
        else:
            # ── Butt-weld tee ────────────────────────────────────────────
            propList = [
                d["PSize"],
                float(pq(d["OD"])),
                float(pq(d["OD2"])),
                float(pq(d["thk"])),
                float(pq(d["thk2"])),
                float(pq(d["C"])),
                float(pq(d["M"])),
            ]
            rating = self.ratingList.currentItem().text()
            self.lastTee = pCmd.doTees(
                rating, propList, FreeCAD.__activePypeLine__, insertOnBranch)[-1]

        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.lastTee)

    # ── trim ─────────────────────────────────────────────────────────────────

    def trim(self):
        if len(fCmd.beams()) == 1:
            pipe = fCmd.beams()[0]
            comPipeEdges = [e.CenterOfMass for e in pipe.Shape.Edges]
            eds = [e for e in fCmd.edges() if e.CenterOfMass not in comPipeEdges]
            FreeCAD.activeDocument().openTransaction(
                translate("Transaction", "Trim pipes"))
            for edge in eds:
                fCmd.extendTheBeam(fCmd.beams()[0], edge)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
        else:
            FreeCAD.Console.PrintError(
                translate("insertTeeForm", "Wrong selection\n"))

    # ── rotatePort ───────────────────────────────────────────────────────────

    def rotatePort(self):
        if self.lastTee is None:
            return
        port = 2 if self.branchRadio.isChecked() else 0
        pCmd.rotateTheTeePort(self.lastTee, port, self.lastAngle * -1)
        self.lastAngle = self.dial.value()
        pCmd.rotateTheTeePort(self.lastTee, port, self.lastAngle)
        self.lab.setText(str(self.dial.value()) + translate("insertTeeForm", " deg"))

    # ── apply ────────────────────────────────────────────────────────────────

    def apply(self):
        branch_idx = self._branchList.currentRow()
        if branch_idx < 0 or branch_idx >= len(self._branchDictList):
            return
        d = self._branchDictList[branch_idx]

        for obj in FreeCADGui.Selection.getSelection():
            if not hasattr(obj, "PType"):
                continue
            if obj.PType == "SocketTee" and self._isSocketConn():
                obj.PSize       = d["PSize"]
                obj.PSizeBranch = d.get("PSizeBranch", d["PSize"])
                obj.OD          = pq(d["OD"])
                obj.OD2         = pq(d["OD2"])
                obj.A           = pq(d["A"])
                obj.C           = pq(d["C"])
                obj.D           = pq(d["D"])
                obj.E           = pq(d["E"])
                obj.G           = pq(d["G"])
                obj.Conn        = d.get("Conn", "SW")
                obj.PRating     = self.PRating
                FreeCAD.activeDocument().recompute()
            elif obj.PType == "Tee" and not self._isSocketConn():
                obj.PSize   = d["PSize"]
                obj.OD      = pq(d["OD"])
                obj.OD2     = pq(d["OD2"])
                obj.thk     = pq(d["thk"])
                obj.thk2    = pq(d["thk2"])
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()

    # ── reverse ──────────────────────────────────────────────────────────────

    def reverse(self):
        if self.lastTee is None:
            return
        port = 2 if self.branchRadio.isChecked() else 0
        initial_port_pos = self.lastTee.Placement.multVec(self.lastTee.Ports[port])
        crossVector1 = FreeCAD.Vector(1, 0, 0)
        crossVector2 = self.lastTee.Ports[port].normalize()
        if crossVector2 == crossVector1:
            crossVector1 = FreeCAD.Vector(0, 1, 0)
        if crossVector2 == FreeCAD.Vector(0, 0, 0):
            crossVector2 = FreeCAD.Vector(0, 1, 0)
        pCmd.rotateTheTubeAx(self.lastTee, crossVector1.cross(crossVector2), angle=180)
        final_port_pos = self.lastTee.Placement.multVec(self.lastTee.Ports[port])
        self.lastTee.Placement.move(initial_port_pos - final_port_pos)


class insertTerminalAdapterForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert adapter.
    For position and orientation you can select
      - two pipes parallel (possibly co-linear)
      - one pipe at one of its ends
      - one pipe
      - one circular edge
      - one straight edge
      - one vertex
      - nothing (created at origin)
    In case one pipe is selected, its properties are applied
    """

    def __init__(self):
        super(insertTerminalAdapterForm, self).__init__(
            translate("insertTerminalAdapter", "Insert terminal adapter"),
            "TerminalAdapter",
            "ConduitPVC0.5in-SCH-40",
            "TA.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.ratingList.itemClicked.connect(self.changeRating2)
        self.ratingList.setMaximumHeight(50)
        self.btn2 = QPushButton(translate("insertTerminalAdapterForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn3 = QPushButton(translate("insertTerminalAdapterFormForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn1.clicked.connect(self.insert)
        self.btn2.clicked.connect(self.reverse)
        self.btn3.clicked.connect(self.applyProp)
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.show()
        self.lastTA = None

    def applyProp(self):
        r = self.pipeDictList[self.sizeList.currentRow()]
        DN = r["PSize"]
        OD1 = float(pq(r["OD"]))
        idx2 = self.OD2list.currentRow()
        OD2 = float(pq(self._od2_raw[idx2])) if hasattr(self, "_od2_raw") and idx2 < len(self._od2_raw) else float(pq(self.OD2list.currentItem().text()))
        thk1 = float(pq(r["thk"]))
        try:
            thk2 = float(pq(self._thk2_raw[idx2])) if hasattr(self, "_thk2_raw") and idx2 < len(self._thk2_raw) else float(pq(r["thk2"].split(">")[idx2]))
        except:
            thk2 = thk1
        H = pq(r["H"])
        terminalAdapter = [
            red
            for red in FreeCADGui.Selection.getSelection()
            if hasattr(red, "PType") and red.PType == "TA"
        ]
        if len(terminalAdapter):
            for TA in terminalAdapter:
                TA.PSize = DN
                TA.PRating = self.PRating
                TA.OD = OD1
                TA.OD2 = OD2
                TA.thk = thk1
                TA.thk2 = thk2
                TA.Height = H
        elif self.lastTA:
            self.lastTA.PSize = DN
            self.lastTA.PRating = self.PRating
            self.lastTA.OD = OD1
            self.lastTA.OD2 = OD2
            self.lastTA.thk = thk1
            self.lastTA.thk2 = thk2
            self.lastTA.Height = H
        FreeCAD.activeDocument().recompute()

    def reverse(self):
        selRed = [
            r
            for r in FreeCADGui.Selection.getSelection()
            if hasattr(r, "PType") and r.PType == "TerminalAdapter"
        ]
        if len(selRed):
            for r in selRed:
                pCmd.rotateTheTubeAx(r, FreeCAD.Vector(1, 0, 0), 180)
        elif self.lastTA:
            pCmd.rotateTheTubeAx(self.lastTA, FreeCAD.Vector(1, 0, 0), 180)

    def insert(self):
        size = self.pipeDictList[self.sizeList.currentRow()]
        rating = self.ratingList.currentItem().text()
        # FreeCAD.Console.PrintMessage(rating)
        propList=[]
        pos = Z = None
        selex = FreeCADGui.Selection.getSelectionEx()
        pipes = [p.Object for p in selex if hasattr(p.Object, "PType") and p.Object.PType == "Pipe"]
        if len(pipes) > 0:  # if 1 pipe is selected...
            Psize_data = pipes[0].PSize
            # OD1 = float(pipes[0].OD)
            curves = [e for e in fCmd.edges() if e.curvatureAt(0) > 0]
            if len(curves):  # ...and 1 curve is selected...
                pos = curves[0].centerOfCurvatureAt(0)
            else:  # ...or no curve is selected...
                pos = pipes[0].Placement.Base
            Z = pos - pipes[0].Shape.Solids[0].CenterOfMass
            # FreeCAD.Console.PrintMessage(Psize_data)
            # FreeCAD.Console.PrintMessage(self.sizeList.findItems(Psize_data,Qt.MatchExactly))
            for sub in self.pipeDictList:
                if sub["PSize"] == Psize_data:
                    size2 = sub
                    propList = [
                        Psize_data,
                        float(pq(size2["OD"])),
                        float(pq(size2["L"])),
                        float(pq(size2["SW"])),
                        float(pq(size2["OD2"])),
                    ]
        else:  # if no pipe is selected...
            if not propList:
                propList = [
                    size["PSize"],
                    float(pq(size["OD"])),
                    float(pq(size["L"])),
                    float(pq(size["SW"])),
                    float(pq(size["OD2"])),
                ]
                # FreeCAD.Console.PrintMessage(propList)
            if fCmd.edges():  # ...but 1 curve is selected...
                edge = fCmd.edges()[0]
                if edge.curvatureAt(0) > 0:
                    pos = edge.centerOfCurvatureAt(0)
                    Z = edge.tangentAt(0).cross(edge.normalAt(0))
                else:
                    pos = edge.valueAt(0)
                    Z = edge.tangentAt(0)
            elif selex and selex[0].SubObjects[0].ShapeType == "Vertex":  # ...or 1 vertex..
                pos = selex[0].SubObjects[0].Point
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert terminal adapter"))
        self.lastTA = pCmd.makeTerminalAdapter(rating,propList, pos, Z)
        FreeCAD.activeDocument().commitTransaction()
        FreeCAD.activeDocument().recompute()
        if self.combo.currentText() != "<none>":
            pCmd.moveToPyLi(self.lastTA, self.combo.currentText())

    def changeRating2(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)


class insertFlangeForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert flanges.
    For position and orientation you can select
      - one or more circular edges,
      - one or more vertexes,
      - nothing.
    In case one pipe is selected, its properties are applied to the flange.
    Available one button to reverse the orientation of the last or selected
    flanges.
    """

    def __init__(self):
        super(insertFlangeForm, self).__init__(
            translate("insertFlangeForm", "Insert flanges"),
            "Flange",
            "DIN-PN16",
            "flange.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.btn1.clicked.connect(self.insert)
        self.insertModeGroup = QButtonGroup()  
        self.weldEndRadio = QRadioButton(translate("insertFlangeForm", "Connect on Weld End"))
        self.faceEndRadio = QRadioButton(translate("insertFlangeForm", "Connect on Flange Face"))
        self.weldEndRadio.setChecked(True)  # Default: weld end connects to pipe
        self.insertModeGroup.addButton(self.weldEndRadio)
        self.insertModeGroup.addButton(self.faceEndRadio)
        self.secondCol.layout().addWidget(self.weldEndRadio)
        self.secondCol.layout().addWidget(self.faceEndRadio)


        self.btn2 = QPushButton(translate("insertFlangeForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.reverse)  # lambda: pCmd.rotateTheTubeAx(self.lastFlange,FreeCAD.Vector(1,0,0),180))
        self.btn3 = QPushButton(translate("insertFlangeForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn4 = QCheckBox(translate("insertFlangeForm", "Remove pipe equivalent length"))
        self.secondCol.layout().addWidget(self.btn4)
        self.btn3.clicked.connect(self.apply)
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.show()
        self.lastFlange = None
        self.offsetoption=False

    def reverse(self):
        port = 0 if self.faceEndRadio.isChecked() else 1  
        """
        selFlanges = [
            f
            for f in FreeCADGui.Selection.getSelection()
            if hasattr(f, "PType") and f.PType == "Flange"
        ]
        if len(selFlanges):
            for f in selFlanges:
                pCmd.rotateTheTubeAx(f, FreeCAD.Vector(1, 0, 0), 180)
        else:
            pCmd.rotateTheTubeAx(self.lastFlange, FreeCAD.Vector(1, 0, 0), 180)
        """
        initial_port_pos = self.lastFlange.Placement.multVec(self.lastFlange.Ports[port])
        crossVector1 = FreeCAD.Vector(1,0,0)
        crossVector2 = self.lastFlange.Ports[port].normalize()
        #if the port is at Vector(0,0,0) or Vector(1,0,0), it will cause problems, so catch those and assign different rotation axes.
        if crossVector2 == crossVector1:
            crossVector1 = FreeCAD.Vector(0,1,0)
        if crossVector2 == FreeCAD.Vector(0,0,0):
            crossVector2 = FreeCAD.Vector(0,1,0)
        pCmd.rotateTheTubeAx(self.lastFlange,crossVector1.cross(crossVector2), angle=180)
        final_port_pos = self.lastFlange.Placement.multVec(self.lastFlange.Ports[port])
        
        #recalculate the distance between the two and move object again
        dist = initial_port_pos - final_port_pos
        self.lastFlange.Placement.move(dist)

    def insert(self):
        self.offsetoption=self.btn4.isChecked()
        attachFace = self.faceEndRadio.isChecked()
        """Do not override selected flange size
        tubes = [t for t in fCmd.beams() if hasattr(t, "PSize")]
        if len(tubes) > 0 and tubes[0].PSize in [prop["PSize"] for prop in self.pipeDictList]:
            for prop in self.pipeDictList:
                if prop["PSize"] == tubes[0].PSize:
                    d = prop
                    break
        else:
        """
        d = self.pipeDictList[self.sizeList.currentRow()]
        propList = [
            d["PSize"],
            d["FlangeType"],
            float(pq(d["D"])),
            float(pq(d.get("d", "0"))),      # blind flanges have no bore
            float(pq(d["df"])),
            float(pq(d["f"])),
            float(pq(d["t"])),
            int(d["n"]),
        ]
        try:  # for raised-face
            propList.append(float(d["trf"]))
            propList.append(float(d["drf"]))
        except:
            for x in range(0, 2, 1):
                propList.append(0)
        try:  # for welding-neck
            propList.append(float(d["twn"]))
            propList.append(float(d["dwn"]))
        except:
            for x in range(0, 2, 1):
                propList.append(0)
        try:  # for welding-neck
            propList.append(float(d["ODp"]))
        except:
            propList.append(0)
        try:  # for welding-neck
            propList.append(float(d["R"]))
        except:
            propList.append(0)
        try:
            propList.append(float(d["T1"]))
        except:
            propList.append(0)
        try:
            propList.append(float(d["B2"]))
        except:
            propList.append(0)
        try:
            propList.append(float(d["Y"]))
        except:
            propList.append(0)
        #FreeCAD.Console.PrintMessage(self.offsetoption)
        rating = self.ratingList.currentItem().text()
        self.lastFlange = self.lastFlange = pCmd.doFlanges(
            rating,
            propList,
            pypeline=FreeCAD.__activePypeLine__,
            doOffset=self.offsetoption,
            attachFace=attachFace,
        )[-1]
        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.lastFlange)
        
    def apply(self):
        for obj in FreeCADGui.Selection.getSelection():
            d = self.pipeDictList[self.sizeList.currentRow()]
            if hasattr(obj, "PType") and obj.PType == self.PType:
                obj.PSize = d["PSize"]
                obj.FlangeType = d["FlangeType"]
                obj.D = float(pq(d["D"]))
                obj.d = float(pq(d.get("d", "0")))      # blind flanges have no bore
                obj.df = float(pq(d["df"]))
                obj.f = float(pq(d["f"]))
                obj.t = float(pq(d["t"]))
                obj.n = int(pq(d["n"]))
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()



class insertReductForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert concentric reductions.
    For position and orientation you can select
      - two pipes parallel (possibly co-linear)
      - one pipe at one of its ends
      - one pipe
      - one circular edge
      - one straight edge
      - one vertex
      - nothing (created at origin)
    In case one pipe is selected, its properties are applied to the reduction.
    Available one button to reverse the orientation of the last or selected
    reductions.
    """

    def __init__(self):
        super(insertReductForm, self).__init__(
            translate("insertReductForm", "Insert reductions"),
            "Reduct",
            "SCH-STD",
            "reduct.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.ratingList.itemClicked.connect(self.changeRating2)
        self.sizeList.currentItemChanged.connect(self.fillOD2)
        self.ratingList.setCurrentRow(0)
        self.ratingList.setMaximumHeight(50)
        self.OD2list = QListWidget()
        self.OD2list.setMaximumHeight(80)
        self.secondCol.layout().addWidget(self.OD2list)
        # Add radio buttons for insert mode selection
        self.insertModeGroup = QButtonGroup()
        self.largerEndRadio = QRadioButton(translate("insertReductForm", "Insert on Larger End"))
        self.smallerEndRadio = QRadioButton(translate("insertReductForm", "Insert on Smaller End"))
        self.largerEndRadio.setChecked(True)  # Default to larger end
        self.insertModeGroup.addButton(self.largerEndRadio)
        self.insertModeGroup.addButton(self.smallerEndRadio)
        self.secondCol.layout().addWidget(self.largerEndRadio)
        self.secondCol.layout().addWidget(self.smallerEndRadio)

        self.btn2 = QPushButton(translate("insertReductForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn3 = QPushButton(translate("insertReductForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn1.clicked.connect(self.insert)
        self.btn2.clicked.connect(self.reverse)
        self.btn3.clicked.connect(self.applyProp)
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.cb1 = QCheckBox(translate("insertReductForm", "Eccentric"))
        self.secondCol.layout().addWidget(self.cb1)
        self.fillOD2()

        # Rotation dial – shown only for eccentric reducers (in firstCol)
        self.screenDial = QWidget()
        self.screenDial.setLayout(QHBoxLayout())
        self.dial = QDial()
        self.dial.setWrapping(True)
        self.dial.setMaximum(180)
        self.dial.setMinimum(-180)
        self.dial.setNotchTarget(15)
        self.dial.setNotchesVisible(True)
        self.dial.setMaximumSize(70, 70)
        self.screenDial.layout().addWidget(self.dial)
        self.dialLab = QLabel(translate("insertReductForm", "0 deg"))
        self.dialLab.setAlignment(Qt.AlignCenter)
        self.dial.valueChanged.connect(self.rotateEccentric)
        self.screenDial.layout().addWidget(self.dialLab)
        self.firstCol.layout().addWidget(self.screenDial)
        self.screenDial.hide()   # only visible when Eccentric is checked
        self.lastAngle = 0

        self.cb1.toggled.connect(self._onEccentricToggled)

        #auto-select pipe size and rating if available
        pCmd.autoSelectInPipeForm(self)

        self.show()
        self.lastReduct = None

    def _insertPort(self):
        """Return the port index matching the active insert-end radio."""
        return 1 if self.smallerEndRadio.isChecked() else 0

    def _rotateAboutPort(self, obj, port_idx, angle_deg):
        """
        Rotate obj by angle_deg degrees about the axis passing through
        Ports[port_idx] in world space.

        rotateTheTubeAx always pivots about the placement Base (the world
        position of Ports[0]).  For Port 0 that is correct.  For Port 1 of
        an eccentric reducer the pivot point is offset, so we must:
          1. Map the port location into world space.
          2. Build the rotation about the object's insertion axis (world Z
             as seen through the placement rotation).
          3. Rotate both the Base and the Rotation of the Placement so the
             chosen port stays pinned in world space.
        """
        # Axis direction: world-space Z of the object (same for both ports)
        ax = obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1)).normalize()
        rot = FreeCAD.Rotation(ax, angle_deg)

        if port_idx == 0:
            # Port 0 is at the placement Base — standard rotation, no
            # translation needed.
            obj.Placement.Rotation = rot.multiply(obj.Placement.Rotation)
        else:
            # Port 1 is offset from the Base.  Pin it in world space.
            pivot = obj.Placement.multVec(obj.Ports[port_idx])
            old_base = obj.Placement.Base
            new_base = pivot + rot.multVec(old_base - pivot)
            obj.Placement.Base     = new_base
            obj.Placement.Rotation = rot.multiply(obj.Placement.Rotation)

    def _onEccentricToggled(self, checked):
        """Show/hide the rotation dial when Eccentric checkbox changes."""
        if checked:
            self.screenDial.show()
        else:
            self.screenDial.hide()
            # Reset dial and undo any accumulated rotation on the last reducer
            if self.lastAngle != 0 and self.lastReduct:
                self._rotateAboutPort(
                    self.lastReduct, self._insertPort(), -self.lastAngle)
                FreeCAD.activeDocument().recompute()
            self.lastAngle = 0
            self.dial.setValue(0)

    def rotateEccentric(self):
        """Rotate the last eccentric reducer around its insertion-port axis."""
        if not self.lastReduct:
            self.lastAngle = self.dial.value()
            return
        delta = self.dial.value() - self.lastAngle
        self.lastAngle = self.dial.value()
        self._rotateAboutPort(self.lastReduct, self._insertPort(), delta)
        self.dialLab.setText(
            str(self.dial.value()) + translate("insertReductForm", " deg"))
        FreeCAD.activeDocument().recompute()


    def applyProp(self):
        r = self.pipeDictList[self.sizeList.currentRow()]
        DN = r["PSize"]
        OD1 = float(pq(r["OD"]))
        OD2 = float(pq(self.OD2list.currentItem().text()))
        thk1 = float(pq(r["thk"]))
        try:
            thk2 = float(pq(r["thk2"].split(">")[self.OD2list.currentRow()]))
        except:
            thk2 = thk1
        H = pq(r["H"])
        reductions = [
            red
            for red in FreeCADGui.Selection.getSelection()
            if hasattr(red, "PType") and red.PType == "Reduct"
        ]
        if len(reductions):
            for reduct in reductions:
                reduct.PSize = DN
                reduct.PRating = self.PRating
                reduct.OD = OD1
                reduct.OD2 = OD2
                reduct.thk = thk1
                reduct.thk2 = thk2
                reduct.Height = H
        elif self.lastReduct:
            self.lastReduct.PSize = DN
            self.lastReduct.PRating = self.PRating
            self.lastReduct.OD = OD1
            self.lastReduct.OD2 = OD2
            self.lastReduct.thk = thk1
            self.lastReduct.thk2 = thk2
            self.lastReduct.Height = H
        FreeCAD.activeDocument().recompute()

    def fillOD2(self):
        self.OD2list.clear()
        # Keep parallel raw-value lists so insert/applyProp read by index
        self._od2_raw  = []
        self._thk2_raw = []
        if not self.pipeDictList:
            return
        row_idx = self.sizeList.currentRow()
        if row_idx < 0:
            row_idx = 0
        r = self.pipeDictList[row_idx]
        od2_vals  = r["OD2"].split(">")
        thk2_vals = r.get("thk2", "").split(">")
        for i, od2 in enumerate(od2_vals):
            thk2 = thk2_vals[i] if i < len(thk2_vals) else ""
            self._od2_raw.append(od2.strip())
            self._thk2_raw.append(thk2.strip())
            if qu:
                label = qu.format_secondary_label(
                    od2.strip(), thk2.strip(), self.pipeDictList)
            else:
                label = od2.strip() + ("x" + thk2.strip() if thk2.strip() else "")
            self.OD2list.addItem(label)
        self.OD2list.setCurrentRow(0)

    def reverse(self):
        """
        selRed = [
            r
            for r in FreeCADGui.Selection.getSelection()
            if hasattr(r, "PType") and r.PType == "Reduct"
        ]
        if len(selRed):
            for r in selRed:
                pCmd.rotateTheTubeAx(r, FreeCAD.Vector(1, 0, 0), 180)
        elif self.lastReduct:
            pCmd.rotateTheTubeAx(self.lastReduct, FreeCAD.Vector(1, 0, 0), 180)
        """
        
        if self.smallerEndRadio.isChecked(): #if inserted on smaller end, port = 1, if inserted on larger end, port = 0
            port = 1
        else:
            port = 0

        initial_port_pos = self.lastReduct.Placement.multVec(self.lastReduct.Ports[port])
        crossVector1 = FreeCAD.Vector(0,0,1)
        crossVector2 = self.lastReduct.Ports[port]
        #if the port is at Vector(0,0,0) or Vector(1,0,0), it will cause problems, so catch those and assign different rotation axes.
        if crossVector2 == FreeCAD.Vector(0,0,0):
            crossVector2 = FreeCAD.Vector(0,1,0)
        crossVector2.normalize()
        if crossVector2 == crossVector1:
            crossVector1 = FreeCAD.Vector(0,1,0)
        
        pCmd.rotateTheTubeAx(self.lastReduct,crossVector1.cross(crossVector2), angle=180)
        final_port_pos = self.lastReduct.Placement.multVec(self.lastReduct.Ports[port])
        
        #recalculate the distance between the two and move object again
        dist = initial_port_pos - final_port_pos
        self.lastReduct.Placement.move(dist)
        

    def insert(self):
        r = self.pipeDictList[self.sizeList.currentRow()]
        pos = Z = H = None
        selex = FreeCADGui.Selection.getSelectionEx()
        pipes = [p.Object for p in selex if hasattr(p.Object, "PType") and p.Object.PType == "Pipe"]
        DN = r["PSize"]
        OD1 = float(pq(r["OD"]))
        idx2 = self.OD2list.currentRow()
        OD2 = float(pq(self._od2_raw[idx2])) if hasattr(self, "_od2_raw") and idx2 < len(self._od2_raw) else float(pq(self.OD2list.currentItem().text()))
        thk1 = float(pq(r["thk"]))
        try:
            thk2 = float(pq(self._thk2_raw[idx2])) if hasattr(self, "_thk2_raw") and idx2 < len(self._thk2_raw) else float(pq(r["thk2"].split(">")[idx2]))
        except:
            thk2 = thk1
        H = pq(r["H"])
        if not H:  # calculate length if it's not defined
            H = float(3 * (OD1 - OD2))
        # Determine if we should insert on smaller end (requires reversing)
        insertOnSmallerEnd = self.smallerEndRadio.isChecked()


        
        propList = [DN, OD1, OD2, thk1, thk2, H]
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert reduction"))

        rating = self.ratingList.currentItem().text()
        if self.cb1.isChecked():
            self.lastReduct = pCmd.doReduct(rating, propList, FreeCAD.__activePypeLine__, pos, Z, False, insertOnSmallerEnd)[-1]
        else:
            self.lastReduct = pCmd.doReduct(rating, propList, FreeCAD.__activePypeLine__, pos, Z, True, insertOnSmallerEnd)[-1]

        
        FreeCAD.activeDocument().commitTransaction()
        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.lastReduct)
        if self.combo.currentText() != "<none>":
            pCmd.moveToPyLi(self.lastReduct, self.combo.currentText())
        # Reset dial so the next insert starts from 0
        self.lastAngle = 0
        self.dial.setValue(0)

    def fillSizes(self):
        """Override to also refresh the OD2 list when DN/NPS is toggled."""
        super(insertReductForm, self).fillSizes()
        if hasattr(self, "OD2list"):
            self.fillOD2()

    def changeRating2(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

class insertUboltForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert U-bolts.
    For position and orientation you can select
      - one or more circular edges,
      - nothing.
    In case one pipe is selected, its properties are applied to the U-bolt.
    Available one button to reverse the orientation of the last or selected tubes.
    """

    def __init__(self):
        super(insertUboltForm, self).__init__(
            translate("insertUboltForm", "Insert U-bolt"),
            "Clamp",
            "DIN-UBolt",
            "clamp.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.lab1 = QLabel(translate("insertUboltForm", "- no ref. face -"))
        self.lab1.setAlignment(Qt.AlignHCenter)
        self.firstCol.layout().addWidget(self.lab1)
        self.btn1.clicked.connect(self.insert)
        self.btn2 = QPushButton(translate("insertUboltForm", "Ref. face"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.getReference)
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.cb1 = QCheckBox(translate("insertUboltForm", " Head"))
        self.cb1.setChecked(True)
        self.cb2 = QCheckBox(translate("insertUboltForm", " Middle"))
        self.cb3 = QCheckBox(translate("insertUboltForm", " Tail"))
        self.checkb = QWidget()
        self.checkb.setLayout(QFormLayout())
        self.checkb.layout().setAlignment(Qt.AlignHCenter)
        self.checkb.layout().addRow(self.cb1)
        self.checkb.layout().addRow(self.cb2)
        self.checkb.layout().addRow(self.cb3)
        self.secondCol.layout().addWidget(self.checkb)
        self.show()
        self.refNorm = None
        self.getReference()

    def getReference(self):
        selex = FreeCADGui.Selection.getSelectionEx()
        for sx in selex:
            if sx.SubObjects:
                planes = [f for f in fCmd.faces([sx]) if type(f.Surface) == Part.Plane]
                if len(planes) > 0:
                    self.refNorm = rounded(planes[0].normalAt(0, 0))
                    self.lab1.setText("ref. Face on " + sx.Object.Label)

    def insert(self):
        selex = FreeCADGui.Selection.getSelectionEx()
        if len(selex) == 0:
            d = self.pipeDictList[self.sizeList.currentRow()]
            propList = [
                d["PSize"],
                self.PRating,
                float(pq(d["C"])),
                float(pq(d["H"])),
                float(pq(d["d"])),
            ]
            FreeCAD.activeDocument().openTransaction(
                translate("Transaction", "Insert clamp in (0,0,0)")
            )
            ub = pCmd.makeUbolt(propList)
            if self.combo.currentText() != "<none>":
                pCmd.moveToPyLi(ub, self.combo.currentText())
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
        else:
            FreeCAD.activeDocument().openTransaction(
                translate("Transaction", "Insert clamp on tube")
            )
            for objex in selex:
                if hasattr(objex.Object, "PType") and objex.Object.PType == "Pipe":
                    d = [typ for typ in self.pipeDictList if typ["PSize"] == objex.Object.PSize]
                    if len(d) > 0:
                        d = d[0]
                    else:
                        d = self.pipeDictList[self.sizeList.currentRow()]
                    propList = [
                        d["PSize"],
                        self.PRating,
                        float(pq(d["C"])),
                        float(pq(d["H"])),
                        float(pq(d["d"])),
                    ]
                    H = float(objex.Object.Height)
                    gap = H - float(pq(d["C"]))
                    steps = [
                        gap * self.cb1.isChecked(),
                        H / 2 * self.cb2.isChecked(),
                        (H - gap) * self.cb3.isChecked(),
                    ]
                    for s in steps:
                        if s:
                            ub = pCmd.makeUbolt(
                                propList,
                                pos=objex.Object.Placement.Base,
                                Z=fCmd.beamAx(objex.Object),
                            )
                            ub.Placement.move(fCmd.beamAx(objex.Object).multiply(s))
                            if self.refNorm:
                                pCmd.rotateTheTubeAx(
                                    obj=ub,
                                    angle=degrees(
                                        self.refNorm.getAngle(
                                            (fCmd.beamAx(ub, FreeCAD.Vector(0, 1, 0)))
                                        )
                                    ),
                                )
                            if self.combo.currentText() != "<none>":
                                pCmd.moveToPyLi(ub, self.combo.currentText())
            FreeCAD.activeDocument().commitTransaction()
        FreeCAD.activeDocument().recompute()


class insertCapForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert a pipe cap (butt-weld) or socket/threaded cap.

    Butt-weld ratings (CSV has no "Conn" column):
      - sizeList shows PSize + OD x thk
      - Insert calls pCmd.doCaps; Apply updates BW Cap properties.

    Socket-weld / threaded ratings (CSV has Conn == "SW" or "TH"):
      - sizeList shows PSize + OD  (no thk column in SW CSV)
      - Insert calls pCmd.doSocketCap; Apply updates SW/TH SocketCap properties.
    """

    def __init__(self):
        super(insertCapForm, self).__init__(
            translate("insertCapForm", "Insert caps"), "Cap", "SCH-STD", "cap.svg", x, y
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)

        # Disconnect base changeRating and reconnect so layout refreshes on
        # rating-type switch (BW ↔ SW/TH).
        try:
            self.ratingList.itemClicked.disconnect(self.changeRating)
        except Exception:
            pass
        self.ratingList.itemClicked.connect(self._changeRating)

        self.btn1.clicked.connect(self.insert)
        self.btn2 = QPushButton(translate("insertCapForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.reverse)
        self.btn3 = QPushButton(translate("insertCapForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.apply)
        self.btn1.setDefault(True)
        self.btn1.setFocus()

        pCmd.autoSelectInPipeForm(self)

        self.show()
        self.lastCap = None

    # ── helper: detect SW/TH rating ──────────────────────────────────────────

    def _isSocketConn(self):
        """Return True when the loaded CSV is a SW or TH (socket/threaded) table."""
        for row in self.pipeDictList:
            if row.get("Conn", "").strip().upper() in ("SW", "TH"):
                return True
        return False

    # ── fillSizes override ───────────────────────────────────────────────────

    def fillSizes(self):
        """Load Cap_<PRating>.csv and populate sizeList.

        BW  : label = PSize  OD x thk
        SW/TH: label = PSize  OD   (no thk column)
        """
        self.sizeList.clear()
        self.pipeDictList = []
        fname = "Cap_" + self.PRating + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r") as fh:
                self.pipeDictList = list(csv.DictReader(fh, delimiter=";"))
        except Exception:
            return

        for row in self.pipeDictList:
            if self._isSocketConn():
                # SW/TH: no thk column
                if qu:
                    label = qu.format_psize(row["PSize"]) + "  " + qu.format_dim(row["OD"])
                else:
                    label = row["PSize"] + "  " + row.get("OD", "")
            else:
                # BW: standard PSize + OD x thk
                if qu:
                    label = qu.format_size_label(row)
                else:
                    label = row["PSize"] + "  " + row.get("OD", "") + "x" + row.get("thk", "")
            self.sizeList.addItem(label)

    # ── rating-change handler ────────────────────────────────────────────────

    def _changeRating(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # ── insert ───────────────────────────────────────────────────────────────

    def insert(self):
        d = self.pipeDictList[self.sizeList.currentRow()]

        if self._isSocketConn():
            # ── Socket / threaded cap ────────────────────────────────────
            propList = [
                d["PSize"],
                float(pq(d["OD"])),
                float(pq(d["A"])),
                float(pq(d["C"])),
                float(pq(d["E"])),
                d.get("Conn", "SW"),
            ]
            self.lastCap = pCmd.doSocketCap(propList, FreeCAD.__activePypeLine__)[-1]
        else:
            # ── Butt-weld cap ────────────────────────────────────────────
            propList = [d["PSize"], float(pq(d["OD"])), float(pq(d["thk"]))]
            rating = self.ratingList.currentItem().text()
            self.lastCap = pCmd.doCaps(rating, propList, FreeCAD.__activePypeLine__)[-1]

        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.lastCap)

    # ── reverse ──────────────────────────────────────────────────────────────

    def reverse(self):
        """Flip selected caps (or the last inserted cap) 180° around X."""
        selCaps = [
            p for p in FreeCADGui.Selection.getSelection()
            if hasattr(p, "PType") and p.PType in ("Cap", "SocketCap")
        ]
        if selCaps:
            for p in selCaps:
                pCmd.rotateTheTubeAx(p, FreeCAD.Vector(1, 0, 0), 180)
        elif self.lastCap:
            pCmd.rotateTheTubeAx(self.lastCap, FreeCAD.Vector(1, 0, 0), 180)

    # ── apply ────────────────────────────────────────────────────────────────

    def apply(self):
        """Push current size/rating onto all selected cap objects."""
        d = self.pipeDictList[self.sizeList.currentRow()]

        for obj in FreeCADGui.Selection.getSelection():
            if not hasattr(obj, "PType"):
                continue

            # ── Socket / threaded cap ────────────────────────────────────
            if obj.PType == "SocketCap" and self._isSocketConn():
                obj.PSize   = d["PSize"]
                obj.OD      = pq(d["OD"])
                obj.A       = pq(d["A"])
                obj.C       = pq(d["C"])
                obj.E       = pq(d["E"])
                obj.Conn    = d.get("Conn", "SW")
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()

            # ── Butt-weld cap ────────────────────────────────────────────
            elif obj.PType == "Cap" and not self._isSocketConn():
                obj.PSize   = d["PSize"]
                obj.OD      = pq(d["OD"])
                obj.thk     = pq(d["thk"])
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()


class insertPypeLineForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert pypelines.
    Note: Elbow created within this dialog have a standard bending radius of
    3/4 x OD, corresponding to a 3D curve. If you aim to have 5D curve or any
    other custom bending radius, you shall apply it in the "Insert Elbow"
    dialog or change it manually.
    """

    def __init__(self):
        super(insertPypeLineForm, self).__init__(
            translate("insertPypeLineForm", "PypeLine Manager"),
            "Pipe",
            "SCH-STD",
            "pypeline.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.btn1.clicked.connect(self.insert)
        self.combo.activated.connect(self.summary)
        self.edit1 = QLineEdit()
        self.edit1.setPlaceholderText(translate("insertPypeLineForm", "<name>"))
        self.edit1.setAlignment(Qt.AlignHCenter)
        self.secondCol.layout().addWidget(self.edit1)
        self.btn4 = QPushButton(translate("insertPypeLineForm", "Redraw"))
        self.secondCol.layout().addWidget(self.btn4)
        self.btn4.clicked.connect(self.redraw)
        self.btn2 = QPushButton(translate("insertPypeLineForm", "Part list"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.partList)
        self.btn3 = QPushButton(translate("insertPypeLineForm", "Color"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.changeColor)
        self.btn5 = QPushButton(translate("insertPypeLineForm", "Get Path"))
        self.firstCol.layout().addWidget(self.btn5)
        self.btn5.clicked.connect(self.getBase)
        self.btnX = QPushButton(translate("insertPypeLineForm", "Get Profile"))
        self.firstCol.layout().addWidget(self.btnX)
        self.btnX.clicked.connect(self.apply)
        self.color = 0.8, 0.8, 0.8
        self.combo.setItemText(0, translate("insertPypeLineForm", "<new>"))
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.lastPypeLine = None

        #auto-select pipe size and rating if available
        pCmd.autoSelectInPipeForm(self)

        self.show()

    def summary(self, pl=None):
        if self.combo.currentText() != translate("insertPypeLineForm", "<new>"):
            pl = FreeCAD.ActiveDocument.getObjectsByLabel(self.combo.currentText())[0]
            FreeCAD.Console.PrintMessage(
                "\n%s: %s - %s\nProfile: %.1fx%.1f\nRGB color: %.3f, %.3f, %.3f\n"
                % (
                    pl.Label,
                    pl.PSize,
                    pl.PRating,
                    pl.OD,
                    pl.thk,
                    pl.ViewObject.ShapeColor[0],
                    pl.ViewObject.ShapeColor[1],
                    pl.ViewObject.ShapeColor[2],
                )
            )
            if pl.Base:
                FreeCAD.Console.PrintMessage("Path: %s\n" % pl.Base.Label)
            else:
                FreeCAD.Console.PrintMessage("Path not defined\n")

    def apply(self):
        d = self.pipeDictList[self.sizeList.currentRow()]
        if self.combo.currentText() != translate("insertPypeLineForm", "<new>"):
            pl = FreeCAD.ActiveDocument.getObjectsByLabel(self.combo.currentText())[0]
            pl.PSize = d["PSize"]
            pl.PRating = self.PRating
            pl.OD = float(d["OD"])
            pl.thk = float(d["thk"])
            self.summary()
        else:
            FreeCAD.Console.PrintError("Select a PypeLine to apply first\n")

    def insert(self):
        d = self.pipeDictList[self.sizeList.currentRow()]
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert pipe line"))
        if self.combo.currentText() == translate("insertPypeLineForm", "<new>"):
            plLabel = self.edit1.text()
            if not plLabel:
                plLabel = "Tubatura"
            a = pCmd.makePypeLine2(
                DN=d["PSize"],
                PRating=self.PRating,
                OD=float(d["OD"]),
                thk=float(d["thk"]),
                lab=plLabel,
                color=self.color,
            )
            self.combo.addItem(a.Label)
        else:
            plname = self.combo.currentText()
            plcolor = FreeCAD.activeDocument().getObjectsByLabel(plname)[0].ViewObject.ShapeColor
            pCmd.makePypeLine2(
                DN=d["PSize"],
                PRating=self.PRating,
                OD=float(d["OD"]),
                thk=float(d["thk"]),
                pl=plname,
                color=plcolor,
            )
        FreeCAD.activeDocument().commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.ActiveDocument.recompute()

    def getBase(self):
        if self.combo.currentText() != translate("insertPypeLineForm", "<new>"):
            pl = FreeCAD.ActiveDocument.getObjectsByLabel(self.combo.currentText())[0]
            sel = FreeCADGui.Selection.getSelection()
            if sel:
                base = sel[0]
                isWire = hasattr(base, "Shape") and base.Shape.Edges  # type(base.Shape)==Part.Wire
                isSketch = hasattr(base, "TypeId") and base.TypeId == "Sketcher::SketchObject"
                if isWire or isSketch:
                    FreeCAD.activeDocument().openTransaction(
                        translate("Transaction", "Assign Base")
                    )
                    pl.Base = base
                    if isWire:
                        pCmd.drawAsCenterLine(pl.Base)
                        pCmd.moveToPyLi(pl.Base, self.combo.currentText())
                    FreeCAD.activeDocument().commitTransaction()
                else:
                    FreeCAD.Console.PrintError("Not valid Base: select a Wire or a Sketch.\n")
            else:
                pl.Base = None
                FreeCAD.Console.PrintWarning(pl.Label + "-> deleted Base\n")
        else:
            FreeCAD.Console.PrintError("Please choose or create a PypeLine first\n")

    def redraw(self):
        self.rd = redrawDialog()

    def changeColor(self):
        self.hide()
        col = QColorDialog.getColor()
        if col.isValid():
            self.color = tuple([c / 255.0 for c in col.toTuple()[:3]])
            if self.combo.currentText() != translate("insertPypeLineForm", "<new>"):
                pl = FreeCAD.ActiveDocument.getObjectsByLabel(self.combo.currentText())[0]
                pl.ViewObject.ShapeColor = self.color
                pCmd.updatePLColor([pl])
        self.show()

    def partList(self):
        from PySide.QtGui import QFileDialog as qfd

        f = None
        f = qfd.getSaveFileName()[0]
        if f:
            if self.combo.currentText() != translate("insertPypeLineForm", "<new>"):
                group = FreeCAD.activeDocument().getObjectsByLabel(
                    FreeCAD.__activePypeLine__ + "_pieces"
                )[0]
                fields = ["Label", "PType", "PSize", "Volume", "Height"]
                rows = list()
                for o in group.OutList:
                    if hasattr(o, "PType"):
                        if o.PType in [
                            "Pipe",
                            "Elbow",
                            "Flange",
                            "Clamp",
                            "Reduct",
                            "Cap",
                            "Tee",
                        ]:
                            data = [o.Label, o.PType, o.PSize, o.Shape.Volume, "-"]
                            if o.PType == "Pipe":
                                data[4] = o.Height
                            rows.append(dict(zip(fields, data)))
                        elif o.PType in ["PypeBranch"]:
                            for name in o.Tubes + o.Curves:
                                pype = FreeCAD.ActiveDocument.getObject(name)
                                data = [
                                    pype.Label,
                                    pype.PType,
                                    pype.PSize,
                                    pype.Shape.Volume,
                                    "-",
                                ]
                                if pype.PType == "Pipe":
                                    data[4] = pype.Height
                                rows.append(dict(zip(fields, data)))
                plist = open(abspath(f), "w")
                w = csv.DictWriter(plist, fields, restval="-", delimiter=";")
                w.writeheader()
                w.writerows(rows)
                plist.close()
                FreeCAD.Console.PrintMessage("Data saved in %s.\n" % f)


class insertBranchForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert branches.
    Note: Elbow created within this dialog have a standard bending radius of
    3/4 x OD, corresponding to a 3D curve.
    """

    def __init__(self):
        super(insertBranchForm, self).__init__(
            translate("insertBranchForm", "Insert a branch"),
            "Pipe",
            "SCH-STD",
            "branch.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.btn1.clicked.connect(self.insert)
        self.combo.activated.connect(self.summary)
        self.edit1 = QLineEdit()
        self.edit1.setPlaceholderText(translate("insertBranchForm", "<name>"))
        self.edit1.setAlignment(Qt.AlignHCenter)
        self.secondCol.layout().addWidget(self.edit1)
        self.edit2 = QLineEdit()
        self.edit2.setPlaceholderText(translate("insertBranchForm", "<bend radius>"))
        self.edit2.setAlignment(Qt.AlignHCenter)
        self.edit2.setValidator(QDoubleValidator())
        self.secondCol.layout().addWidget(self.edit2)
        self.color = 0.8, 0.8, 0.8
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.show()

    def summary(self, pl=None):
        if self.combo.currentIndex() != 0:
            pl = FreeCAD.ActiveDocument.getObjectsByLabel(self.combo.currentText())[0]
            FreeCAD.Console.PrintMessage(
                "\n%s: %s - %s\nProfile: %.1fx%.1f\nRGB color: %.3f, %.3f, %.3f\n"
                % (
                    pl.Label,
                    pl.PSize,
                    pl.PRating,
                    pl.OD,
                    pl.thk,
                    pl.ViewObject.ShapeColor[0],
                    pl.ViewObject.ShapeColor[1],
                    pl.ViewObject.ShapeColor[2],
                )
            )
            if pl.Base:
                FreeCAD.Console.PrintMessage("Path: %s\n" % pl.Base.Label)
            else:
                FreeCAD.Console.PrintMessage("Path not defined\n")

    # def apply(self):
    # d=self.pipeDictList[self.sizeList.currentRow()]
    # if self.combo.currentText()!="<new>":
    # pl=FreeCAD.ActiveDocument.getObjectsByLabel(self.combo.currentText())[0]
    # pl.PSize=d["PSize"]
    # pl.PRating=self.PRating
    # pl.OD=float(d["OD"])
    # pl.thk=float(d["thk"])
    # self.summary()
    # else:
    # FreeCAD.Console.PrintError('Select a PypeLine to apply first\n')
    def insert(self):
        d = self.pipeDictList[self.sizeList.currentRow()]
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert pipe branch"))
        plLabel = self.edit1.text()
        if not plLabel:
            plLabel = "Traccia"
        if not self.edit2.text():
            bendRad = 0.75 * float(d["OD"])
        else:
            bendRad = float(self.edit2.text())
        a = pCmd.makeBranch(
            DN=d["PSize"],
            PRating=self.PRating,
            OD=float(d["OD"]),
            thk=float(d["thk"]),
            BR=bendRad,
            lab=plLabel,
            color=self.color,
        )
        if self.combo.currentIndex() != 0:
            pCmd.moveToPyLi(a, self.combo.currentText())
        FreeCAD.activeDocument().commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.ActiveDocument.recompute()


class breakForm(QDialog):
    """
    Dialog to break one pipe and create a gap.
    """

    def __init__(
        self,
        winTitle=translate("breakForm", "Break the pipes"),
        PType="Pipe",
        PRating="SCH-STD",
        icon="break.svg",
    ):
        self.refL = 0.0
        super(breakForm, self).__init__()
        self.move(QPoint(100, 250))
        self.PType = PType
        self.PRating = PRating
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(winTitle)
        iconPath = join(dirname(abspath(__file__)), "iconz", icon)
        from PySide.QtGui import QIcon

        Icon = QIcon()
        Icon.addFile(iconPath)
        self.setWindowIcon(Icon)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.btn0 = QPushButton(translate("breakForm", "Length"))
        self.btn0.clicked.connect(self.getL)
        self.lab0 = QLabel(translate("breakForm", "<reference>"))
        self.lab1 = QLabel(translate("breakForm", "PypeLine:"))
        self.combo = QComboBox()
        self.combo.addItem(translate("breakForm", "<none>"))
        try:
            self.combo.addItems(
                [
                    o.Label
                    for o in FreeCAD.activeDocument().Objects
                    if hasattr(o, "PType") and o.PType == "PypeLine"
                ]
            )
        except:
            None
        self.combo.currentIndexChanged.connect(self.setCurrentPL)
        if FreeCAD.__activePypeLine__ and FreeCAD.__activePypeLine__ in [
            self.combo.itemText(i) for i in range(self.combo.count())
        ]:
            self.combo.setCurrentIndex(self.combo.findText(FreeCAD.__activePypeLine__))
        self.edit1 = QLineEdit("0")
        self.edit1.setAlignment(Qt.AlignCenter)
        self.edit1.editingFinished.connect(self.updateSlider)
        self.edit2 = QLineEdit("0")
        self.edit2.setAlignment(Qt.AlignCenter)
        self.edit2.editingFinished.connect(self.calcGapPercent)
        rx = QRegExp("[0-9,.%]*")
        val = QRegExpValidator(rx)
        self.edit1.setValidator(val)
        self.edit2.setValidator(val)
        self.lab2 = QLabel("Point:")
        self.btn1 = QPushButton("Break")
        self.btn1.clicked.connect(self.breakPipe)
        self.btn1.setDefault(True)
        self.btn1.setFocus()
        self.lab3 = QLabel("Gap:")
        self.btn2 = QPushButton("Get gap")
        self.btn2.clicked.connect(self.changeGap)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.changePoint)
        self.slider.setMaximum(100)
        self.grid.addWidget(self.btn0, 4, 0)
        self.grid.addWidget(self.lab0, 4, 1, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.lab1, 0, 0, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.combo, 0, 1, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.lab2, 1, 0, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.edit1, 1, 1)
        self.grid.addWidget(self.lab3, 2, 0, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.edit2, 2, 1)
        self.grid.addWidget(self.btn1, 3, 0)
        self.grid.addWidget(self.btn2, 3, 1)
        self.grid.addWidget(self.slider, 5, 0, 1, 2)
        self.show()

    def setCurrentPL(self, PLName=None):
        if self.combo.currentText() not in [
            translate("breakForm", "<none>"),
            translate("breakForm", "<new>"),
        ]:
            FreeCAD.__activePypeLine__ = self.combo.currentText()
        else:
            FreeCAD.__activePypeLine__ = None

    def getL(self):
        l = [p.Height for p in fCmd.beams() if pCmd.isPipe(p)]
        if l:
            refL = min(l)
            self.lab0.setText(str(refL))
            self.refL = float(refL)
            self.edit1.setText("%.2f" % (self.refL * self.slider.value() / 100.0))
        else:
            self.lab0.setText("<reference>")
            self.refL = 0.0
            self.edit1.setText(str(self.slider.value()) + "%")

    def changePoint(self):
        if self.refL:
            self.edit1.setText("%.2f" % (self.refL * self.slider.value() / 100.0))
        else:
            self.edit1.setText(str(self.slider.value()) + "%")

    def changeGap(self):
        shapes = [
            y
            for x in FreeCADGui.Selection.getSelectionEx()
            for y in x.SubObjects
            if hasattr(y, "ShapeType")
        ]
        if len(shapes) == 1:
            sub = shapes[0]
            if sub.ShapeType == "Edge":
                if sub.curvatureAt(0) == 0:
                    gapL = float(sub.Length)
            else:
                gapL = 0
        elif len(shapes) > 1:
            gapL = shapes[0].distToShape(shapes[1])[0]
        else:
            gapL = 0
        self.edit2.setText("%.2f" % gapL)

    def updateSlider(self):
        if self.edit1.text() and self.edit1.text()[-1] == "%":
            self.slider.setValue(int(float(self.edit1.text().rstrip("%").strip())))
        elif self.edit1.text() and float(self.edit1.text().strip()) < self.refL:
            self.slider.setValue(int(float(self.edit1.text().strip()) / self.refL * 100))

    def calcGapPercent(self):
        if self.edit2.text() and self.edit2.text()[-1] == "%":
            if self.refL:
                self.edit2.setText(
                    "%.2f" % (float(self.edit2.text().rstrip("%").strip()) / 100 * self.refL)
                )
            else:
                self.edit2.setText("0")
                FreeCAD.Console.PrintError("No reference length defined yet\n")

    def breakPipe(self):
        p2nd = None
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Break pipes"))
        if self.edit1.text()[-1] == "%":
            pipes = [p for p in fCmd.beams() if pCmd.isPipe(p)]
            for p in pipes:
                p2nd = pCmd.breakTheTubes(
                    float(p.Height) * float(self.edit1.text().rstrip("%").strip()) / 100,
                    pipes=[p],
                    gap=float(self.edit2.text()),
                )
                if p2nd and self.combo.currentText() != translate("breakForm","<none>"):
                    for p in p2nd:
                        pCmd.moveToPyLi(p, self.combo.currentText())
        else:
            p2nd = pCmd.breakTheTubes(float(self.edit1.text()), gap=float(self.edit2.text()))
            if p2nd and self.combo.currentText() != translate("breakForm","<none>"):
                for p in p2nd:
                    pCmd.moveToPyLi(p, self.combo.currentText())
        FreeCAD.activeDocument().commitTransaction()
        FreeCAD.activeDocument().recompute()


import pObservers as po


class joinForm(dodoDialogs.protoTypeDialog):
    def __init__(self):
        super(joinForm, self).__init__("joinPypes.ui")
        self.form.btn1.clicked.connect(self.reset)
        self.observer = po.joinObserver()
        FreeCADGui.Selection.addObserver(self.observer)

    def reject(self):  # redefined to remove the observer
        info = dict()
        info["State"] = "DOWN"
        info["Key"] = "ESCAPE"
        self.observer.goOut(info)
        super(joinForm, self).reject()

    def accept(self):
        self.reject()

    def selectAction(self):
        self.reset()

    def reset(self):
        po.pCmd.o1 = None
        po.pCmd.o2 = None
        for a in po.pCmd.arrows1 + po.pCmd.arrows2:
            a.closeArrow()
        po.pCmd.arrows1 = []
        po.pCmd.arrows2 = []




class insertValveForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert Valves.

    Two modes selected automatically from the loaded CSV:

    Generic double-cone construction  (CSV has no Conn column, or Conn not SW/TH)
    ----------------------------------------------------------------
      CSV columns : PSize ; VType ; ODBody ; ID ; H ; Kv
      sizeList    : PSize   ODBody x ID
      propList    : [DN, VType, ODBody, ID, H, Kv]
      "Insert in pipe" checkbox + slider are shown.

    Socket-weld / Threaded  (CSV has Conn == "SW" or "TH")
    -------------------------------------------------------
      CSV columns : Psize ; OD ; Vtype ; ODBody ; H ; E ; Conn  [; Kv]
      sizeList    : PSize   OD
      propList    : [DN, VType, OD, ODBody, H, E, Conn, Kv]
      "Insert in pipe" checkbox + slider are hidden.

    A rotation dial lets the last-inserted valve be spun around its
    flow axis (Z) in 15-degree increments, identical to insertElbowForm.
    """

    def __init__(self):
        self.PType     = "Valve"
        self.PRating   = ""
        self.lastValve = None
        self.lastAngle = 0

        super(insertValveForm, self).__init__(
            translate("insertValveForm", "Insert valves"),
            "Valve",
            "ball",
            "valve.svg",
            x,
            y,
        )
        # NOTE: protoPypeForm.__init__ calls self.fillSizes() above.
        # self.sli / self.cb1 do NOT exist yet at that point, so
        # fillSizes() must guard against their absence (see _refreshLayout).

        self.move(QPoint(75, 225))
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)

        # Reconnect rating signal so _changeRating (not base changeRating) fires
        try:
            self.ratingList.itemClicked.disconnect(self.changeRating)
        except Exception:
            pass
        self.ratingList.itemClicked.connect(self._changeRating)

        self.btn1.clicked.connect(self.insert)

        self.btn2 = QPushButton(translate("insertValveForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.reverse)

        self.btn3 = QPushButton(translate("insertValveForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.apply)

        self.btn1.setDefault(True)
        self.btn1.setFocus()

        # Rotation dial (Z-axis spin) -- mirrors insertElbowForm layout
        self.screenDial = QWidget()
        self.screenDial.setLayout(QHBoxLayout())
        self.dial = QDial()
        self.dial.setWrapping(True)
        self.dial.setMaximum(180)
        self.dial.setMinimum(-180)
        self.dial.setNotchTarget(15)
        self.dial.setNotchesVisible(True)
        self.dial.setMaximumSize(70, 70)
        self.screenDial.layout().addWidget(self.dial)
        self.dialLab = QLabel(translate("insertValveForm", "0 deg"))
        self.dialLab.setAlignment(Qt.AlignCenter)
        self.dial.valueChanged.connect(self.rotateDial)
        self.screenDial.layout().addWidget(self.dialLab)
        self.firstCol.layout().addWidget(self.screenDial)

        # "Insert in pipe" controls (generic only; hidden for SW/TH)
        self.sli = QSlider(Qt.Vertical)
        self.sli.setMaximum(100)
        self.sli.setMinimum(1)
        self.sli.setValue(50)
        self.mainHL.addWidget(self.sli)

        self.cb1 = QCheckBox(translate("insertValveForm", " Insert in pipe"))
        self.secondCol.layout().addWidget(self.cb1)

        # Actuator selection radio buttons (flanged valves only)
        self.actuatorGroup = QWidget()
        self.actuatorGroup.setLayout(QHBoxLayout())
        self.actuatorGroup.layout().setContentsMargins(0, 0, 0, 0)
        self.rbHandle   = QRadioButton(translate("insertValveForm", "Handle"))
        self.rbGearbox  = QRadioButton(translate("insertValveForm", "Gearbox"))
        self.rbHandle.setChecked(True)
        self.actuatorGroup.layout().addWidget(self.rbHandle)
        self.actuatorGroup.layout().addWidget(self.rbGearbox)
        self.secondCol.layout().addWidget(self.actuatorGroup)

        # Now that sli, cb1, and actuator controls exist, apply the correct visibility
        self._refreshLayout()
        self.show()

    # ── helper: detect SW/TH rating ──────────────────────────────────────────

    # Pressure-class strings that indicate a flanged valve connection
    _FLANGE_CONNS = ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb")

    def _isFlangedConn(self):
        """Return True when the loaded CSV is a flanged (pressure-class) table."""
        for row in self.pipeDictList:
            if row.get("Conn", "").strip() in self._FLANGE_CONNS:
                return True
        return False

    def _loadFlangePropList(self, conn, psize):
        """Load the matching blind-flange CSV and return the property row for psize.

        File name convention: Flange_ASME-BL-RF-<conn>.csv
        Returns [PSize, FlangeType, D, t, f, n, df, drf, trf] or None.
        """
        fname = "Flange_ASME-BL-RF-" + conn + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r") as fh:
                reader = csv.DictReader(fh, delimiter=";")
                for row in reader:
                    if row.get("PSize", "").strip() == psize:
                        return [
                            row.get("PSize",      "").strip(),
                            row.get("FlangeType", "BL").strip(),
                            float(row.get("D",    "0")),
                            float(row.get("t",    "0")),
                            float(row.get("f",    "0")),
                            int(float(row.get("n", "0"))),
                            float(row.get("df",   "0")),
                            float(row.get("drf",  "0")),
                            float(row.get("trf",  "0")),
                        ]
        except Exception:
            pass
        return None

    def _isSocketConn(self):
        """Return True when the loaded CSV is a SW or TH (socket/threaded) table."""
        for row in self.pipeDictList:
            if row.get("Conn", "").strip().upper() in ("SW", "TH"):
                return True
        return False

    # ── normalise a CSV row so keys are always capitalised consistently ────────

    @staticmethod
    def _normRow(row):
        """Return a copy of row with every key title-cased for safe lookup.

        The Ball-Threaded CSV uses 'Psize' and 'Vtype'; the legacy CSV uses
        'PSize' and 'VType'.  Normalising to lower-case avoids KeyErrors.
        """
        return {k.strip().lower(): v.strip() for k, v in row.items()}

    # ── show/hide controls depending on mode ─────────────────────────────────

    def _refreshLayout(self):
        """Show/hide controls depending on valve connection type.

        - "Insert in pipe" slider/checkbox: shown for legacy BW valves only.
        - Actuator radio buttons (Handle / Gearbox): shown for flanged valves only.

        Called from fillSizes() which runs during __init__ (via super().__init__),
        so controls may not exist yet -- guard with hasattr throughout.
        """
        is_flanged         = self._isFlangedConn()
        is_socket_or_flanged = self._isSocketConn() or is_flanged
        if hasattr(self, "sli"):
            self.sli.setVisible(not is_socket_or_flanged)
        if hasattr(self, "cb1"):
            self.cb1.setVisible(not is_socket_or_flanged)
        if hasattr(self, "actuatorGroup"):
            self.actuatorGroup.setVisible(is_flanged)

    # ── fillSizes override ───────────────────────────────────────────────────

    def fillSizes(self):
        """Load Valve_<PRating>.csv and populate sizeList.

        Legacy (BW)  : label = PSize   ODBody x ID
        SW / TH      : label = PSize   OD
        Flanged      : label = PSize   H
        """
        self.sizeList.clear()
        self.pipeDictList = []
        fname = "Valve_" + self.PRating + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r") as fh:
                self.pipeDictList = list(csv.DictReader(fh, delimiter=";"))
        except Exception:
            return

        for row in self.pipeDictList:
            r = self._normRow(row)
            if self._isFlangedConn():
                # Flanged: show PSize + H (face-to-face length)
                if qu:
                    label = qu.format_psize(r["psize"]) + "  " + qu.format_dim(r["h"])
                else:
                    label = r.get("psize", "") + "  " + r.get("h", "")
            elif self._isSocketConn():
                # SW/TH: show PSize + OD (no ID column in these tables)
                if qu:
                    label = qu.format_psize(r["psize"]) + "  " + qu.format_dim(r["od"])
                else:
                    label = r.get("psize", "") + "  " + r.get("od", "")
            else:
                # Legacy BW: show PSize + ODBody x ID
                if qu:
                    label = (qu.format_psize(r["psize"]) + "  "
                             + qu.format_dim(r.get("odbody", r.get("od", "")))
                             + "x" + qu.format_dim(r.get("id", "")))
                else:
                    label = (r.get("psize", "") + "  "
                             + r.get("odbody", r.get("od", ""))
                             + "x" + r.get("id", ""))
            self.sizeList.addItem(label)

        self._refreshLayout()

    # ── rating-change handler ─────────────────────────────────────────────────

    def _changeRating(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # ── rotation dial ─────────────────────────────────────────────────────────

    def rotateDial(self):
        """Spin the last-inserted valve around its flow axis (Z) by dial delta."""
        if self.lastValve:
            # Undo previous dial position, then apply new one
            pCmd.rotateTheTubeAx(self.lastValve, FreeCAD.Vector(0, 0, 1),
                                  self.lastAngle * -1)
            self.lastAngle = self.dial.value()
            pCmd.rotateTheTubeAx(self.lastValve, FreeCAD.Vector(0, 0, 1),
                                  self.lastAngle)
            self.dialLab.setText(
                str(self.dial.value()) + translate("insertValveForm", " deg"))

    # ── reverse ──────────────────────────────────────────────────────────────

    def reverse(self):
        selValves = [
            p for p in FreeCADGui.Selection.getSelection()
            if hasattr(p, "PType") and p.PType == "Valve"
        ]
        if selValves:
            for p in selValves:
                pCmd.rotateTheTubeAx(p, FreeCAD.Vector(1, 0, 0), 180)
        elif self.lastValve:
            pCmd.rotateTheTubeAx(self.lastValve, FreeCAD.Vector(1, 0, 0), 180)

    # ── insert ────────────────────────────────────────────────────────────────

    def insert(self):
        self.lastAngle = 0
        self.dial.setValue(0)
        d  = self.pipeDictList[self.sizeList.currentRow()]
        r  = self._normRow(d)

        if self._isFlangedConn():
            # Flanged Trunnion Ball valve
            # propList: [DN, VType, H, Kv, Conn]
            psize = r["psize"]
            conn  = r["conn"]
            propList = [
                psize,
                r.get("vtype", self.PRating),
                float(pq(r["h"])),
                float(pq(r.get("kv", "0"))),
                conn,
            ]
            flgPropList = self._loadFlangePropList(conn, psize)
            # Read actuator choice from radio buttons (default to "Handle")
            actuator = "Gearbox" if (hasattr(self, "rbGearbox") and
                                     self.rbGearbox.isChecked()) else "Handle"
            self.lastValve = pCmd.doValves(
                propList, FreeCAD.__activePypeLine__,
                flgPropList=flgPropList, actuator=actuator)[-1]
        elif self._isSocketConn():
            # [DN, VType, OD, ODBody, H, E, Conn, Kv]
            propList = [
                r["psize"],
                r.get("vtype", self.PRating),
                float(pq(r["od"])),
                float(pq(r["odbody"])),
                float(pq(r["h"])),
                float(pq(r["e"])),
                r["conn"],
                float(pq(r.get("kv", "0"))),
            ]
            self.lastValve = pCmd.doValves(propList, FreeCAD.__activePypeLine__)[-1]
        else:
            # [DN, VType, ODBody, ID, H, Kv]
            propList = [
                r["psize"],
                r.get("vtype", self.PRating),
                float(pq(r.get("odbody", r.get("od", "0")))),
                float(pq(r.get("id", "0"))),
                float(pq(r["h"])),
                float(pq(r.get("kv", "0"))),
            ]
            if self.cb1.isChecked():
                pipes = [
                    p for p in FreeCADGui.Selection.getSelection()
                    if hasattr(p, "PType") and p.PType == "Pipe"
                ]
                if pipes:
                    self.lastValve = pCmd.doValves(
                        propList, FreeCAD.__activePypeLine__,
                        self.sli.value())[-1]
                    return
            self.lastValve = pCmd.doValves(propList, FreeCAD.__activePypeLine__)[-1]

    # ── apply ─────────────────────────────────────────────────────────────────

    def apply(self):
        """Push the currently selected size onto all selected Valve objects."""
        d = self.pipeDictList[self.sizeList.currentRow()]
        r = self._normRow(d)

        for obj in FreeCADGui.Selection.getSelection():
            if not (hasattr(obj, "PType") and obj.PType == "Valve"):
                continue

            if self._isSocketConn() and hasattr(obj, "Conn"):
                # Socket-weld / Threaded valve
                obj.PSize   = r["psize"]
                obj.PRating = r.get("vtype", self.PRating)
                obj.OD      = pq(r["od"])
                obj.ODBody  = pq(r["odbody"])
                obj.Height  = pq(r["h"])
                obj.E       = pq(r["e"])
                obj.Conn    = r["conn"]
                obj.Kv      = float(pq(r.get("kv", "0")))
                FreeCAD.activeDocument().recompute()

            elif not self._isSocketConn() and hasattr(obj, "ID"):
                # Legacy / butt-weld valve
                obj.PSize   = r["psize"]
                obj.PRating = r.get("vtype", self.PRating)
                obj.ODBody  = pq(r.get("odbody", r.get("od", "0")))
                obj.ID      = pq(r.get("id", "0"))
                obj.Height  = pq(r["h"])
                obj.Kv      = float(pq(r.get("kv", "0")))
                FreeCAD.activeDocument().recompute()

import DraftTools
import Draft
import uForms
import uCmd
from PySide.QtGui import *


class point2pointPipe(DraftTools.Wire):
    """
    Draw pipes by sequence point.
    """

    def __init__(self, wireFlag=True):
        # view = FreeCADGui.ActiveDocument.ActiveView
        # view.setAxisCross(True)
        # view.hasAxisCross()
        # DraftTools.Line.__init__(self, wireFlag)
        DraftTools.Wire.__init__(self)
        self.Activated()
        self.pform = insertPipeForm()
        self.pform.btn1.setText(translate("point2pointPipe", "Reset"))
        self.pform.btn1.clicked.disconnect(self.pform.insert)
        self.pform.btn1.clicked.connect(self.rset)
        self.pform.btn3.hide()
        self.pform.edit1.hide()
        self.pform.sli.hide()
        self.pform.cb1 = QCheckBox(translate("point2pointPipe", " Move WP on click "))
        self.pform.cb1.setChecked(True)
        self.pform.firstCol.layout().addWidget(self.pform.cb1)
        dialogPath = join(dirname(abspath(__file__)), "dialogz", "hackedline.ui")
        self.hackedUI = FreeCADGui.PySideUic.loadUi(dialogPath)
        self.hackedUI.btnRot.clicked.connect(self.rotateWP)
        self.hackedUI.btnOff.clicked.connect(self.offsetWP)
        self.hackedUI.btnXY.clicked.connect(lambda: self.alignWP(FreeCAD.Vector(0, 0, 1)))
        self.hackedUI.btnXZ.clicked.connect(lambda: self.alignWP(FreeCAD.Vector(0, 1, 0)))
        self.hackedUI.btnYZ.clicked.connect(lambda: self.alignWP(FreeCAD.Vector(1, 0, 0)))
        self.ui.layout.addWidget(self.hackedUI)
        self.start = None
        self.lastPipe = None
        self.nodes = list()

    def alignWP(self, norm):
        FreeCAD.DraftWorkingPlane.alignToPointAndAxis(self.nodes[-1], norm)
        FreeCADGui.Snapper.setGrid()

    def offsetWP(self):
        if hasattr(FreeCAD, "DraftWorkingPlane") and hasattr(FreeCADGui, "Snapper"):
            s = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft").GetInt("gridSize")
            sc = [float(x * s) for x in [1, 1, 0.2]]
            varrow = uCmd.arrow(FreeCAD.DraftWorkingPlane.getPlacement(), scale=sc, offset=s)
            offset = QInputDialog.getInt(
                None,
                translate("pForms", "Offset Work Plane"),
                translate("pForms", "Offset: "),
            )
            if offset[1]:
                uCmd.offsetWP(offset[0])
            FreeCADGui.ActiveDocument.ActiveView.getSceneGraph().removeChild(varrow.node)

    def rotateWP(self):
        self.form = uForms.rotWPForm()

    def rset(self):
        self.start = None
        self.lastPipe = None

    def numericInput(self, numx, numy, numz):
        """Validate the entry fields in the user interface.

        This function is called by the toolbar or taskpanel interface
        when valid x, y, and z have been entered in the input fields.
        """
        self.point = FreeCAD.Vector(numx, numy, numz)
        self.node.append(self.point)
        self.drawSegment(self.point)
        self.sequencepiping()
        if self.mode == "line" and len(self.node) == 2:
            self.finish(cont=None, closed=False)
        self.ui.setNextFocus()
    
    def sequencepiping(self):
            if not self.start:
                self.start = self.point
            else:
                if self.lastPipe:
                    prev = self.lastPipe
                else:
                    prev = None
                d = self.pform.pipeDictList[self.pform.sizeList.currentRow()]
                rating = self.pform.ratingList.currentItem().text()
                v = self.point - self.start
                propList = [
                    d["PSize"],
                    float(pq(d["OD"])),
                    float(pq(d["thk"])),
                    float(v.Length),
                ]
                self.lastPipe = pCmd.makePipe(rating,propList, self.start, v)
                if self.pform.combo.currentText() != "<none>":
                    pCmd.moveToPyLi(self.lastPipe, self.pform.combo.currentText())
                self.start = self.point
                FreeCAD.ActiveDocument.recompute()
                if prev:
                    c = pCmd.makeElbowBetweenThings(
                        prev,
                        self.lastPipe,
                        [
                            d["PSize"],
                            float(pq(d["OD"])),
                            float(pq(d["thk"])),
                            90,
                            float(pq(d["OD"]) * 0.75),
                        ],
                    )
                    if c and self.pform.combo.currentText() != "<none>":
                        pCmd.moveToPyLi(c, self.pform.combo.currentText())
                    FreeCAD.ActiveDocument.recompute()
            if self.pform.cb1.isChecked():
                rot = FreeCAD.DraftWorkingPlane.getPlacement().Rotation
                normal = rot.multVec(FreeCAD.Vector(0, 0, 1))
                FreeCAD.DraftWorkingPlane.alignToPointAndAxis(self.point, normal)
                FreeCADGui.Snapper.setGrid()
            # if not self.isWire and len(self.node) == 2:
            #     self.finish(False, cont=True)
            if len(self.node) > 2:
                if (self.point - self.node[0]).Length < Draft.tolerance():
                    self.undolast()
                    self.finish(True, cont=True)

    def action(self, arg):  # re-defintition of the method of parent
        "scene event handler"
        # FreeCAD.Console.PrintMessage("Tecla presionada: "+str(arg["Key"]))
        if arg["Type"] == "SoKeyboardEvent" and arg["State"] == "DOWN":
            # key detection
            if arg["Key"] == "ESCAPE":
                self.pform.close()
                self.finish()
            return
        elif arg["Type"] == "SoLocation2Event":
            # mouse movement detection
            self.point, ctrlPoint, info = DraftTools.getPoint(self, arg)
            # DraftTools.redraw3DView()
            # FreeCAD.Console.PrintMessage(self.point)
            return
        elif arg["Type"] == "SoMouseButtonEvent":
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Point to Point"))
            # mouse button detection
            if (arg["State"] == "DOWN") and (arg["Button"] == "BUTTON1"):
                if arg["Position"] == self.pos:
                    self.finish(False, cont=True)
                else:
                    if (not self.node) and (not self.support):
                        DraftTools.getSupport(arg)
                        self.point, ctrlPoint, info = DraftTools.getPoint(self, arg)
                    if self.point:
                        self.ui.redraw()
                        self.pos = arg["Position"]
                        self.nodes.append(self.point)
                        self.sequencepiping()
                        # try:
                        # print(arg)
                        # print(self.point)
                        # print(ctrlPoint)
                        # print(info)
                        # except:
                        # pass
            FreeCAD.activeDocument().commitTransaction()
            return


class insertTankForm(dodoDialogs.protoTypeDialog):
    def __init__(self):
        self.nozzles = list()
        super(insertTankForm, self).__init__("tank.ui")
        tablez = listdir(join(dirname(abspath(__file__)), "tablez"))
        self.pipeRatings = [
            s.lstrip("Pipe_").rstrip(".csv")
            for s in tablez
            if s.startswith("Pipe") and s.endswith(".csv")
        ]
        self.flangeRatings = [
            s.lstrip("Flange_").rstrip(".csv")
            for s in tablez
            if s.startswith("Flange") and s.endswith(".csv")
        ]
        self.form.comboPipe.addItems(self.pipeRatings)
        self.form.comboPipe.setToolTip("List available pipe thickness standards")
        self.form.comboFlange.addItems(self.flangeRatings)
        self.form.comboFlange.setToolTip("List available flange standards")
        self.form.btn1.clicked.connect(self.addNozzle)
        self.form.btn1.setToolTip(
            "In order to make it work, must select a circular edge direct from viewer then press this button"
        )
        self.form.editLength.setValidator(QDoubleValidator())
        self.form.editX.setValidator(QDoubleValidator())
        self.form.editY.setValidator(QDoubleValidator())
        self.form.editZ.setValidator(QDoubleValidator())
        self.form.comboPipe.currentIndexChanged.connect(self.combine)
        self.form.comboFlange.currentIndexChanged.connect(self.combine)

    def accept(self):
        dims = list()
        for lineEdit in [self.form.editX, self.form.editY, self.form.editZ]:
            if lineEdit.text():
                dims.append(float(lineEdit.text()))
            else:
                dims.append(1000)
        t = pCmd.makeShell(*dims)
        so = None
        if FreeCADGui.Selection.getSelectionEx():
            so = FreeCADGui.Selection.getSelectionEx()[0].SubObjects
        if so:
            so0 = so[0]
            if so0.Faces:
                t.Placement.Base = so0.Faces[0].CenterOfMass
            elif so0.Edges:
                t.Placement.Base = so0.Edges[0].CenterOfMass
            elif so0.Vertexes:
                t.Placement.Base = so0.Vertexes[0].Point

    def addNozzle(self):
        DN = self.form.listSizes.currentItem().text()
        args = self.nozzles[DN]
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Add nozzles"))
        pCmd.makeNozzle(DN, float(self.form.editLength.text()), *args)
        FreeCAD.ActiveDocument.commitTransaction()

    def combine(self):
        # print(translate("insertTankForm", "doing combine"))
        self.form.listSizes.clear()
        try:
            fileName = "Pipe_" + self.form.comboPipe.currentText() + ".csv"
            # print(fileName)
            f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
            reader = csv.DictReader(f, delimiter=";")
            pipes = dict(
                [[line["PSize"], [float(line["OD"]), float(line["thk"])]] for line in reader]
            )
            f.close()
            fileName = "Flange_" + self.form.comboFlange.currentText() + ".csv"
            # print(fileName)
            f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
            reader = csv.DictReader(f, delimiter=";")
            flanges = dict(
                [
                    [
                        line["PSize"],
                        [
                            float(line["D"]),
                            float(line["d"]),
                            float(line["df"]),
                            float(line["f"]),
                            float(line["t"]),
                            int(line["n"]),
                        ],
                    ]
                    for line in reader
                ]
            )
            f.close()
            # print(translate("insertTankForm", "files read"))
        except:
            # print(translate("insertTankForm", "files not read"))
            return
        listNozzles = [
            [p[0], p[1] + flanges[p[0]]] for p in pipes.items() if p[0] in flanges.keys()
        ]
        # print(translate("insertTankForm", "listNozzles: %s") % str(listNozzles))
        self.nozzles = dict(listNozzles)
        self.form.listSizes.addItems(list(self.nozzles.keys()))
        # self.form.listSizes.sortItems()


class insertRouteForm(dodoDialogs.protoTypeDialog):
    """
    Dialog for makeRoute().
    """

    def __init__(self):
        FreeCADGui.Selection.clearSelection()
        super(insertRouteForm, self).__init__("route.ui")
        self.normal = FreeCAD.Vector(0, 0, 1)
        self.L = 0
        self.obj = None
        self.edge = None
        self.form.edit1.setValidator(QDoubleValidator())
        self.form.btn1.clicked.connect(self.selectAction)
        self.form.btn2.clicked.connect(self.mouseActionB1)
        self.form.btnX.clicked.connect(lambda: self.getPrincipalAx("X"))
        self.form.btnY.clicked.connect(lambda: self.getPrincipalAx("Y"))
        self.form.btnZ.clicked.connect(lambda: self.getPrincipalAx("Z"))
        self.form.slider.valueChanged.connect(
            self.changeOffset
        )  # lambda:self.form.edit1.setText(str(self.form.dial.value())))
        # self.form.edit1.editingFinished.connect(self.moveSlider) #lambda:self.form.dial.setValue(int(round(self.form.edit1.text()))))

    def changeOffset(self):
        if self.L:
            offset = self.L * self.form.slider.value() / 100
            self.form.edit1.setText("%.1f" % offset)

    def getPrincipalAx(self, ax):
        if ax == "X":
            self.normal = FreeCAD.Vector(1, 0, 0)
        elif ax == "Y":
            self.normal = FreeCAD.Vector(0, 1, 0)
        elif ax == "Z":
            self.normal = FreeCAD.Vector(0, 0, 1)
        self.form.lab1.setText("global " + ax)

    def accept(self, ang=None):
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Make pipe route"))
        if fCmd.edges():
            e = fCmd.edges()[0]
            if e.curvatureAt(0):
                pCmd.makeRoute(self.normal)
            else:
                s = FreeCAD.ActiveDocument.addObject("Sketcher::SketchObject", "pipeRoute")
                s.MapMode = "NormalToEdge"
                s.AttachmentSupport = [(self.obj, self.edge)]
                s.AttachmentOffset = FreeCAD.Placement(
                    FreeCAD.Vector(0, 0, -1 * float(self.form.edit1.text())),
                    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0),
                )
                FreeCADGui.activeDocument().setEdit(s.Name)
        FreeCAD.ActiveDocument.commitTransaction()

    def selectAction(self):
        if fCmd.faces():
            self.normal = fCmd.faces()[0].normalAt(0, 0)
        elif fCmd.edges():
            self.normal = fCmd.edges()[0].tangentAt(0)
        else:
            self.normal = FreeCAD.Vector(0, 0, 1)
        self.form.lab1.setText("%.1f,%.1f,%.1f " % (self.normal.x, self.normal.y, self.normal.z))

    def mouseActionB1(self, CtrlAltShift=[False, False, False]):
        v = FreeCADGui.ActiveDocument.ActiveView
        infos = v.getObjectInfo(v.getCursorPos())
        self.form.slider.setValue(0)
        if infos and infos["Component"][:4] == "Edge":
            self.obj = FreeCAD.ActiveDocument.getObject(infos["Object"])
            self.edge = infos["Component"]
            i = int(self.edge[4:]) - 1
            e = self.obj.Shape.Edges[i]
            if e.curvatureAt(0) == 0:
                self.L = e.Length
            else:
                self.L = 0
            self.form.lab2.setText(infos["Object"] + ": " + self.edge)
        elif fCmd.edges():
            selex = FreeCADGui.Selection.getSelectionEx()[0]
            self.obj = selex.Object
            e = fCmd.edges()[0]
            self.edge = fCmd.edgeName(e)[1]
            self.L = float(e.Length)
            self.form.lab2.setText(self.edge + " of " + self.obj.Label)
        else:
            self.L = 0
            self.obj = None
            self.edge = None
            self.form.lab2.setText(translate("insertRouteForm", "<select an edge>"))

class insertGasketForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert spiral-wound gaskets and/or stud bolt sets.
    For position and orientation you can select
      - one circular edge (e.g. a flange face edge),
      - one vertex,
      - a ported object (e.g. a Flange) -- gasket/bolts snap to the selected port,
      - nothing (created at origin).

    Two check boxes control what is inserted:
      Insert Gasket  -- inserts a Gasket object (default: checked)
      Insert Bolts   -- inserts a Bolts_Nuts object (default: unchecked)

    Either or both check boxes may be checked.  If both are checked the gasket
    and the bolt set are inserted as separate objects at the same location.

    Available buttons to reverse the orientation of the last or selected
    gaskets and to apply the current size to existing gaskets.
    """

    # ---------------------------------------------------------------
    # Helper: find the bolt CSV file for the current rating and return
    # the row matching the currently selected PSize.
    # Returns a dict of bolt properties or None if not found.
    # ---------------------------------------------------------------
    def _getBoltRow(self):
        """Load Bolt_<PRating>.csv and return the row for the selected PSize."""
        # Resolve the CSV directory the same way protoPypeForm does.
        csv_dir = join(dirname(abspath(__file__)), "tablez")
        fname = "Bolt_" + self.PRating + ".csv"
        fpath = join(csv_dir, fname)
        try:
            with open(fpath, "r") as fh:
                bolt_list = list(csv.DictReader(fh, delimiter=";"))
        except Exception:
            FreeCAD.Console.PrintError(
                "insertGasketForm: cannot open %s\n" % fpath
            )
            return None

        # Match on PSize from the currently selected gasket row
        d_gasket = self.pipeDictList[self.sizeList.currentRow()]
        psize = d_gasket.get("PSize", "")
        for row in bolt_list:
            if row.get("PSize", "").strip() == psize.strip():
                return row
        FreeCAD.Console.PrintError(
            "insertGasketForm: PSize %s not found in %s\n" % (psize, fname)
        )
        return None

    def __init__(self):
        super(insertGasketForm, self).__init__(
            translate("insertGasketForm", "Insert gaskets"),
            "Gasket",
            "150lb",
            "gasket.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.btn1.clicked.connect(self.insert)

        # --- check boxes for what to insert ---
        self.chkGasket = QCheckBox(
            translate("insertGasketForm", "Insert Gasket")
        )
        self.chkGasket.setChecked(True)
        self.secondCol.layout().addWidget(self.chkGasket)

        self.chkBolts = QCheckBox(
            translate("insertGasketForm", "Insert Bolts")
        )
        self.chkBolts.setChecked(False)
        self.secondCol.layout().addWidget(self.chkBolts)

        self.btn2 = QPushButton(translate("insertGasketForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.reverse)

        self.btn3 = QPushButton(translate("insertGasketForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.apply)

        self.btn1.setDefault(True)
        self.btn1.setFocus()

        # auto-select matching size from whatever is currently selected
        pCmd.autoSelectInPipeForm(self)

        self.show()
        self.lastGasket = None
        self.lastBolts  = None

    def reverse(self):
        selGaskets = [
            g
            for g in FreeCADGui.Selection.getSelection()
            if hasattr(g, "PType") and g.PType == "Gasket"
        ]
        target = selGaskets[0] if selGaskets else self.lastGasket
        if not target:
            return

        # Pin Port[0] (the -Z face) in world space while flipping
        initial_port_pos = target.Placement.multVec(target.Ports[0])
        pCmd.rotateTheTubeAx(target, FreeCAD.Vector(1, 0, 0), 180)
        final_port_pos = target.Placement.multVec(target.Ports[0])
        target.Placement.move(initial_port_pos - final_port_pos)

    def insert(self):
        insert_gasket = self.chkGasket.isChecked()
        insert_bolts  = self.chkBolts.isChecked()

        if not insert_gasket and not insert_bolts:
            FreeCAD.Console.PrintWarning(
                "insertGasketForm: nothing to insert -- check at least one box\n"
            )
            return

        d = self.pipeDictList[self.sizeList.currentRow()]

        if insert_gasket:
            propList = [
                d["PSize"],
                self.PRating,   # FClass comes from the selected rating
                float(pq(d["IRID"])),
                float(pq(d["SEID"])),
                float(pq(d["SEOD"])),
                float(pq(d["CROD"])),
                float(pq(d["SEthk"])),
                float(pq(d["Rthk"])),
            ]
            self.lastGasket = pCmd.doGaskets(
                propList,
                pypeline=FreeCAD.__activePypeLine__,
            )

        if insert_bolts:
            bolt_row = self._getBoltRow()
            if bolt_row is not None:
                # SEthk is taken from the gasket data for the same PSize/rating
                sethk = float(pq(d["SEthk"]))
                bolt_propList = [
                    bolt_row["PSize"],
                    self.PRating,
                    float(pq(bolt_row["dBolt"])),
                    float(pq(bolt_row["dNut"])),
                    float(pq(bolt_row["tNut"])),
                    float(pq(bolt_row["df"])),
                    int(float(bolt_row["n"])),
                    float(pq(bolt_row["lBolt"])),
                    sethk,
                ]
                self.lastBolts = pCmd.doBolts_Nuts(
                    bolt_propList,
                    pypeline=FreeCAD.__activePypeLine__,
                )

    def apply(self):
        """Apply the currently selected size to already-placed gaskets."""
        d = self.pipeDictList[self.sizeList.currentRow()]
        targets = [
            g
            for g in FreeCADGui.Selection.getSelection()
            if hasattr(g, "PType") and g.PType == "Gasket"
        ]
        if not targets and self.lastGasket:
            targets = [self.lastGasket]
        for g in targets:
            g.PSize   = d["PSize"]
            g.FClass  = self.PRating
            g.IRID    = float(pq(d["IRID"]))
            g.SEID    = float(pq(d["SEID"]))
            g.SEOD    = float(pq(d["SEOD"]))
            g.CROD    = float(pq(d["CROD"]))
            g.SEthk   = float(pq(d["SEthk"]))
            g.Rthk    = float(pq(d["Rthk"]))
        FreeCAD.activeDocument().recompute()

class insertBeamForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert structural beam sections.
    Selection behaviour:
      - Select a ported frame object -> beam snaps to that port
      - Select a straight edge       -> beam aligns to edge, length = edge length
      - Select a vertex              -> beam placed at vertex, default orientation
      - Nothing selected             -> beam placed at origin
    Reverse button keeps Port[0] (the base end) pinned in world space.
    Apply button updates properties of already-placed beams.
    """

    def __init__(self):
        super(insertBeamForm, self).__init__(
            translate("insertBeamForm", "Insert beam section"),
            "Beam",          # PType used to filter CSV filenames: Beam_<rating>.csv
            "HEA",           # default rating shown on open
            "structure.svg", # replace with a dedicated icon if available
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)
        self.btn1.clicked.connect(self.insert)

        # Length field and slider (mirrors insertPipeForm)
        self.edit1 = QLineEdit()
        _unit_hint = qu.get_length_unit() if qu else "mm"
        self.edit1.setPlaceholderText(
            translate("insertBeamForm", "<length> (") + _unit_hint + ")")
        self.edit1.setAlignment(Qt.AlignHCenter)
        self.edit1.editingFinished.connect(lambda: self.sli.setValue(100))
        self.secondCol.layout().addWidget(self.edit1)

        self.btn2 = QPushButton(translate("insertBeamForm", "Reverse"))
        self.secondCol.layout().addWidget(self.btn2)
        self.btn2.clicked.connect(self.reverse)

        self.btn3 = QPushButton(translate("insertBeamForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn3)
        self.btn3.clicked.connect(self.apply)

        self.btn1.setDefault(True)
        self.btn1.setFocus()

        # Vertical length slider
        self.sli = QSlider(Qt.Vertical)
        self.sli.setMaximum(200)
        self.sli.setMinimum(1)
        self.sli.setValue(100)
        self.mainHL.addWidget(self.sli)
        self.sli.valueChanged.connect(self.changeL)

        self.show()
        self.lastBeam = None
        self.H = 1000.0   # default length in mm

    def changeL(self, val):
        """Scale the displayed length proportionally with the slider."""
        if self.edit1.text():
            try:
                base = float(pq(self.edit1.text()))
            except Exception:
                base = self.H
        else:
            base = self.H
        self.H = base * val / 100.0
        self.edit1.setText("{:.1f}".format(self.H))

    def reverse(self):
        """Flip the last-inserted (or selected) beam, keeping Port[0] pinned."""
        selBeams = [
            b for b in FreeCADGui.Selection.getSelection()
            if hasattr(b, "FType") and b.FType == "Beam"
        ]
        target = selBeams[0] if selBeams else self.lastBeam
        if not target:
            return
        initial = target.Placement.multVec(target.Ports[0])
        pCmd.rotateTheTubeAx(target, FreeCAD.Vector(1, 0, 0), 180)
        final = target.Placement.multVec(target.Ports[0])
        target.Placement.move(initial - final)

    def insert(self):
        d = self.pipeDictList[self.sizeList.currentRow()]
        if self.edit1.text():
            try:
                self.H = float(pq(self.edit1.text()))
            except Exception:
                pass
        self.sli.setValue(100)

        propList = [
            self.PRating,           # rating / standard
            d["PSize"],             # SSize designation
            d["stype"],             # profile type code
            float(pq(d["H"])),
            float(pq(d["W"])),
            float(pq(d["ta"])),
            float(pq(d["tf"])),
            self.H,                 # beam length
        ]
        self.lastBeam = pCmd.doBeams(propList)

    def apply(self):
        """Apply currently selected size to already-placed Beam objects."""
        d = self.pipeDictList[self.sizeList.currentRow()]
        targets = [
            b for b in FreeCADGui.Selection.getSelection()
            if hasattr(b, "FType") and b.FType == "Beam"
        ]
        if not targets and self.lastBeam:
            targets = [self.lastBeam]
        for b in targets:
            b.FRating = self.PRating
            b.SSize   = d["PSize"]
            b.stype   = d["stype"]
            b.H       = float(pq(d["H"]))
            b.W       = float(pq(d["W"]))
            b.ta      = float(pq(d["ta"]))
            b.tf      = float(pq(d["tf"]))
        FreeCAD.activeDocument().recompute()


class insertOutletForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert Outlet fittings .

    CSV naming convention (tablez/Outlet_<rating>.csv):
      PSize ; OD ; thk ; A ; B ; [E ;] Ang ; Conn
      Ang  = 0  -> straight     Conn = BW -> butt-weld
      Ang  = 45 -> 45 deg lat.  Conn = SW -> socket-weld

    Position controls (Pipe / Tee host):
      Axial slider + spinbox  - distance from Port 0 along run axis
      Rotation dial + spinbox - circumferential angle around run axis (phi)
        0 deg = pipe/tee local +X
        Tee default: phi = 270 deg (opposite branch)

    Spin control (45 deg lateral only):
      Spin dial + spinbox - rotation of the fitting around its own outward axis
        0 deg = lateral branch points along pipe/tee run axis
        90 deg = lateral branch points circumferentially
    """

    def __init__(self):
        # State attrs must be set BEFORE super().__init__ because
        # protoPypeForm calls self.fillSizes() during its __init__.
        self._angFilter   = 0      # 0 = straight, 45 = lateral
        self._srcObj      = None
        self._t           = None
        self._phi         = 0.0
        self._alpha       = 0.0    # spin around fitting's own outward axis
        self._t_max       = 1000.0
        self._updating_ui = False
        self.lastOutlet   = None

        super(insertOutletForm, self).__init__(
            translate("insertOutletForm", "Insert Outlet"),
            "Outlet",
            "Sch-STD",
            "Quetzal_InsertOutlet.svg",
            x,
            y,
        )

        # -- Outlet angle radio buttons  (secondCol) -----------------------
        self.angGroup = QGroupBox(translate("insertOutletForm", "Outlet Angle"))
        angLayout = QVBoxLayout(self.angGroup)
        self._angBG    = QButtonGroup(self)
        self._radioStr = QRadioButton(translate("insertOutletForm", "Straight (0 deg)"))
        self._radioLat = QRadioButton(translate("insertOutletForm", "45 deg Lateral"))
        self._radioStr.setChecked(True)
        self._angBG.addButton(self._radioStr,  0)
        self._angBG.addButton(self._radioLat, 45)
        angLayout.addWidget(self._radioStr)
        angLayout.addWidget(self._radioLat)
        self.secondCol.layout().addWidget(self.angGroup)

        # -- Position-on-host group  (secondCol) ---------------------------
        self._posGroup = QGroupBox(
            translate("insertOutletForm", "Position on Host"))
        pgLayout = QVBoxLayout(self._posGroup)
        pgLayout.setSpacing(3)

        # Axial slider row
        _ax_unit = qu.get_length_unit() if qu else "mm"
        pgLayout.addWidget(QLabel(
            translate("insertOutletForm", "Distance from Port 0 (") + _ax_unit + "):"))
        axRow = QHBoxLayout()
        self._axSlider = QSlider(Qt.Horizontal)
        self._axSlider.setMinimum(0)
        self._axSlider.setMaximum(1000)
        self._axSlider.setValue(500)
        self._axSpin = QDoubleSpinBox()
        self._axSpin.setDecimals(3)
        self._axSpin.setMinimum(0.0)
        self._axSpin.setMaximum(999999.0)
        self._axSpin.setSuffix(" " + _ax_unit)
        self._axSpin.setFixedWidth(100)
        axRow.addWidget(self._axSlider)
        axRow.addWidget(self._axSpin)
        pgLayout.addLayout(axRow)

        # Circumferential rotation dial row (phi - positions fitting on pipe)
        pgLayout.addWidget(QLabel(
            translate("insertOutletForm", "Position angle (deg):")))
        rotRow = QHBoxLayout()
        self._dial = QDial()
        self._dial.setMinimum(0)
        self._dial.setMaximum(359)
        self._dial.setValue(0)
        self._dial.setWrapping(True)
        self._dial.setNotchesVisible(True)
        self._dial.setNotchTarget(30)
        self._dial.setMaximumSize(72, 72)
        self._rotSpin = QDoubleSpinBox()
        self._rotSpin.setDecimals(1)
        self._rotSpin.setMinimum(0.0)
        self._rotSpin.setMaximum(359.9)
        self._rotSpin.setSuffix(" deg")
        self._rotSpin.setWrapping(True)
        self._rotSpin.setFixedWidth(78)
        rotRow.addWidget(self._dial)
        rotRow.addWidget(self._rotSpin, alignment=Qt.AlignVCenter)
        pgLayout.addLayout(rotRow)

        # Spin dial row (alpha - rotates 45-deg fitting around its own axis)
        # Hidden when Straight is selected; shown for 45 deg Lateral.
        self._spinWidget = QWidget()
        spinLayout = QVBoxLayout(self._spinWidget)
        spinLayout.setContentsMargins(0, 0, 0, 0)
        spinLayout.setSpacing(2)
        spinLayout.addWidget(QLabel(
            translate("insertOutletForm", "Lateral alignment angle (deg):")))
        spinHint = QLabel(translate("insertOutletForm",
            "0 deg = branch along pipe axis"))
        spinHint.setStyleSheet("color: grey; font-size: 9pt;")
        spinLayout.addWidget(spinHint)
        spinRow = QHBoxLayout()
        self._spinDial = QDial()
        self._spinDial.setMinimum(-180)
        self._spinDial.setMaximum(180)
        self._spinDial.setValue(0)
        self._spinDial.setWrapping(True)
        self._spinDial.setNotchesVisible(True)
        self._spinDial.setNotchTarget(30)
        self._spinDial.setMaximumSize(72, 72)
        self._spinSpin = QDoubleSpinBox()
        self._spinSpin.setDecimals(1)
        self._spinSpin.setMinimum(-180.0)
        self._spinSpin.setMaximum(180.0)
        self._spinSpin.setSuffix(" deg")
        self._spinSpin.setWrapping(True)
        self._spinSpin.setFixedWidth(78)
        spinRow.addWidget(self._spinDial)
        spinRow.addWidget(self._spinSpin, alignment=Qt.AlignVCenter)
        spinLayout.addLayout(spinRow)
        self._spinWidget.hide()   # only visible for 45 deg lateral

        self._posHint = QLabel("")
        self._posHint.setWordWrap(True)
        self._posHint.setStyleSheet("color: grey; font-size: 9pt;")
        pgLayout.addWidget(self._posHint)

        self.secondCol.layout().addWidget(self._posGroup)
        # _spinWidget is outside _posGroup so it remains visible for elbows
        self.secondCol.layout().addWidget(self._spinWidget)

        # -- Extra buttons  (secondCol) ------------------------------------
        self.btn2 = QPushButton(translate("insertOutletForm", "Reverse"))
        self.btn3 = QPushButton(translate("insertOutletForm", "Apply"))
        self.secondCol.layout().addWidget(self.btn2)
        self.secondCol.layout().addWidget(self.btn3)

        # -- Signals -------------------------------------------------------
        self._radioStr.toggled.connect(self._onAngChanged)
        self._radioLat.toggled.connect(self._onAngChanged)
        self.ratingList.itemClicked.connect(self._changeRating)
        self.btn1.clicked.connect(self.insert)
        self.btn2.clicked.connect(self.reverse)
        self.btn3.clicked.connect(self.apply)
        self._axSlider.valueChanged.connect(self._onSliderChanged)
        self._axSpin.valueChanged.connect(self._onAxSpinChanged)
        self._dial.valueChanged.connect(self._onDialChanged)
        self._rotSpin.valueChanged.connect(self._onRotSpinChanged)
        self._spinDial.valueChanged.connect(self._onSpinDialChanged)
        self._spinSpin.valueChanged.connect(self._onSpinSpinChanged)

        self.btn1.setDefault(True)
        self.btn1.setFocus()

        # -- Initial fill --------------------------------------------------
        for _i in range(self.ratingList.count()):
            if self.ratingList.item(_i).text() == self.PRating:
                self.ratingList.setCurrentRow(_i)
                break
        self.fillSizes()
        self.sizeList.setCurrentRow(0)
        self._detectHostObject()

        self.show()
        self.lastOutlet = None

    # =======================================================================
    # Overridden: fillSizes  -  filter rows by _angFilter
    # =======================================================================

    def fillSizes(self):
        self.sizeList.clear()
        self.pipeDictList = []
        fname = "Outlet_" + self.PRating + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r") as fh:
                all_rows = list(csv.DictReader(fh, delimiter=";"))
        except Exception:
            return
        ang_str = str(self._angFilter)
        for row in all_rows:
            if row.get("Ang", "0") == ang_str:
                self.pipeDictList.append(row)
                if qu:
                    psize = qu.format_psize(row["PSize"])
                    od    = qu.format_dim(row["OD"])
                    thk   = qu.format_dim(row["thk"])
                    label = psize + "  " + od + " x " + thk + "  " + row.get("Conn", "")
                else:
                    label = (row["PSize"] + "  " + row["OD"] + "x" + row["thk"]
                             + "  " + row.get("Conn", ""))
                self.sizeList.addItem(label)

    # =======================================================================
    # Rating / angle filter callbacks
    # =======================================================================

    def _changeRating(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    def _onAngChanged(self):
        self._angFilter = 45 if self._radioLat.isChecked() else 0
        # Show spin control only for 45-deg lateral, then resize the dialog
        if self._angFilter == 45:
            self._spinWidget.show()
        else:
            self._spinWidget.hide()
            self._alpha = 0.0
        self.adjustSize()
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # =======================================================================
    # Host-object detection
    # =======================================================================

    def _detectHostObject(self):
        self._srcObj = None
        try:
            selex = FreeCADGui.Selection.getSelectionEx()
            if selex and hasattr(selex[0].Object, "PType"):
                self._srcObj = selex[0].Object
        except Exception:
            pass

        if self._srcObj is None:
            self._posGroup.hide()
            self._posHint.setText("")
            return

        ptype = self._srcObj.PType

        if ptype == "Pipe":
            H = float(self._srcObj.Height)
            self._t_max = H
            self._t = H / 2.0
            self._phi = 0.0
            self._posGroup.show()
            self._posHint.setText(translate("insertOutletForm",
                "0 deg = pipe local +X"))
            self._syncSlider(self._t)
            self._syncDial(self._phi)

        elif ptype == "Tee":
            C = float(self._srcObj.C)
            self._t_max = 2.0 * C
            self._t = C
            self._phi = 270.0
            self._posGroup.show()
            self._posHint.setText(translate("insertOutletForm",
                "Branch ~90 deg  |  0 deg = local +X"))
            self._syncSlider(self._t)
            self._syncDial(self._phi)

        elif ptype == "Elbow":
            self._posGroup.hide()
            self._posHint.setText(translate("insertOutletForm",
                "Elbow: placed at bend midpoint (outer face)"))
            if self._angFilter == 45:
                self._spinWidget.show()
            else:
                self._spinWidget.hide()

        else:
            self._posGroup.hide()
            self._posHint.setText("")

    # =======================================================================
    # Sync helpers
    # =======================================================================

    def _syncSlider(self, t_mm):
        self._updating_ui = True
        frac = t_mm / self._t_max if self._t_max > 0 else 0.0
        self._axSlider.setValue(int(round(frac * 1000)))
        if qu:
            _u = qu.get_length_unit()
            _cvt = lambda v: float(FreeCAD.Units.parseQuantity(str(v) + " mm").getValueAs(_u))
            self._axSpin.setMaximum(_cvt(self._t_max))
            self._axSpin.setValue(_cvt(t_mm))
        else:
            self._axSpin.setMaximum(self._t_max)
            self._axSpin.setValue(t_mm)
        self._updating_ui = False

    def _syncDial(self, phi_deg):
        self._updating_ui = True
        self._dial.setValue(int(round(phi_deg)) % 360)
        self._rotSpin.setValue(phi_deg % 360.0)
        self._updating_ui = False

    def _syncSpinDial(self, alpha_deg):
        self._updating_ui = True
        a = max(-180.0, min(180.0, alpha_deg))
        self._spinDial.setValue(int(round(a)))
        self._spinSpin.setValue(a)
        self._updating_ui = False

    # =======================================================================
    # Signal handlers - axial slider / circumferential dial / spin dial
    # =======================================================================

    def _onSliderChanged(self, val):
        if self._updating_ui:
            return
        self._t = (val / 1000.0) * self._t_max
        self._updating_ui = True
        self._axSpin.setValue(self._t)
        self._updating_ui = False
        self._liveUpdate()

    def _onAxSpinChanged(self, val):
        if self._updating_ui:
            return
        if qu:
            _u = qu.get_length_unit()
            self._t = float(FreeCAD.Units.parseQuantity(str(val) + " " + _u).getValueAs("mm"))
        else:
            self._t = val
        frac = self._t / self._t_max if self._t_max > 0 else 0.0
        self._updating_ui = True
        self._axSlider.setValue(int(round(frac * 1000)))
        self._updating_ui = False
        self._liveUpdate()

    def _onDialChanged(self, val):
        if self._updating_ui:
            return
        self._phi = float(val)
        self._updating_ui = True
        self._rotSpin.setValue(self._phi)
        self._updating_ui = False
        self._liveUpdate()

    def _onRotSpinChanged(self, val):
        if self._updating_ui:
            return
        self._phi = val % 360.0
        self._updating_ui = True
        self._dial.setValue(int(round(self._phi)) % 360)
        self._updating_ui = False
        self._liveUpdate()

    def _onSpinDialChanged(self, val):
        if self._updating_ui:
            return
        self._alpha = float(val)
        self._updating_ui = True
        self._spinSpin.setValue(self._alpha)
        self._updating_ui = False
        self._liveUpdate()

    def _onSpinSpinChanged(self, val):
        if self._updating_ui:
            return
        self._alpha = val
        self._updating_ui = True
        self._spinDial.setValue(int(round(val)))
        self._updating_ui = False
        self._liveUpdate()

    def _liveUpdate(self):
        """Reposition the last-inserted outlet in real time."""
        if self.lastOutlet is None or self._srcObj is None:
            return
        try:
            ptype = self._srcObj.PType
            if ptype == "Pipe":
                pos, rot = pCmd.outletPlacementOnPipe(
                    self._srcObj, self._t, self._phi, self._alpha)
            elif ptype == "Tee":
                pos, rot = pCmd.outletPlacementOnTee(
                    self._srcObj, self._t, self._phi, self._alpha)
            elif ptype == "Elbow":
                pos, rot = pCmd.outletPlacementOnElbow(
                    self._srcObj, self._alpha)
            else:
                return
            self.lastOutlet.Placement = FreeCAD.Placement(pos, rot)
            FreeCAD.activeDocument().recompute()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                "insertOutletForm._liveUpdate: " + str(exc) + "\n")

    # =======================================================================
    # Action buttons
    # =======================================================================

    def _buildPropList(self):
        row = self.sizeList.currentRow()
        if row < 0 or row >= len(self.pipeDictList):
            return None
        d = self.pipeDictList[row]
        E = float(pq(d["E"])) if "E" in d and d["E"].strip() else 0.0
        return [
            self.PRating,
            d["PSize"],
            float(pq(d["OD"])),
            float(pq(d["thk"])),
            float(pq(d["A"])),
            float(pq(d["B"])),
            d.get("Conn", "BW"),       # passed straight to pFeatures as EndType
            int(d.get("Ang", "0")),
            E,
        ]

    def insert(self):
        self._detectHostObject()
        propList = self._buildPropList()
        if propList is None:
            FreeCAD.Console.PrintWarning("insertOutletForm: no size selected\n")
            return

        pl = (self.combo.currentText()
              if self.combo.currentText() != "<none>" else None)
        t_use     = self._t     if self._srcObj is not None else None
        phi_use   = self._phi   if self._srcObj is not None else None
        alpha_use = self._alpha if self._srcObj is not None else 0.0

        result = pCmd.doOutlets(propList, pl,
                                srcObj=self._srcObj,
                                t=t_use, phi_deg=phi_use,
                                alpha_deg=alpha_use)
        if result:
            self.lastOutlet = result[-1]

        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        if self.lastOutlet:
            FreeCADGui.Selection.addSelection(self.lastOutlet)

    def reverse(self):
        """Flip 180 deg in circumferential position (phi), keeping axial pos."""
        if self.lastOutlet is None or self._srcObj is None:
            objs = [o for o in FreeCADGui.Selection.getSelection()
                    if hasattr(o, "PType") and o.PType == "Outlet"]
            tgt = objs[0] if objs else self.lastOutlet
            if tgt:
                pCmd.rotateTheTubeAx(tgt, FreeCAD.Vector(1, 0, 0), 180)
            return
        self._phi = (self._phi + 180.0) % 360.0
        self._syncDial(self._phi)
        self._liveUpdate()

    def apply(self):
        """Push current size/rating onto all selected Outlet objects."""
        propList = self._buildPropList()
        if propList is None:
            return
        for obj in FreeCADGui.Selection.getSelection():
            if not (hasattr(obj, "PType") and obj.PType == "Outlet"):
                continue
            obj.PRating = propList[0]
            obj.PSize   = propList[1]
            obj.OD      = propList[2]
            obj.thk     = propList[3]
            obj.A       = propList[4]
            obj.B       = propList[5]
            obj.EndType = propList[6]
            obj.Angle   = propList[7]
            obj.E       = propList[8]
        FreeCAD.activeDocument().recompute()

class insertCouplingUnionForm(dodoDialogs.protoPypeForm):
    """
    Dialog to insert a socket-weld coupling or union.

    A radio-button pair at the top of the second column selects whether a
    Coupling or a Union is being inserted.

    Coupling mode
    ─────────────
      CSV: Coupling_<rating>.csv  columns: PSize;PSize2;OD;OD2;A;C;D;E;Conn
      Primary sizeList  : unique PSize values  (port 0 nominal diameter)
      Secondary portList: matching PSize2 rows for the selected PSize
      Insert  → pCmd.doSocketCoupling (9-element propList)
      Apply   → pushes properties onto selected SocketCoupling objects

    Union mode
    ──────────
      CSV: Union_<rating>.csv  columns: PSize;OD;A;C;D;E;Conn  (no header row)
      sizeList: all sizes; no second list needed
      Insert  → pCmd.doSocketUnion (7-element propList)
      Apply   → pushes properties onto selected SocketUnion objects
    """

    # Union CSV has no header — define fieldnames here so DictReader works.
    _UNION_FIELDS = ["PSize", "OD", "A", "C", "D", "E", "Conn"]

    def __init__(self):
        # Initialise as a Coupling form (PType="Coupling" so the rating list
        # scans for files named Coupling_*.csv).
        super(insertCouplingUnionForm, self).__init__(
            translate("insertCouplingUnionForm", "Insert coupling / union"),
            "Coupling",
            "3000lb_SW",
            "Quetzal_CouplingUnion.svg",
            x,
            y,
        )
        self.sizeList.setCurrentRow(0)
        self.ratingList.setCurrentRow(0)

        # ── mode radio buttons ────────────────────────────────────────────────
        self._modeGroup   = QButtonGroup()
        self._couplingRad = QRadioButton(
            translate("insertCouplingUnionForm", "Coupling"))
        self._unionRad    = QRadioButton(
            translate("insertCouplingUnionForm", "Union"))
        self._couplingRad.setChecked(True)
        self._modeGroup.addButton(self._couplingRad)
        self._modeGroup.addButton(self._unionRad)
        self.secondCol.layout().addWidget(self._couplingRad)
        self.secondCol.layout().addWidget(self._unionRad)
        self._couplingRad.toggled.connect(self._onModeChange)

        # ── secondary port-2 size list (coupling only) ────────────────────────
        self._port2DictList = []
        self._port2Label    = QLabel(
            translate("insertCouplingUnionForm", "Port 1 size:"))
        self._port2List     = QListWidget()
        self._port2List.setMaximumHeight(100)
        self.secondCol.layout().addWidget(self._port2Label)
        self.secondCol.layout().addWidget(self._port2List)

        # ── buttons ───────────────────────────────────────────────────────────
        self.btn1.clicked.connect(self.insert)
        self._btnReverse = QPushButton(
            translate("insertCouplingUnionForm", "Reverse"))
        self.secondCol.layout().addWidget(self._btnReverse)
        self._btnReverse.clicked.connect(self.reverse)
        self._btnApply = QPushButton(
            translate("insertCouplingUnionForm", "Apply"))
        self.secondCol.layout().addWidget(self._btnApply)
        self._btnApply.clicked.connect(self.apply)
        self.btn1.setDefault(True)
        self.btn1.setFocus()

        # Rewire rating-change so fillSizes() is called correctly.
        try:
            self.ratingList.itemClicked.disconnect(self.changeRating)
        except Exception:
            pass
        self.ratingList.itemClicked.connect(self._changeRating)

        # Keep port-2 list in sync when primary selection changes.
        self.sizeList.currentItemChanged.connect(self._fillPort2)

        pCmd.autoSelectInPipeForm(self)

        self.show()
        self.lastFitting = None

    # ── mode helpers ──────────────────────────────────────────────────────────

    def _isCoupling(self):
        return self._couplingRad.isChecked()

    def _onModeChange(self):
        """Called when the Coupling/Union radio button changes."""
        is_coupling = self._isCoupling()
        # Swap the PType so the rating scan picks up the right CSV files.
        self.PType = "Coupling" if is_coupling else "Union"
        # Show/hide the secondary list.
        self._port2Label.setVisible(is_coupling)
        self._port2List.setVisible(is_coupling)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # ── rating-change handler ─────────────────────────────────────────────────

    def _changeRating(self, item):
        self.PRating = item.text()
        self.currentRatingLab.setText(
            translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()
        self.sizeList.setCurrentRow(0)

    # ── fillSizes override ────────────────────────────────────────────────────
    def fillSizes(self):
        """Load the appropriate CSV and populate sizeList (and port-2 list for couplings)."""
        self.sizeList.clear()
        self.pipeDictList = []

        fname = self.PType + "_" + self.PRating + ".csv"
        fpath = join(dirname(abspath(__file__)), "tablez", fname)
        try:
            with open(fpath, "r", encoding="utf-8-sig") as fh:
                if self._isCoupling():
                    self.pipeDictList = list(csv.DictReader(fh, delimiter=";"))
                else:
                    self.pipeDictList = list(
                        csv.DictReader(fh, fieldnames=self._UNION_FIELDS, delimiter=";"))
        except Exception:
            return

        if self._isCoupling():
            seen = []
            for row in self.pipeDictList:
                ps = row["PSize"]
                if ps not in seen:
                    seen.append(ps)
                    if qu:
                        label = qu.format_psize(ps) + "  " + qu.format_dim(row.get("OD", ""))
                    else:
                        label = ps + "  " + row.get("OD", "")
                    self.sizeList.addItem(label)
        else:
            for row in self.pipeDictList:
                if qu:
                    label = qu.format_psize(row["PSize"]) + "  " + qu.format_dim(row.get("OD", ""))
                else:
                    label = row["PSize"] + "  " + row.get("OD", "")
                self.sizeList.addItem(label)

        self._fillPort2()

    def _fillPort2(self):
        """Populate _port2List with PSize2 options for the selected PSize."""
        self._port2List.clear()
        self._port2DictList = []

        if not self._isCoupling() or not self.pipeDictList:
            return

        seen = []
        for row in self.pipeDictList:
            if row["PSize"] not in seen:
                seen.append(row["PSize"])

        idx = self.sizeList.currentRow()
        if idx < 0 or idx >= len(seen):
            return
        run_psize = seen[idx]

        for row in self.pipeDictList:
            if row["PSize"] != run_psize:
                continue
            self._port2DictList.append(row)
            if qu:
                label = qu.format_psize(row.get("PSize2", "")) + "  " + qu.format_dim(row.get("OD2", ""))
            else:
                label = row.get("PSize2", "") + "  " + row.get("OD2", "")
            self._port2List.addItem(label)

        self._port2List.setCurrentRow(0)

    # ── insert ────────────────────────────────────────────────────────────────

    def insert(self):
        if self._isCoupling():
            # Use the row selected from the secondary list.
            idx = self._port2List.currentRow()
            if idx < 0 or idx >= len(self._port2DictList):
                FreeCAD.Console.PrintWarning(
                    "insertCouplingUnionForm: no port-1 size selected\n")
                return
            d = self._port2DictList[idx]
            propList = [
                d["PSize"],
                d.get("PSize2", d["PSize"]),
                float(pq(d["OD"])),
                float(pq(d["OD2"])),
                float(pq(d["A"])),
                float(pq(d["C"])),
                float(pq(d["D"])),
                float(pq(d["E"])),
                d.get("Conn", "SW"),
            ]
            self.lastFitting = pCmd.doSocketCoupling(
                propList, FreeCAD.__activePypeLine__)[-1]
        else:
            # Union: use the row selected from the primary list.
            idx = self.sizeList.currentRow()
            if idx < 0 or idx >= len(self.pipeDictList):
                FreeCAD.Console.PrintWarning(
                    "insertCouplingUnionForm: no size selected\n")
                return
            d = self.pipeDictList[idx]
            propList = [
                d["PSize"],
                float(pq(d["OD"])),
                float(pq(d["A"])),
                float(pq(d["C"])),
                float(pq(d["D"])),
                float(pq(d["E"])),
                d.get("Conn", "SW"),
            ]
            self.lastFitting = pCmd.doSocketUnion(
                propList, FreeCAD.__activePypeLine__)[-1]

        FreeCAD.activeDocument().recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.lastFitting)

    # ── reverse ───────────────────────────────────────────────────────────────

    def reverse(self):
        """Flip selected couplings/unions (or the last inserted one) 180° around X."""
        ptypes = ("SocketCoupling", "SocketUnion")
        sel = [p for p in FreeCADGui.Selection.getSelection()
               if hasattr(p, "PType") and p.PType in ptypes]
        if sel:
            for p in sel:
                pCmd.rotateTheTubeAx(p, FreeCAD.Vector(1, 0, 0), 180)
        elif self.lastFitting:
            pCmd.rotateTheTubeAx(self.lastFitting, FreeCAD.Vector(1, 0, 0), 180)

    # ── apply ─────────────────────────────────────────────────────────────────

    def apply(self):
        """Push current size/rating onto all selected coupling or union objects."""
        for obj in FreeCADGui.Selection.getSelection():
            if not hasattr(obj, "PType"):
                continue

            if obj.PType == "SocketCoupling" and self._isCoupling():
                idx = self._port2List.currentRow()
                if idx < 0 or idx >= len(self._port2DictList):
                    continue
                d = self._port2DictList[idx]
                obj.PSize   = d["PSize"]
                obj.PSize2  = d.get("PSize2", d["PSize"])
                obj.OD      = pq(d["OD"])
                obj.OD2     = pq(d["OD2"])
                obj.A       = pq(d["A"])
                obj.C       = pq(d["C"])
                obj.D       = pq(d["D"])
                obj.E       = pq(d["E"])
                obj.Conn    = d.get("Conn", "SW")
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()

            elif obj.PType == "SocketUnion" and not self._isCoupling():
                idx = self.sizeList.currentRow()
                if idx < 0 or idx >= len(self.pipeDictList):
                    continue
                d = self.pipeDictList[idx]
                obj.PSize   = d["PSize"]
                obj.OD      = pq(d["OD"])
                obj.A       = pq(d["A"])
                obj.C       = pq(d["C"])
                obj.D       = pq(d["D"])
                obj.E       = pq(d["E"])
                obj.Conn    = d.get("Conn", "SW")
                obj.PRating = self.PRating
                FreeCAD.activeDocument().recompute()
