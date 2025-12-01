# SPDX-License-Identifier: LGPL-3.0-or-later

__license__ = "LGPL 3"

from os.path import abspath, dirname, join

import FreeCAD
import FreeCADGui
from PySide.QtCore import *
from PySide.QtGui import *

import dodoDialogs
import fCmd
from uCmd import label3D

translate = FreeCAD.Qt.translate

FTypes = ["R", "circle", "T", "TSLOT", "H", "U", "L", "Z", "omega"]


class fillForm(dodoDialogs.protoTypeDialog):
    "dialog for fillFrame()"

    def __init__(self):
        super(fillForm, self).__init__("fillframe.ui")
        self.beam = None
        self.form.btn1.clicked.connect(self.selectAction)

    def accept(self):
        if self.beam != None and len(fCmd.edges()) > 0:
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Fill frame"))
            if self.form.radio1.isChecked():
                fCmd.placeTheBeam(self.beam, fCmd.edges()[0])
            else:
                for edge in fCmd.edges():
                    struct = FreeCAD.activeDocument().copyObject(self.beam, True)
                    fCmd.placeTheBeam(struct, edge)
                FreeCAD.activeDocument().recompute()
            FreeCAD.ActiveDocument.recompute()
            FreeCAD.activeDocument().commitTransaction()

    def selectAction(self):
        if len(fCmd.beams()) > 0:
            self.beam = fCmd.beams()[0]
            self.form.label.setText(self.beam.Label + ":" + self.beam.Profile)
            FreeCADGui.Selection.removeSelection(self.beam)


class extendForm(dodoDialogs.protoTypeDialog):
    "dialog for fCmd.extendTheBeam()"

    def __init__(self):
        super(extendForm, self).__init__("extend.ui")
        selex = FreeCADGui.Selection.getSelectionEx()
        self.form.btn1.clicked.connect(self.selectAction)
        if len(selex):
            self.target = selex[0].SubObjects[0]
            self.form.label.setText(selex[0].Object.Label + ":" + self.target.ShapeType)
            FreeCADGui.Selection.removeSelection(selex[0].Object)
        else:
            self.target = None

    def selectAction(self):
        selex = FreeCADGui.Selection.getSelectionEx()
        if len(selex[0].SubObjects) > 0 and hasattr(selex[0].SubObjects[0], "ShapeType"):
            self.target = selex[0].SubObjects[0]
            self.form.label.setText(selex[0].Object.Label + ":" + self.target.ShapeType)
            FreeCADGui.Selection.clearSelection()

    def accept(self):  # extend
        if self.target != None and len(fCmd.beams()) > 0:
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Extend beam"))
            for beam in fCmd.beams():
                fCmd.extendTheBeam(beam, self.target)
            FreeCAD.activeDocument().recompute()
            FreeCAD.activeDocument().commitTransaction()


class stretchForm(dodoDialogs.protoTypeDialog):
    """dialog for stretchTheBeam()
    [Get Length] measures the min. distance of the selected objects or
      the length of the selected edge or
      the Height of the selected beam
    [ Stretch ] changes the Height of the selected beams
    """

    def __init__(self):
        self.L = None
        super(stretchForm, self).__init__("beamstretch.ui")
        self.form.edit1.setValidator(QDoubleValidator())
        self.form.edit1.editingFinished.connect(self.edit12L)
        self.form.btn1.clicked.connect(self.selectAction)
        self.form.slider.setMinimum(-100)
        self.form.slider.setMaximum(100)
        self.form.slider.setValue(0)
        self.form.slider.valueChanged.connect(self.changeL)
        self.labTail = None

    def edit12L(self):
        if self.form.edit1.text():
            self.L = float(self.form.edit1.text())
            self.form.slider.setValue(0)

    def changeL(self):
        if self.L:
            ext = self.L * (1 + self.form.slider.value() / 100.0)
            self.form.edit1.setText("%.3f" % ext)

    def selectAction(self):
        if self.labTail:
            self.labTail.removeLabel()
            self.labTail = None
        self.L = fCmd.getDistance()
        if self.L:
            self.form.edit1.setText("%.3f" % self.L)
        elif fCmd.beams():
            beam = fCmd.beams()[0]
            self.L = float(beam.Height)
            self.form.edit1.setText("%.3f" % self.L)
        else:
            self.form.edit1.setText("")
        self.form.slider.setValue(0)
        # self.writeTail()

    # def writeTail(self):
    # if fCmd.beams():
    # beam=fCmd.beams()[0]
    # from uCmd import label3D
    # self.labTail=label3D(pl=beam.Placement, text='____TAIL')
    def accept(self):
        if self.labTail:
            self.labTail.removeLabel()
            self.labTail = None
        self.L = fCmd.getDistance()
        if self.form.edit1.text():
            length = float(self.form.edit1.text())
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Stretch beam"))
            for beam in fCmd.beams():
                delta = float(beam.Height) - length
                fCmd.stretchTheBeam(beam, length)
                if self.form.tail.isChecked():
                    disp = fCmd.beamAx(beam).multiply(delta)
                    beam.Placement.move(disp)
                elif self.form.both.isChecked():
                    disp = fCmd.beamAx(beam).multiply(delta / 2.0)
                    beam.Placement.move(disp)
            FreeCAD.activeDocument().recompute()
            FreeCAD.activeDocument().commitTransaction()

    def reject(self):  # redefined to remove label from the scene
        if self.labTail:
            self.labTail.removeLabel()
        super(stretchForm, self).reject()

    def mouseActionB1(self, CtrlAltShift):
        v = FreeCADGui.ActiveDocument.ActiveView
        i = v.getObjectInfo(v.getCursorPos())
        if i:
            labText = i["Object"]
            obj = FreeCAD.ActiveDocument.getObject(i["Object"])
            if hasattr(obj, "Height"):
                if self.labTail:
                    self.labTail.removeLabel()
                self.labTail = label3D(pl=obj.Placement, text="____TAIL")
            else:
                if self.labTail:
                    self.labTail.removeLabel()
                self.labTail = label3D(pl=FreeCAD.Placement(), text="")
        else:
            if self.labTail:
                self.labTail.removeLabel()
            self.labTail = label3D(pl=FreeCAD.Placement(), text="")


class translateForm(dodoDialogs.protoTypeDialog):
    "dialog for moving blocks"

    def __init__(self):
        super(translateForm, self).__init__("beamshift.ui")
        for e in [
            self.form.edit1,
            self.form.edit2,
            self.form.edit3,
            self.form.edit4,
            self.form.edit5,
        ]:
            e.setValidator(QDoubleValidator())
        self.form.btn1.clicked.connect(self.selectAction)
        self.arrow = None

    def getDistance(self):
        self.deleteArrow()
        roundDigits = 3
        shapes = [
            y
            for x in FreeCADGui.Selection.getSelectionEx()
            for y in x.SubObjects
            if hasattr(y, "ShapeType")
        ][:2]
        if len(shapes) > 1:  # if at least 2 shapes selected....
            base, target = shapes[:2]
            disp = None
            if base.ShapeType == target.ShapeType == "Vertex":
                disp = target.Point - base.Point
            elif base.ShapeType == target.ShapeType == "Edge":
                if base.curvatureAt(0):
                    P1 = base.centerOfCurvatureAt(0)
                else:
                    P1 = base.CenterOfMass
                if target.curvatureAt(0):
                    P2 = target.centerOfCurvatureAt(0)
                else:
                    P2 = target.CenterOfMass
                disp = P2 - P1
            elif set([base.ShapeType, target.ShapeType]) == {"Vertex", "Edge"}:
                P = list()
                i = 0
                for o in [base, target]:
                    if o.ShapeType == "Vertex":
                        P.append(o.Point)
                    elif o.curvatureAt(0):
                        P.append(o.centerOfCurvatureAt(0))
                    else:
                        return
                    i += 1
                disp = P[1] - P[0]
            elif base.ShapeType == "Vertex" and target.ShapeType == "Face":
                disp = (
                    fCmd.intersectionPlane(base.Point, target.normalAt(0, 0), target) - base.Point
                )
            elif base.ShapeType == "Face" and target.ShapeType == "Vertex":
                disp = target.Point - fCmd.intersectionPlane(
                    target.Point, base.normalAt(0, 0), base
                )
                disp = P[1] - P[0]
            if disp != None:
                self.form.edit4.setText(str(disp.Length))
                self.form.edit5.setText("1")
                disp.normalize()
                dx, dy, dz = list(disp)
                self.form.edit1.setText(str(round(dx, roundDigits)))
                self.form.edit2.setText(str(round(dy, roundDigits)))
                self.form.edit3.setText(str(round(dz, roundDigits)))
                FreeCADGui.Selection.clearSelection()

    def getLength(self):
        roundDigits = 3
        if len(fCmd.edges()) > 0:
            edge = fCmd.edges()[0]
            self.form.edit4.setText(str(edge.Length))
            self.form.edit5.setText("1")
            dx, dy, dz = list(edge.tangentAt(0))
            self.form.edit1.setText(str(round(dx, roundDigits)))
            self.form.edit2.setText(str(round(dy, roundDigits)))
            self.form.edit3.setText(str(round(dz, roundDigits)))
            self.deleteArrow()
            from uCmd import arrow

            where = FreeCAD.Placement()
            where.Base = edge.valueAt(0)
            where.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), edge.tangentAt(0))
            # obj=fCmd.edgeName[0] #TARGET [working]: make "where" deal with App::Parts
            # if fCmd.isPartOfPart(obj):
            # part=fCmd.isPartOfPart(obj)
            # where=part.Placement.multiply(where)
            size = [edge.Length / 20.0, edge.Length / 10.0, edge.Length / 20.0]
            self.arrow = arrow(pl=where, scale=size, offset=edge.Length / 2.0)
            FreeCADGui.Selection.clearSelection()

    def selectAction(self):
        shapes = [
            y
            for x in FreeCADGui.Selection.getSelectionEx()
            for y in x.SubObjects
            if hasattr(y, "ShapeType")
        ][:2]
        if len(shapes) > 1:
            self.getDistance()
        elif len(fCmd.edges()) > 0:
            self.getLength()

    def accept(self):  # translate
        self.deleteArrow()
        scale = float(self.form.edit4.text()) / float(self.form.edit5.text())
        disp = FreeCAD.Vector(
            float(self.form.edit1.text()) * self.form.cbX.isChecked(),
            float(self.form.edit2.text()) * self.form.cbY.isChecked(),
            float(self.form.edit3.text()) * self.form.cbZ.isChecked(),
        ).scale(scale, scale, scale)
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Translate"))
        for o in set(FreeCADGui.Selection.getSelection()):
            if self.form.cbCopy.isChecked():
                for i in range(self.form.spinBox.value()):
                    FreeCAD.activeDocument().copyObject(o, True).Placement.move(disp * (i + 1))
            else:
                o.Placement.move(disp)
        FreeCAD.activeDocument().recompute()
        FreeCAD.activeDocument().commitTransaction()

    def deleteArrow(self):
        if self.arrow:
            self.arrow.closeArrow()  # FreeCADGui.ActiveDocument.ActiveView.getSceneGraph().removeChild(self.arrow.node)
        self.arrow = None

    def reject(self):  # redefined to remove arrow from scene
        self.deleteArrow()
        super(translateForm, self).reject()


class alignForm(dodoDialogs.protoTypeDialog):
    "dialog to flush faces"

    def __init__(self):
        super(alignForm, self).__init__("align.ui")
        self.faceRef = None
        self.selectAction()
        self.form.btn1.clicked.connect(self.selectAction)
        self.form.btnXY.clicked.connect(lambda: self.refPlane(FreeCAD.Vector(0, 0, 1)))
        self.form.btnXZ.clicked.connect(lambda: self.refPlane(FreeCAD.Vector(0, 1, 0)))
        self.form.btnYZ.clicked.connect(lambda: self.refPlane(FreeCAD.Vector(1, 0, 0)))
        self.form.X.setValidator(QDoubleValidator())
        self.form.btnNorm.clicked.connect(
            lambda: self.refPlane(
                FreeCAD.Vector(
                    float(self.form.X.text()), float(self.form.Y.text()), float(self.form.Z.text())
                )
            )
        )
        self.form.Y.setValidator(QDoubleValidator())
        self.form.Z.setValidator(QDoubleValidator())

    def selectAction(self):
        if fCmd.faces():
            a = [
                (o, fCmd.faces([o])[0])
                for o in FreeCADGui.Selection.getSelectionEx()
                if fCmd.faces([o])
            ][0]
            self.faceRef = a[1]
            self.form.label.setText(a[0].Object.Label + ":Face")
            FreeCADGui.Selection.clearSelection()

    def refPlane(self, norm):
        self.faceRef = norm
        if norm == FreeCAD.Vector(0, 0, 1):
            self.form.label.setText("plane XY")
        elif norm == FreeCAD.Vector(0, 1, 0):
            self.form.label.setText("plane XZ")
        elif norm == FreeCAD.Vector(1, 0, 0):
            self.form.label.setText("plane YZ")
        else:
            self.form.label.setText("normal: X=%.2f Y=%.2f Z=%.2f" % (norm.x, norm.y, norm.z))
        for edit in [self.form.X, self.form.Y, self.form.Z]:
            edit.clear()

    def accept(self):
        faces = fCmd.faces()
        objs = FreeCADGui.Selection.getSelection()  # beams=fCmd.beams()
        if len(faces) == len(objs) > 0 and self.faceRef:
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Align Flange"))
            if self.form.cbInvert.isChecked():
                for i in range(len(objs)):
                    fCmd.rotTheBeam(objs[i], self.faceRef, faces[i], True)
            else:
                for i in range(len(objs)):
                    fCmd.rotTheBeam(objs[i], self.faceRef, faces[i])
            FreeCAD.activeDocument().recompute()
            FreeCAD.activeDocument().commitTransaction()


class rotateAroundForm(dodoDialogs.protoTypeDialog):
    """
    Dialog for rotateTheBeamAround().
    It allows to rotate one object around one edge or the axis of a circular edge (or one principal axis.)
    """

    def __init__(self):
        super(rotateAroundForm, self).__init__("rotAround.ui")
        self.form.edit1.setValidator(QDoubleValidator())
        self.form.btn1.clicked.connect(self.selectAction)
        self.form.btn2.clicked.connect(self.reverse)
        self.form.btnX.clicked.connect(lambda: self.getPrincipalAx("X"))
        self.form.btnY.clicked.connect(lambda: self.getPrincipalAx("Y"))
        self.form.btnZ.clicked.connect(lambda: self.getPrincipalAx("Z"))
        self.form.dial.valueChanged.connect(
            lambda: self.form.edit1.setText(str(self.form.dial.value()))
        )
        self.form.edit1.editingFinished.connect(
            lambda: self.form.dial.setValue(int(self.form.edit1.text()))
        )
        self.Axis = None
        self.arrow = None
        self.selectAction()

    def accept(
        self, ang=None
    ):  # TARGET [working]: not correct if objects belong to different App::Part
        if not ang:
            ang = float(self.form.edit1.text())
        self.deleteArrow()
        objects = FreeCADGui.Selection.getSelection()
        if objects and self.Axis:
            FreeCAD.activeDocument().openTransaction(
                translate("Transaction", "Rotate The Beam Around")
            )
            for o in objects:
                if self.form.copyCB.isChecked():
                    FreeCAD.activeDocument().copyObject(o, True)
                fCmd.rotateTheBeamAround(o, self.Axis, ang)
            FreeCAD.ActiveDocument.commitTransaction()

    def reverse(self):
        ang = float(self.form.edit1.text()) * -1
        self.form.edit1.setText("%.0f" % ang)
        self.form.dial.setValue(int(self.form.edit1.text()))
        self.accept(ang * 2)

    def getPrincipalAx(self, ax="Z"):
        self.deleteArrow()
        from Part import Edge, Line

        O = FreeCAD.Vector()
        l = Line(O, FreeCAD.Vector(0, 0, 1000))
        if ax == "X":
            l = Line(O, FreeCAD.Vector(1000, 0, 0))
        elif ax == "Y":
            l = Line(O, FreeCAD.Vector(0, 1000, 0))
        self.Axis = Edge(l)
        self.form.lab1.setText("Principal: " + ax)

    def selectAction(self):
        edged = [objex for objex in FreeCADGui.Selection.getSelectionEx() if fCmd.edges([objex])]
        if edged:
            self.Axis = fCmd.edges([edged[0]])[0]
            self.deleteArrow()
            from uCmd import arrow

            where = FreeCAD.Placement()
            where.Base = self.Axis.valueAt(self.Axis.LastParameter)
            where.Rotation = FreeCAD.Rotation(
                FreeCAD.Vector(0, 0, 1), self.Axis.tangentAt(self.Axis.LastParameter)
            )
            obj = edged[0].Object  # TARGET [solved]: make "where" deal with App::Parts
            if fCmd.isPartOfPart(obj):
                part = fCmd.isPartOfPart(obj)
                where = part.Placement.multiply(where)
            size = [self.Axis.Length / 20.0, self.Axis.Length / 10.0, self.Axis.Length / 20.0]
            self.arrow = arrow(pl=where, scale=size, offset=self.Axis.Length / 10.0)
            if self.Axis.curvatureAt(0):
                O = self.Axis.centerOfCurvatureAt(0)
                n = self.Axis.tangentAt(0).cross(self.Axis.normalAt(0))
                from Part import Edge, Line

                self.Axis = Edge(Line(FreeCAD.Vector(O), FreeCAD.Vector(O + n)))
            self.form.lab1.setText(edged[0].Object.Label + ": edge")

    def deleteArrow(self):
        if self.arrow:
            self.arrow.closeArrow()
        self.arrow = None

    def reject(self):  # redefined to remove arrow from scene
        self.deleteArrow()
        super(rotateAroundForm, self).reject()


###### PROFILE EDITOR ########

import fFeatures

# the icons
pixs = [pixSquare, pixT, pixU, pixH, pixL, pixZ, pixOmega, pixCircle] = [
    QPixmap(join(dirname(abspath(__file__)), "iconz", "sectionz", fileName))
    for fileName in [
        "square.png",
        "T.png",
        "U.png",
        "H.png",
        "L.png",
        "Z.png",
        "omega.png",
        "circle.png",
    ]
]


class profEdit(dodoDialogs.protoTypeDialog):
    def __init__(self):
        super(profEdit, self).__init__("sections.ui")
        self.setProfile("square")
        self.form.editB.editingFinished.connect(
            lambda: self.form.editD.setText(self.form.editB.text())
        )
        self.form.editT2.editingFinished.connect(
            lambda: self.form.editT3.setText(self.form.editT2.text())
        )
        self.form.tbSquare.clicked.connect(lambda: self.setProfile("square"))
        self.form.tbCircle.clicked.connect(lambda: self.setProfile("circle"))
        self.form.tbT.clicked.connect(lambda: self.setProfile("T"))
        self.form.tbU.clicked.connect(lambda: self.setProfile("U"))
        self.form.tbH.clicked.connect(lambda: self.setProfile("H"))
        self.form.tbL.clicked.connect(lambda: self.setProfile("L"))
        self.form.tbZ.clicked.connect(lambda: self.setProfile("Z"))
        self.form.btn1.clicked.connect(self.apply)
        self.form.btn2.clicked.connect(lambda: self.shiftProfile(None))
        self.form.tbOmega.clicked.connect(lambda: self.setProfile("omega"))
        for z in list(
            zip(
                pixs,
                [
                    self.form.tbSquare,
                    self.form.tbT,
                    self.form.tbU,
                    self.form.tbH,
                    self.form.tbL,
                    self.form.tbZ,
                    self.form.tbOmega,
                    self.form.tbCircle,
                ],
            )
        ):
            icon = QIcon()
            icon.addPixmap(z[0], QIcon.Normal, QIcon.Off)
            z[1].setIcon(icon)
        # TODO: translation

    def setProfile(self, typeS):
        # NOTE: the self.label is used on the `addObject()` method as therefore is assigned
        # tot the internal name of the object, to translate the label is needed to
        # assign the translated string to `obj.Label`.
        if typeS == "square":
            self.form.labImg.setPixmap(pixSquare)
            self.type = "R"
            self.label = "Square"
        elif typeS == "T":
            self.form.labImg.setPixmap(pixT)
            self.type = "T"
            self.label = "T-profile"
        elif typeS == "TSLOT":
            self.form.labImg.setPixmap(pixT)
            self.type = "TSLOT"
            self.label = "T-slot"
        elif typeS == "U":
            self.form.labImg.setPixmap(pixU)
            self.type = "U"
            self.label = "U-profile"
        elif typeS == "H":
            self.form.labImg.setPixmap(pixH)
            self.type = "H"
            self.label = "H-profile"
        elif typeS == "L":
            self.form.labImg.setPixmap(pixL)
            self.type = "L"
            self.label = "L-profile"
        elif typeS == "Z":
            self.form.labImg.setPixmap(pixZ)
            self.type = "Z"
            self.label = "Z-profile"
        elif typeS == "omega":
            self.form.labImg.setPixmap(pixOmega)
            self.type = "omega"
            self.label = "Omega-profile"
        elif typeS == "circle":
            self.form.labImg.setPixmap(pixCircle)
            self.type = "circle"
            self.label = "Circle-profile"

    def accept(self):
        D, H, B, t1, t2, t3 = (
            float(self.form.editD.text()),
            float(self.form.editH.text()),
            float(self.form.editB.text()),
            float(self.form.editT1.text()),
            float(self.form.editT2.text()),
            float(self.form.editT3.text()),
        )
        if not self.form.lineEdit.text():
            label = self.label
        else:
            label = self.form.lineEdit.text()
        if FreeCAD.ActiveDocument:
            FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert profile"))
            if self.type == "R":
                if not self.form.cbFull.isChecked() and t2 < H / 2 and t1 < B / 2:
                    sect = fFeatures.doProfile("RH", label, [B, H, t1, t2])
                else:
                    sect = fFeatures.doProfile("R", label, [B, H])
            elif self.type == "H":
                sect = fFeatures.doProfile(self.type, label, [B, H, D, t1, t2, t3])
            elif self.type == "U" and t2 < H and t1 < B / 2:
                sect = fFeatures.doProfile(self.type, label, [B, H, D, t1, t2, t3])
            elif self.type == "L" and t2 < H and t1 < B:
                sect = fFeatures.doProfile(self.type, label, [B, H, t1, t2])
            elif self.type == "T" and t2 < H and t1 < B:
                sect = fFeatures.doProfile(self.type, label, [B, H, t1, t2])
            elif self.type == "Z" and t2 < H / 2 and t1 < B * 2:
                sect = fFeatures.doProfile(self.type, label, [B, H, t1, t2])
            elif self.type == "omega":
                sect = fFeatures.doProfile(self.type, label, [B, H, D, t1, t2, t3])
            elif self.type == "circle":
                if self.form.cbFull.isChecked():
                    sect = fFeatures.doProfile(self.type, label, [D, 0])
                else:
                    sect = fFeatures.doProfile(self.type, label, [D, t1])
            FreeCAD.ActiveDocument.recompute()
            self.shiftProfile(sect)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.ActiveDocument.recompute()
            FreeCAD.ActiveDocument.recompute()

    def apply(self):
        D, H, B, t1, t2, t3 = (
            float(self.form.editD.text()),
            float(self.form.editH.text()),
            float(self.form.editB.text()),
            float(self.form.editT1.text()),
            float(self.form.editT2.text()),
            float(self.form.editT3.text()),
        )
        sel = FreeCADGui.Selection.getSelection()
        if sel:
            obj = sel[0]
            if hasattr(obj, "Shape") and obj.Shape.ShapeType in ("Face", "Shell"):
                FreeCAD.activeDocument().openTransaction(translate("Transaction", "Modify profile"))
                if self.form.lineEdit.text():
                    obj.Label = self.form.lineEdit.text()
                if hasattr(obj, "H"):
                    obj.H = H
                if hasattr(obj, "W"):
                    obj.W = B
                if hasattr(obj, "D"):
                    obj.D = D
                if hasattr(obj, "t1"):
                    obj.t1 = t1
                if hasattr(obj, "t2"):
                    obj.t2 = t2
                if hasattr(obj, "t3"):
                    obj.t3 = t3
                FreeCAD.ActiveDocument.commitTransaction()
                # self.shiftProfile(obj)
            FreeCAD.ActiveDocument.recompute()

    def mouseActionB1(self, CtrlAltShift):
        # self.form.labSelect.setText('<selection>')
        v = FreeCADGui.ActiveDocument.ActiveView
        i = v.getObjectInfo(v.getCursorPos())
        if i:
            labText = i["Object"]
            obj = FreeCAD.ActiveDocument.getObject(i["Object"])
            if hasattr(obj, "FType") and obj.FType in FTypes:
                if obj.FType == "R":
                    self.setProfile("R")
                elif obj.FType == "circle":
                    self.setProfile("circle")
                elif obj.FType == "T":
                    self.setProfile("T")
                elif obj.FType == "H":
                    self.setProfile("H")
                elif obj.FType == "L":
                    self.setProfile("L")
                elif obj.FType == "U":
                    self.setProfile("U")
                elif obj.FType == "Z":
                    self.setProfile("Z")
                elif obj.FType == "omega":
                    self.setProfile("omega")
                ###############
                self.form.lineEdit.setText(obj.Label)
                if hasattr(obj, "H"):
                    self.form.editH.setText(str(float(obj.H.Value)))
                else:
                    self.form.editH.setText("0")
                if hasattr(obj, "W"):
                    self.form.editB.setText(str(float(obj.W)))
                else:
                    self.form.editW.setText("0")
                if hasattr(obj, "D"):
                    self.form.editD.setText(str(float(obj.D)))
                else:
                    self.form.editD.setText("0")
                if hasattr(obj, "t1"):
                    self.form.editT1.setText(str(float(obj.t1)))
                else:
                    self.form.editT1.setText("0")
                if hasattr(obj, "t2"):
                    self.form.editT2.setText(str(float(obj.t2)))
                else:
                    self.form.editT2.setText("0")
                if hasattr(obj, "t3"):
                    self.form.editT3.setText(str(float(obj.t3)))
                else:
                    self.form.editT3.setText("0")
                # self.form.labSelect.setText(obj.Label)
        else:
            self.form.editH.setText("80")
            self.form.editB.setText("45")
            self.form.editD.setText("45")
            self.form.editT1.setText("5")
            self.form.editT2.setText("5")
            self.form.editT3.setText("5")
            # self.form.labSelect.setText('')
            self.form.lineEdit.setText("")

    def shiftProfile(self, sect=None):
        if not sect:
            sel = FreeCADGui.Selection.getSelection()
            if sel and hasattr(sel[0], "FType"):
                sect = sel[0]
        if sect:
            sect.Placement.move(sect.Shape.CenterOfMass.negative())
            FreeCAD.ActiveDocument.recompute()
            FreeCAD.activeDocument().openTransaction(translate("profEdit", "Shift profile"))
            B = sect.Shape.BoundBox
            O = sect.Shape.CenterOfMass
            N = FreeCAD.Vector(0, O.y - B.YMin, 0)
            S = FreeCAD.Vector(0, O.y - B.YMax, 0)
            E = FreeCAD.Vector(O.x - B.XMin, 0, 0)
            W = FreeCAD.Vector(O.x - B.XMax, 0, 0)
            delta = FreeCAD.Vector()
            if self.form.rbN.isChecked():
                delta = S
            elif self.form.rbS.isChecked():
                delta = N
            elif self.form.rbE.isChecked():
                delta = W
            elif self.form.rbW.isChecked():
                delta = E
            elif self.form.rbNE.isChecked():
                delta = S.add(W)
            elif self.form.rbNW.isChecked():
                delta = S.add(E)
            elif self.form.rbSE.isChecked():
                delta = N.add(W)
            elif self.form.rbSW.isChecked():
                delta = N.add(E)
            elif self.form.rbC.isChecked():
                delta = O * -1
            sect.Placement.move(delta)
            FreeCAD.ActiveDocument.commitTransaction()
