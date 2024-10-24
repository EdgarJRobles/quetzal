# (c) 2019 R. T. LGPL: part of dodo w.b. for FreeCAD

__title__ = "query dialog"
__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

translate = FreeCAD.Qt.translate

# UI Class definitions


class QueryForm(QtGui.QDialog):  # QWidget):
    "form for qCmd.py"

    def __init__(self, Selection):
        super(QueryForm, self).__init__()
        self.initUI()
        self.Selection = Selection

    def initUI(self):
        self.setWindowTitle(translate("uForms", "QueryTool"))
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setMouseTracking(True)
        # 1st row
        self.labName = QtGui.QLabel(translate("uForms", "(Select a object)"), self)
        # 2nd row
        self.labBaseVal = QtGui.QLabel(translate("uForms", "(base)"), self)
        self.subFLayout1 = QtGui.QFormLayout()
        self.subFLayout1.addRow(translate("uForms", "Base: "), self.labBaseVal)
        # 3rd row
        self.labRotAng = QtGui.QLabel(translate("uForms", "(angle)"), self)
        self.subFLayout2 = QtGui.QFormLayout()
        self.subFLayout2.addRow(translate("uForms", "Rotation angle: "), self.labRotAng)
        # 4th row
        self.labRotAx = QtGui.QLabel(translate("uForms", "v = (x,y,z)"), self)
        self.subFLayout3 = QtGui.QFormLayout()
        self.subFLayout3.addRow(translate("uForms", "Rotation axis: "), self.labRotAx)
        # 5th row
        self.labSubObj = QtGui.QLabel(
            translate("uForms", "(Sub object property)"), self
        )
        # 6th row
        self.labBeam = QtGui.QLabel(translate("uForms", "(Beam property)"), self)
        # 7th row
        self.labProfile = QtGui.QLabel(translate("uForms", "(Profile property)"), self)
        # 8th row
        self.pushButton1 = QtGui.QPushButton(translate("uForms", "QueryObject"))
        self.pushButton1.setDefault(True)
        self.pushButton1.clicked.connect(self.onPushButton1)
        self.pushButton1.setMinimumWidth(90)
        self.cancelButton = QtGui.QPushButton(translate("uForms", "Exit"))
        self.cancelButton.clicked.connect(self.onCancel)
        self.subHLayout1 = QtGui.QHBoxLayout()
        self.subHLayout1.addWidget(self.pushButton1)
        self.subHLayout1.addWidget(self.cancelButton)
        # arrange the layout
        self.mainVLayout = QtGui.QVBoxLayout()
        self.mainVLayout.addWidget(self.labName)
        self.mainVLayout.addLayout(self.subFLayout1)
        self.mainVLayout.addLayout(self.subFLayout2)
        self.mainVLayout.addLayout(self.subFLayout3)
        self.mainVLayout.addWidget(self.labSubObj)
        self.mainVLayout.addWidget(self.labBeam)
        self.mainVLayout.addWidget(self.labProfile)
        self.mainVLayout.addLayout(self.subHLayout1)
        QtGui.QWidget.setLayout(self, self.mainVLayout)
        # now make the window visible
        self.show()

    def onPushButton1(self):
        from math import pi, degrees
        import fCmd

        try:
            obj = self.Selection.getSelection()[0]
            self.labName.setText(obj.Label)
            self.labBaseVal.setText(
                str("P = %.1f,%.1f,%.1f" % tuple(obj.Placement.Base))
            )
            self.labRotAng.setText(
                str("%.2f " % (degrees(obj.Placement.Rotation.Angle)))
            )
            ax = obj.Placement.Rotation.Axis
            self.labRotAx.setText(
                str("v = (%(x).2f,%(y).2f,%(z).2f)" % {"x": ax.x, "y": ax.y, "z": ax.z})
            )
            shapes = [
                y
                for x in self.Selection.getSelectionEx()
                for y in x.SubObjects
                if hasattr(y, "ShapeType")
            ]
            if len(shapes) == 1:
                sub = shapes[0]
                if sub.ShapeType == "Edge":
                    if sub.curvatureAt(0) == 0:
                        self.labSubObj.setText(
                            sub.ShapeType + ":\tL = %.1f mm" % sub.Length
                        )
                    else:
                        x, y, z = sub.centerOfCurvatureAt(0)
                        d = 2 / sub.curvatureAt(0)
                        self.labSubObj.setText(
                            sub.ShapeType
                            + ":\tD = %.1f mm\n\tC = %.1f,%.1f,%.1f" % (d, x, y, z)
                        )
                elif sub.ShapeType == "Face":
                    self.labSubObj.setText(sub.ShapeType + ":\tA = %.1f mm2" % sub.Area)
                elif sub.ShapeType == "Vertex":
                    self.labSubObj.setText(
                        sub.ShapeType
                        + ": pos = (%(x).1f,%(y).1f,%(z).1f)"
                        % {"x": sub.X, "y": sub.Y, "z": sub.Z}
                    )
            elif len(shapes) > 1:
                self.labSubObj.setText(
                    shapes[0].ShapeType
                    + " to "
                    + shapes[1].ShapeType
                    + ": distance = %.1f mm" % (shapes[0].distToShape(shapes[1])[0])
                )
            else:
                self.labSubObj.setText(" ")
            if len(fCmd.beams()) == 1:
                b = fCmd.beams()[0]
                self.labBeam.setText(b.Label + ":\tL=%.2f" % (b.Height))
                self.labProfile.setText("Profile: " + b.Profile)
            elif len(fCmd.beams()) > 1:
                b1, b2 = fCmd.beams()[:2]
                self.labBeam.setText(
                    b1.Label
                    + "^"
                    + b2.Label
                    + ": %.2f" % (degrees(fCmd.beamAx(b1).getAngle(fCmd.beamAx(b2))))
                )
                self.labProfile.setText("")
            else:
                self.labBeam.setText("")
                self.labProfile.setText("")
        except:
            pass

    def onCancel(self):
        self.close()


from PySide.QtCore import *
from PySide.QtGui import *
from os import listdir
from os.path import join, dirname, abspath


class rotWPForm(QDialog):  # QWidget):
    """
    Dialog to rotate the working plane about its axis.
    """

    def __init__(self, winTitle=translate("uForms", "Rotate WP"), icon="rotWP.svg"):
        super(rotWPForm, self).__init__()
        self.move(QPoint(100, 250))
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(winTitle)
        iconPath = join(dirname(abspath(__file__)), "iconz", icon)
        from PySide.QtGui import QIcon

        Icon = QIcon()
        Icon.addFile(iconPath)
        self.setWindowIcon(Icon)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.radioX = QRadioButton("X")
        self.radioX.setChecked(True)
        self.radioY = QRadioButton("Y")
        self.radioZ = QRadioButton("Z")
        self.lab1 = QLabel(translate("rotWPForm", "Angle:"))
        self.edit1 = QLineEdit("45")
        self.edit1.setAlignment(Qt.AlignCenter)
        self.edit1.setValidator(QDoubleValidator())
        self.btn1 = QPushButton(translate("rotWPForm", "Rotate working plane"))
        self.btn1.clicked.connect(self.rotate)
        self.grid.addWidget(self.radioX, 0, 0, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.radioY, 0, 1, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.radioZ, 0, 2, 1, 1, Qt.AlignCenter)
        self.grid.addWidget(self.lab1, 1, 0, 1, 1)
        self.grid.addWidget(self.edit1, 1, 1, 1, 2)
        self.grid.addWidget(self.btn1, 2, 0, 1, 3, Qt.AlignCenter)
        self.show()
        self.sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
        s = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft").GetInt(
            "gridSize"
        )
        sc = [float(x * s) for x in [1, 1, 0.2]]
        from uCmd import arrow

        self.arrow = arrow(FreeCAD.DraftWorkingPlane.getPlacement(), scale=sc, offset=s)

    def rotate(self):
        if self.radioX.isChecked():
            ax = FreeCAD.Vector(1, 0, 0)
        elif self.radioY.isChecked():
            ax = FreeCAD.Vector(0, 1, 0)
        else:
            ax = FreeCAD.Vector(0, 0, 1)
        ang = float(self.edit1.text())
        import uCmd as puc

        newpl = puc.rotWP(ax, ang)
        self.arrow.moveto(newpl)

    def closeEvent(self, event):
        self.sg.removeChild(self.arrow.node)

    def reject(self):
        self.sg.removeChild(self.arrow.node)
        self.close()

    def accept(self):
        self.rotate()


# DP_calc

import csv
from PySide.QtCore import *
from PySide.QtGui import *
from math import pi, log, radians, sin, sqrt, atan, degrees


class dpCalcDialog:
    def __init__(self):
        dialogPath = join(dirname(abspath(__file__)), "dialogz", "dp.ui")
        self.form = FreeCADGui.PySideUic.loadUi(dialogPath)
        self.form.editDensity.textChanged.connect(self.setRho)
        self.form.editViscosity.textChanged.connect(self.setMu)
        self.form.editFlow.setValidator(QDoubleValidator())
        self.form.editRough.setValidator(QDoubleValidator())
        self.form.editPressure.setValidator(QDoubleValidator())
        self.form.editTemperature.setValidator(QDoubleValidator())
        self.form.editDensity.setValidator(QDoubleValidator())
        self.form.editViscosity.setValidator(QDoubleValidator())
        self.form.radioLiquid.released.connect(self.setLiquid)
        self.form.radioGas.released.connect(self.setGas)
        self.form.butExport.clicked.connect(self.export)
        self.form.comboWhat.currentIndexChanged.connect(
            lambda: self.form.labResult.setText("---")
        )
        f = open(join(dirname(abspath(__file__)), "tablez", "roughness.csv"), "r")
        reader = csv.DictReader(f, delimiter=";")
        self.materials = [m for m in reader]
        f.close()
        self.form.comboMat.currentIndexChanged.connect(self.changeMat)
        for row in self.materials:
            self.form.comboMat.addItem(row["Material"])
        self.isLiquid = True
        self.form.radioLiquid.setEnabled(False)
        self.form.radioGas.setEnabled(False)
        self.form.editPressure.setEnabled(False)
        self.form.editTemperature.setEnabled(False)
        self.form.editDensity.setEnabled(True)
        self.form.editViscosity.setEnabled(True)
        self.form.editDensity.setText("1000")
        self.form.editViscosity.setText("1")
        self.form.labName.setText(translate("dpCalcDialog", "*** CUSTOM FLUID ***"))
        self.form.comboFluid.addItems([translate("dpCalcDialog", "<custom fluid>")])
        self.form.comboWhat.addItems(
            [
                o.Label
                for o in FreeCAD.ActiveDocument.Objects
                if hasattr(o, "PType")
                and (o.PType == "PypeBranch" or o.PType == "PypeLine")
            ]
        )
        self.checkFluid()

    def changeMat(self):
        for m in self.materials:
            if m["Material"] == self.form.comboMat.currentText():
                self.form.editRough.setText(m["e_abs"])

    def accept(self):
        Dp = Ltot = nc = 0
        elements = list()
        Q = float(self.form.editFlow.text()) / 3600
        if not self.isLiquid:
            Q = Q / self.Rho
        if self.form.comboWhat.currentText() == "<on selection>":
            elements = FreeCADGui.Selection.getSelection()
        else:
            o = FreeCAD.ActiveDocument.getObjectsByLabel(
                self.form.comboWhat.currentText()
            )[0]
            if hasattr(o, "PType") and o.PType == "PypeBranch":
                elements = [
                    FreeCAD.ActiveDocument.getObject(name)
                    for name in o.Tubes + o.Curves
                ]
            elif hasattr(o, "PType") and o.PType == "PypeLine":
                group = FreeCAD.ActiveDocument.getObjectsByLabel(o.Label + "_pieces")[0]
                elements = group.OutList
        self.form.editResults.clear()
        for o in elements:
            loss = 0
            if hasattr(o, "PType") and o.PType in ["Pipe", "Elbow", "Reduct"]:
                if o.PType in ["Pipe", "Elbow"]:
                    ID = float(o.ID) / 1000
                else:
                    ID = float(o.OD - 2 * o.thk) / 1000
                e = float(self.form.editRough.text()) * 1e-6 / ID
                v = Q / ((ID) ** 2 * pi / 4)
                Re = v * ID * self.Rho / self.Mu
                if Re <= 2300:
                    f = 64 / Re
                else:
                    f = (-1.8 * log((e / 3.7) ** 1.11 + 6.9 / Re, 10)) ** -2
                if o.PType == "Pipe":
                    L = float(o.Height) / 1000
                    Ltot += L
                    loss = v**2 / 2 * self.Rho * f * L / ID
                    self.form.editResults.append(
                        "%s\t%.1f mm\t%.1f m/s\t%.5f bar"
                        % (o.Label, ID * 1000, v, loss / 1e5)
                    )
                elif o.PType == "Elbow":
                    ang = float(o.BendAngle)
                    R = float(o.BendRadius) / 1000
                    nc += 1
                    ang = radians(ang)
                    K = (
                        f * ang * R / ID
                        + (0.10 + 2.4 * f) * sin(ang / 2)
                        + (6.6 * f * (sqrt(sin(ang / 2)) + sin(ang / 2)))
                        / ((R / ID) ** (4 * ang / pi))
                    )  # Rennels
                    loss = self.Rho * K * v**2 / 2
                    self.form.editResults.append(
                        "%s\t%.1f mm\t%.1f m/s\t%.5f bar"
                        % (o.Label, ID * 1000, v, loss / 1e5)
                    )
                elif o.PType == "Reduct":
                    ID1 = float(o.OD - o.thk * 2)
                    ID2 = float(o.OD2 - o.thk2 * 2)
                    teta = 2 * atan((ID1 - ID2) / 2.0 / float(o.Height))
                    beta = ID2 / ID1
                    if teta < pi / 4:
                        K = 0.8 * sin(teta / 2) * (1 - beta**2)
                    else:
                        K = 0.5 * sqrt(sin(teta / 2)) * (1 - beta**2)
                    loss = self.Rho * K * v**2 / 2
                    self.form.editResults.append(
                        "%s\t%.1f mm\t%.1f m/s\t%.5f bar"
                        % (o.Label, ID * 1000, v, loss / 1e5)
                    )
            elif hasattr(o, "Kv") and o.Kv > 0:
                if self.isLiquid:
                    loss = (Q * 3600 / o.Kv) ** 2 * 100000 * self.Rho / 1000
                elif (
                    self.form.comboFluid.currentText() == translate("water")
                    and not self.isLiquid
                ):
                    pass  # TODO: formula for steam
                else:
                    pass  # TODO: formula for gases
                if hasattr(o, "ID"):
                    ID = float(o.ID) / 1000
                    v = Q / (ID**2 * pi / 4)
                else:
                    v = 0
                    ID = 0
                self.form.editResults.append(
                    "%s\t%.1f mm\t%.1f m/s\t%.5f bar"
                    % (o.Label, ID * 1000, v, loss / 1e5)
                )
            Dp += loss
        if Dp > 200:
            result = " = %.3f bar" % (Dp / 100000)
        else:
            result = " = %.2e bar" % (Dp / 100000)
        self.form.labResult.setText(result)
        self.form.labLength.setText("Total length = %.3f m" % Ltot)
        self.form.labCurves.setText("Nr. of curves = %i" % nc)

    def checkFluid(self):
        T = float(self.form.editTemperature.text()) + 273.16
        P = float(self.form.editPressure.text()) * 1e5
        self.isMixture = True
        self.fluid = None
        self.form.labName.setText(translate("dpCalcDialog", "*** CUSTOM FLUID ***"))
        self.form.editDensity.setEnabled(True)
        self.form.editViscosity.setEnabled(True)
        self.form.labResult.setText("---")

    def setLiquid(self):
        if self.fluid:
            try:
                self.Rho = self.fluid.rhol
                self.Mu = self.fluid.mul
                self.form.editDensity.setText("%.4f" % self.Rho)
                self.form.editViscosity.setText(
                    "%.4f" % (self.Mu * 1000000 / self.Rho)
                )  # conversion between kinematic and dynamic!!
            except:
                QMessageBox.warning(
                    None,
                    translate("dpCalcDialog", "No data found"),
                    translate(
                        "dpCalcDialog", "It seems the fluid has not a liquid state."
                    ),
                )
                self.form.radioGas.setChecked(True)
                return
        self.isLiquid = True
        self.form.labState.setText(translate("dpCalcDialog", "*** LIQUID ***"))
        self.form.labQ.setText(translate("dpCalcDialog", "Flow (m3/h)"))
        self.form.labResult.setText("---")

    def setGas(self):
        if self.fluid:
            try:
                self.Rho = self.fluid.rhog
                self.Mu = self.fluid.mug
                self.form.editDensity.setText("%.4f" % self.Rho)
                self.form.editViscosity.setText(
                    "%.4f" % (self.Mu * 1000000 / self.Rho)
                )  # conversion between kinematic and dynamic!!
            except:
                QMessageBox.warning(
                    None,
                    translate("dpCalcDialog", "No data found"),
                    translate(
                        "dpCalcDialog", "It seems the fluid has not a gas state."
                    ),
                )
                self.form.radioLiquid.setChecked(True)
                return
        self.isLiquid = False
        self.form.labState.setText(translate("dpCalcDialog", "*** GAS/VAPOUR ***"))
        self.form.labQ.setText(translate("dpCalcDialog", "Flow (kg/h)"))
        self.form.labResult.setText("---")

    def setRho(self):
        self.Rho = float(self.form.editDensity.text())

    def setMu(self):
        self.Mu = (
            float(self.form.editViscosity.text()) * self.Rho / 1000000
        )  # conversion between kinematic and dynamic!!

    def export(self):
        rows = list()
        fields = ["Item", "ID (mm)", "v (m/s)", "Dp (bar)"]
        for row in self.form.editResults.toPlainText().split("\n"):
            record = [cell.rstrip(" mm bar m/s") for cell in row.split("\t")]
            rows.append(dict(zip(fields, record)))
        f = QFileDialog.getSaveFileName()[0]
        if f:
            dpFile = open(abspath(f), "w")
            w = csv.DictWriter(dpFile, fields, restval="-", delimiter=";")
            w.writeheader()
            w.writerows(rows)
            dpFile.close()
