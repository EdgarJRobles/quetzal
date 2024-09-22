# (c) 2019 R. T. LGPL: part of dodo tools w.b. for FreeCAD

__title__ = "frameTools objects"
__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"

import FreeCAD, FreeCADGui, Part, csv, fCmd, pCmd, ArchProfile
from Arch import makeStructure
from Arch import makeProfile
from Draft import makeCircle
from PySide2.QtCore import *
from PySide2.QtGui import *
from os import listdir
from os.path import join, dirname, abspath
from math import degrees
from uCmd import label3D
from PySide2.QtCore import QT_TRANSLATE_NOOP
from PySide2.QtWidgets import QDialog
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QListWidget
from PySide2.QtWidgets import QCheckBox
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QComboBox
from PySide2.QtWidgets import QHBoxLayout
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtWidgets import QPushButton
# from DraftGui import translate
from draftutils.translate import translate

################ FUNCTIONS ###########################


def newProfile(prop):
    """
    Auxiliary function to create profiles with ArchProfiles
    """
    if prop["stype"] == "C":
        profile = makeCircle(float(prop["H"]))
    else:
        if int(FreeCAD.Version()[0]) >=1:
            profile=makeProfile([0,"SECTION",prop["SSize"] + "-000",prop["stype"],float(prop["W"]),float(prop["H"]),float(prop["ta"]),float(prop["tf"]),])
        else:
            profile=ArchProfile.makeProfile([0,"SECTION",prop["SSize"] + "-000",prop["stype"],float(prop["W"]),float(prop["H"]),float(prop["ta"]),float(prop["tf"]),])
    return profile


def indexEdge(edge, listedges):
    """
    Auxiliary function to find the index of an edge
    """
    for e in listedges:
        if e.isSame(edge):
            return listedges.index(e)
    return None


def findFB(beamName=None, baseName=None):
    Branches = [
        o.Name
        for o in FreeCAD.ActiveDocument.Objects
        if hasattr(o, "FType") and o.FType == "FrameBranch"
    ]
    if beamName:
        for name in Branches:
            if (
                beamName in FreeCAD.ActiveDocument.getObject(name).Beams
            ):  # if beam.Name in activeFB.Beams:
                return FreeCAD.ActiveDocument.getObject(name)
    elif baseName:
        for name in Branches:
            if (
                baseName == FreeCAD.ActiveDocument.getObject(name).Base.Name
            ):  # if beam.Name in activeFB.Beams:
                return FreeCAD.ActiveDocument.getObject(name)
    return None


def refresh():
    for b in [
        o
        for o in FreeCAD.ActiveDocument.Objects
        if hasattr(o, "FType") and o.FType == "FrameBranch"
    ]:
        b.touch()
    FreeCAD.ActiveDocument.recompute()
    FreeCAD.ActiveDocument.recompute()


################ DIALOGS #############################


class frameLineForm(QDialog):
    """
    Dialog for fFeatures management.
    From this you can:
    - insert a new Frameline object in the model,
    - select its profile,
    - select its path,
    - redraw it,
    - clear it.
    To select profiles, the 2D objects msut be included insied the "Profiles_set"
    group, either created manually or automatically by "Insert Std. Section"
    """

    def __init__(self, winTitle="FrameLine Manager", icon="frameline.svg"):
        super(frameLineForm, self).__init__()
        self.move(QPoint(100, 250))
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(winTitle)
        from PySide2.QtGui import QIcon

        Icon = QIcon()
        iconPath = join(dirname(abspath(__file__)), "iconz", icon)
        Icon.addFile(iconPath)
        self.setWindowIcon(Icon)
        self.mainHL = QHBoxLayout()
        self.setLayout(self.mainHL)
        self.firstCol = QWidget()
        self.firstCol.setLayout(QVBoxLayout())
        self.lab1 = QLabel("  Profiles:")
        self.firstCol.layout().addWidget(self.lab1)
        self.sectList = QListWidget()
        self.sectList.setMaximumWidth(120)
        self.updateSections()
        self.firstCol.layout().addWidget(self.sectList)
        self.cb1 = QCheckBox(" Copy profile")
        self.cb1.setChecked(True)
        self.cb2 = QCheckBox(" Move to origin")
        self.cb2.setChecked(True)
        self.radios = QWidget()
        self.radios.setLayout(QFormLayout())
        self.radios.layout().setAlignment(Qt.AlignHCenter)
        self.radios.layout().addRow(self.cb1)
        self.radios.layout().addRow(self.cb2)
        self.firstCol.layout().addWidget(self.radios)
        self.mainHL.addWidget(self.firstCol)
        self.secondCol = QWidget()
        self.secondCol.setLayout(QVBoxLayout())
        self.current = None
        self.combo = QComboBox()
        self.combo.addItem("<new>")
        # self.combo.activated[str].connect(self.setCurrent)
        try:
            self.combo.addItems(
                [
                    o.Label
                    for o in FreeCAD.activeDocument().Objects
                    if hasattr(o, "FType") and o.FType == "FrameLine"
                ]
            )
        except:
            None
        self.combo.setMaximumWidth(100)
        self.combo.currentIndexChanged.connect(self.setCurrentFL)
        if FreeCAD.__activeFrameLine__ and FreeCAD.__activeFrameLine__ in [
            self.combo.itemText(i) for i in range(self.combo.count())
        ]:
            self.combo.setCurrentIndex(self.combo.findText(FreeCAD.__activeFrameLine__))
        self.secondCol.layout().addWidget(self.combo)
        self.btn0 = QPushButton("Insert")
        self.btn0.setMaximumWidth(100)
        self.secondCol.layout().addWidget(self.btn0)
        self.btn0.clicked.connect(self.insert)
        self.edit1 = QLineEdit()
        self.edit1.setPlaceholderText("<name>")
        self.edit1.setAlignment(Qt.AlignHCenter)
        self.edit1.setMaximumWidth(100)
        self.secondCol.layout().addWidget(self.edit1)
        self.btn1 = QPushButton("Redraw")
        self.btn1.clicked.connect(self.redraw)
        self.btn1.setMaximumWidth(100)
        self.secondCol.layout().addWidget(self.btn1)
        self.btn2 = QPushButton("Get Path")
        self.btn2.clicked.connect(self.getPath)
        self.btn2.setMaximumWidth(100)
        self.secondCol.layout().addWidget(self.btn2)
        self.btn3 = QPushButton("Get Profile")
        self.btn3.clicked.connect(self.getProfile)
        self.btn3.setMaximumWidth(100)
        self.secondCol.layout().addWidget(self.btn3)
        self.btn4 = QPushButton("Clear")
        self.btn4.clicked.connect(self.clear)
        self.btn4.setMaximumWidth(100)
        self.secondCol.layout().addWidget(self.btn4)
        self.mainHL.addWidget(self.secondCol)
        self.show()

    def setCurrentFL(self, FLName=None):
        if self.combo.currentText() not in ["<none>", "<new>"]:
            FreeCAD.__activeFrameLine__ = self.combo.currentText()
            self.current = FreeCAD.ActiveDocument.getObjectsByLabel(
                self.combo.currentText()
            )[0]
            FreeCAD.Console.PrintMessage(
                "current FrameLine = " + self.current.Label + "\n"
            )
            if self.current.Profile:
                FreeCAD.Console.PrintMessage(
                    "Profile: %s\n" % self.current.Profile.Label
                )
            else:
                FreeCAD.Console.PrintMessage("Profile not defined\n")
            if self.current.Base:
                FreeCAD.Console.PrintMessage("Path: %s\n" % self.current.Base.Label)
            else:
                FreeCAD.Console.PrintMessage("Path not defined\n")
        else:
            FreeCAD.__activeFrameLine__ = None
            self.current = None
            FreeCAD.Console.PrintMessage("current FrameLine = None\n")

    def updateSections(self):
        self.sectList.clear()
        result = FreeCAD.ActiveDocument.findObjects(
            "App::DocumentObjectGroup", "Profiles_set"
        )
        if result:
            self.sectList.addItems(
                [
                    o.Label
                    for o in result[0].OutList
                    if hasattr(o, "Shape")
                    and (
                        (type(o.Shape) == Part.Wire and o.Shape.isClosed())
                        or (
                            type(o.Shape) == Part.Face
                            and type(o.Shape.Surface) == Part.Plane
                        )
                    )
                ]
            )
            if self.sectList.count():
                self.sectList.setCurrentRow(0)
        else:
            FreeCAD.Console.PrintError(
                "No set of profiles in this document.\nCreate the sections first.\n"
            )

    def setCurrent(self, flname):
        if flname != "<new>":
            self.current = FreeCAD.ActiveDocument.getObjectsByLabel(flname)[0]
            FreeCAD.Console.PrintMessage(
                "current FrameLine = " + self.current.Label + "\n"
            )
        else:
            self.current = None
            FreeCAD.Console.PrintMessage("current FrameLine = None\n")

    def insert(self):
        from pCmd import moveToPyLi

        if self.combo.currentText() == "<new>":
            name = self.edit1.text()
            if not name:
                name = "Telaio"
            a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
            FrameLine(a)
            a.ViewObject.Proxy = 0
            self.combo.addItem(a.Label)
            self.combo.setCurrentIndex(self.combo.count() - 1)
            if self.sectList.selectedItems():
                self.getProfile()
        elif self.sectList.selectedItems():
            prof = FreeCAD.ActiveDocument.getObjectsByLabel(
                self.sectList.selectedItems()[0].text()
            )[0]
            for e in fCmd.edges():
                if self.cb1.isChecked():
                    s = makeStructure(FreeCAD.ActiveDocument.copyObject(prof))
                else:
                    s = makeStructure(prof)
                fCmd.placeTheBeam(s, e)
                moveToPyLi(s, self.current.Name)
            FreeCAD.ActiveDocument.recompute()

    def redraw(self):
        if self.current and self.current.Profile and self.current.Base:
            if self.cb1.isChecked():
                self.current.Proxy.update(self.current)
            else:
                self.current.Proxy.update(self.current, copyProfile=False)
            self.updateSections()
        else:
            FreeCAD.Console.PrintError("Select a Path and a Profile before\n")

    def clear(self):
        if self.current:
            self.current.Proxy.purge(self.current)
            self.updateSections()

    def getPath(self):
        if self.current:
            sel = FreeCADGui.Selection.getSelection()
            if sel:
                base = sel[0]
                if base.TypeId in [
                    "Part::Part2DObjectPython",
                    "Sketcher::SketchObject",
                ]:
                    self.current.Base = base
                    FreeCAD.Console.PrintWarning(
                        self.current.Label
                        + " base set to "
                        + base.TypeId.split("::")[1]
                        + ".\n"
                    )
                else:
                    FreeCAD.Console.PrintError("Not a Wire nor Sketch\n")
            else:
                self.current.Base = None
                FreeCAD.Console.PrintWarning(
                    self.current.Label + " base set to None.\n"
                )

    def getProfile(self):
        if self.current:
            if fCmd.beams():
                self.current.Profile = fCmd.beams()[0].Base
            elif self.sectList.selectedItems():
                prof = FreeCAD.ActiveDocument.getObjectsByLabel(
                    self.sectList.selectedItems()[0].text()
                )[0]
                if prof.Shape.ShapeType == "Wire" and self.cb2.isChecked():
                    prof.Placement.move(
                        FreeCAD.Vector(0, 0, 0) - prof.Shape.CenterOfMass
                    )
                prof.Placement.Rotation = FreeCAD.Base.Rotation()
                self.current.Profile = prof


class insertSectForm(QWidget):
    """dialog for Arch.makeProfile
    This allows to create in the model the 2D profiles to be used
    for beams objects.
    It creates a group named "Profiles_set where the 2D objects are
    conveniently gathered and retrieved by the Frameline Manager.
    NOTE: It's also possible to create customized 2D profiles and drag-and-drop
    them inside this group."
    """

    def __init__(self, winTitle="Insert section", icon="dodo.svg"):
        """
        __init__(self,winTitle='Title',icon='filename.svg')
        """
        super(insertSectForm, self).__init__()
        self.move(QPoint(100, 250))
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(winTitle)
        iconPath = join(dirname(abspath(__file__)), "iconz", icon)
        from PySide.QtGui import QIcon

        Icon = QIcon()
        Icon.addFile(iconPath)
        self.setWindowIcon(Icon)
        self.mainHL = QHBoxLayout()
        self.setLayout(self.mainHL)
        self.firstCol = QWidget()
        self.firstCol.setLayout(QVBoxLayout())
        self.mainHL.addWidget(self.firstCol)
        self.SType = "IPE"
        self.currentRatingLab = QLabel("Section: " + self.SType)
        self.firstCol.layout().addWidget(self.currentRatingLab)
        self.sizeList = QListWidget()
        self.sizeList.setMaximumWidth(120)
        self.firstCol.layout().addWidget(self.sizeList)
        self.sectDictList = []
        self.fileList = listdir(join(dirname(abspath(__file__)), "tablez"))
        self.fillSizes()
        self.PRatingsList = [
            s.lstrip("Section_").rstrip(".csv")
            for s in self.fileList
            if s.startswith("Section")
        ]
        self.secondCol = QWidget()
        self.secondCol.setLayout(QVBoxLayout())
        self.lab1 = QLabel("Section types:")
        self.secondCol.layout().addWidget(self.lab1)
        self.ratingList = QListWidget()
        self.ratingList.setMaximumWidth(100)
        self.ratingList.addItems(self.PRatingsList)
        self.ratingList.itemClicked.connect(self.changeRating)
        self.ratingList.setCurrentRow(0)
        self.secondCol.layout().addWidget(self.ratingList)
        self.btn1 = QPushButton("Insert")
        self.btn1.setMaximumWidth(100)
        self.btn1.clicked.connect(self.insert)
        self.secondCol.layout().addWidget(self.btn1)
        self.mainHL.addWidget(self.secondCol)
        self.show()

    def fillSizes(self):
        self.sizeList.clear()
        for fileName in self.fileList:
            if fileName == "Section_" + self.SType + ".csv":
                f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
                reader = csv.DictReader(f, delimiter=";")
                self.sectDictList = [x for x in reader]
                f.close()
                for row in self.sectDictList:
                    s = row["SSize"]
                    self.sizeList.addItem(s)

    def changeRating(self, item):
        self.SType = item.text()
        self.currentRatingLab.setText("Section: " + self.SType)
        self.fillSizes()

    def insert(self):  # insert the section
        result = FreeCAD.ActiveDocument.findObjects(
            "App::DocumentObjectGroup", "Profiles_set"
        )
        if result:
            group = result[0]
        else:
            group = FreeCAD.activeDocument().addObject(
                "App::DocumentObjectGroup", "Profiles_set"
            )
        if self.sizeList.selectedItems():
            prop = self.sectDictList[self.sizeList.currentRow()]
            if prop["stype"] == "C":
                s = makeCircle(float(prop["H"]))
            else:
                s = ArchProfile.makeProfile(
                    [
                        0,
                        "SECTION",
                        prop["SSize"] + "-000",
                        prop["stype"],
                        float(prop["W"]),
                        float(prop["H"]),
                        float(prop["ta"]),
                        float(prop["tf"]),
                    ]
                )
            group.addObject(s)
        FreeCAD.activeDocument().recompute()


import dodoDialogs


class frameBranchForm(dodoDialogs.protoTypeDialog):
    "dialog for framebranches"

    def __init__(self):
        super(frameBranchForm, self).__init__("fbranch.ui")
        self.sectDictList = []  # list (sizes) of properties (dictionaries) of the current type of section
        self.form.editAngle.setValidator(QDoubleValidator())
        self.form.editAngle.editingFinished.connect(self.changeAngle)
        self.form.editHead.setValidator(QDoubleValidator())
        self.form.editHead.editingFinished.connect(self.changeHeadOffset)
        self.form.editTail.setValidator(QDoubleValidator())
        self.form.editTail.editingFinished.connect(self.changeTailOffset)
        self.form.editLength.setValidator(QDoubleValidator())
        tablez = listdir(join(dirname(abspath(__file__)), "tablez"))
        files = [name for name in tablez if name.startswith("Section")]
        RatingsList = [s.lstrip("Section_").rstrip(".csv") for s in files]
        self.form.comboRatings.addItems(RatingsList)
        self.form.comboRatings.addItems(["<by sketch>"])
        self.form.comboRatings.currentIndexChanged.connect(self.fillSizes)
        self.form.btnRemove.clicked.connect(self.removeBeams)
        self.form.btnAdd.clicked.connect(self.addBeams)
        self.form.btnProfile.clicked.connect(self.changeProfile)
        self.form.btnRefresh.clicked.connect(self.refresh)
        self.form.btnTargets.clicked.connect(self.selectAction)
        self.form.btnTrim.clicked.connect(self.trim)
        self.form.btnSingle.clicked.connect(self.makeSingle)
        self.form.sliTail.valueChanged.connect(self.stretchTail)
        self.form.sliHead.valueChanged.connect(self.stretchHead)
        self.form.dialAngle.valueChanged.connect(self.spinAngle)
        self.fillSizes()
        self.targets = list()
        self.labTail = None
        self.actionX.triggered.disconnect(self.accept)  # disconnect from accept()
        self.actionX.triggered.connect(self.trim)  # reconnect to trim()

    def makeSingle(self):
        FreeCAD.activeDocument().openTransaction("Insert Single Struct")
        if self.SType == "<by sketch>":
            profile = FreeCAD.ActiveDocument.getObjectsByLabel(
                self.form.listSizes.currentItem().text()
            )[0]
        else:
            prop = self.sectDictList[self.form.listSizes.currentRow()]
            profile = newProfile(prop)
        if fCmd.faces():
            Z = FreeCAD.Vector(0, 0, 1)
            for f in fCmd.faces():
                beam = makeStructure(profile)
                beam.Placement = FreeCAD.Placement(
                    f.CenterOfMass, FreeCAD.Rotation(Z, f.normalAt(0, 0))
                )
                if self.form.editLength.text():
                    beam.Height = float(self.form.editLength.text())
        elif fCmd.edges():
            for e in fCmd.edges():
                beam = makeStructure(profile)
                fCmd.placeTheBeam(beam, e)
                if self.form.editLength.text():
                    beam.Height = float(self.form.editLength.text())
        elif [
            v
            for sx in FreeCADGui.Selection.getSelectionEx()
            for so in sx.SubObjects
            for v in so.Vertexes
        ]:
            vs = [
                v
                for sx in FreeCADGui.Selection.getSelectionEx()
                for so in sx.SubObjects
                for v in so.Vertexes
            ]
            for v in vs:
                beam = makeStructure(profile)
                beam.Placement.Base = v.Point
        else:
            beam = makeStructure(profile)
            if self.form.editLength.text():
                beam.Height = float(self.form.editLength.text())
        FreeCAD.ActiveDocument.recompute()

    def accept(self):
        if FreeCAD.ActiveDocument:
            # GET BASE
            bases = [
                b for b in FreeCADGui.Selection.getSelection() if hasattr(b, "Shape")
            ]
            if bases and self.form.listSizes.selectedItems():
                FreeCAD.activeDocument().openTransaction("Insert FrameBranch")
                if self.SType == "<by sketch>":
                    profile = FreeCAD.ActiveDocument.getObjectsByLabel(
                        self.form.listSizes.currentItem().text()
                    )[0]
                else:
                    prop = self.sectDictList[self.form.listSizes.currentRow()]
                    profile = newProfile(prop)
                # MAKE FRAMEBRANCH
                if self.form.editName.text():
                    name = self.form.editName.text()
                else:
                    name = translate("makeframenbranch","Travatura") 
                a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
                FrameBranch(a, bases[0], profile)
                ViewProviderFrameBranch(a.ViewObject)
                FreeCAD.activeDocument().commitTransaction()
                FreeCAD.activeDocument().recompute()
                FreeCAD.activeDocument().recompute()

    def reject(self):  # redefined to remove label from the scene
        if self.labTail:
            self.labTail.removeLabel()
        super(frameBranchForm, self).reject()

    def selectAction(self):
        self.targets = []
        selex = FreeCADGui.Selection.getSelectionEx()
        shapes = [(sx.SubObjects[0], sx.Object.Label) for sx in selex if sx.SubObjects]
        for shape in shapes:
            self.targets.append(shape[0])
        if len(shapes) > 1:
            self.form.lab2.setText("<multiple selection>")
        else:
            self.form.lab2.setText(shapes[0][1] + ": " + shapes[0][0].ShapeType)

    def mouseActionB1(self, CtrlAltShift):
        v = FreeCADGui.ActiveDocument.ActiveView
        i = v.getObjectInfo(v.getCursorPos())
        if i:
            labText = i["Object"]
            obj = FreeCAD.ActiveDocument.getObject(i["Object"])
            if (
                hasattr(obj, "tailOffset")
                and hasattr(obj, "headOffset")
                and hasattr(obj, "spin")
            ):
                self.form.editTail.setText(str(obj.tailOffset))
                self.form.editHead.setText(str(obj.headOffset))
                self.form.editAngle.setText(str(obj.spin))
                fb = findFB(i["Object"])
                if fb:
                    labText += ": part of " + fb.Label
                if self.labTail:
                    self.labTail.removeLabel()
                self.labTail = label3D(pl=obj.Placement, text=translate("mouseActionB1","____TAIL"))
            else:
                if self.labTail:
                    self.labTail.removeLabel()
                self.labTail = label3D(pl=FreeCAD.Placement(), text="")
                self.form.editTail.clear()
                self.form.editHead.clear()
                self.form.editAngle.clear()
                self.form.sliHead.setValue(0)
                self.form.sliTail.setValue(0)
                self.form.dialAngle.setValue(0)
            self.form.lab1.setText(labText)
        else:
            if self.labTail:
                self.labTail.removeLabel()
            self.labTail = label3D(pl=FreeCAD.Placement(), text="")
            self.form.sliHead.setValue(0)
            self.form.sliTail.setValue(0)
            self.form.dialAngle.setValue(0)
            self.form.lab1.setText("<no item selected>")

    def fillSizes(self):
        self.SType = self.form.comboRatings.currentText()
        self.form.listSizes.clear()
        if self.SType == "<by sketch>":
            self.form.listSizes.addItems(
                [
                    s.Label
                    for s in FreeCAD.ActiveDocument.Objects
                    if s.TypeId == "Sketcher::SketchObject"
                ]
            )
            obj2D = [
                s.Label
                for s in FreeCAD.ActiveDocument.Objects
                if hasattr(s, "Shape") and s.Shape.Faces and not s.Shape.Solids
            ]
            self.form.listSizes.addItems(obj2D)
        else:
            fileName = "Section_" + self.SType + ".csv"
            f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
            reader = csv.DictReader(f, delimiter=";")
            self.sectDictList = [x for x in reader]
            f.close()
            for row in self.sectDictList:
                s = row["SSize"]
                self.form.listSizes.addItem(s)

    def addBeams(self):
        # find selected FB
        try:
            FB = findFB(baseName=FreeCADGui.Selection.getSelection()[0].Name)
        except:
            return
        if FB:
            beamsList = FB.Beams
            for edge in fCmd.edges():
                i = indexEdge(edge, FB.Base.Shape.Edges)
                beam = makeStructure(FB.Profile)
                beam.addProperty(
                    "App::PropertyFloat",
                    "tailOffset",
                    "FrameBranch",
                    QT_TRANSLATE_NOOP(
                        "App::PropertyFloat", "The extension of the tail"
                    ),
                )
                beam.addProperty(
                    "App::PropertyFloat",
                    "headOffset",
                    "FrameBranch",
                    QT_TRANSLATE_NOOP(
                        "App::PropertyFloat", "The extension of the head"
                    ),
                )
                beam.addProperty(
                    "App::PropertyFloat",
                    "spin",
                    "FrameBranch",
                    QT_TRANSLATE_NOOP(
                        "App::PropertyFloat", "The rotation of the section"
                    ),
                )
                if int(FreeCAD.Version()[1]) > 19:  # 20220704
                    beam.addExtension("Part::AttachExtensionPython")
                else:
                    beam.addExtension("Part::AttachExtensionPython", beam)
                if int(FreeCAD.Version()[0]) >= 1:
                    beam.AttachmentSupport = [(FB.Base, "Edge" + str(i + 1))]
                else:
                    beam.Support = [(FB.Base, "Edge" + str(i + 1))]
                beam.MapMode = "NormalToEdge"
                beam.MapReversed = True
                beamsList[i] = str(beam.Name)
            FB.Beams = beamsList
            FreeCAD.ActiveDocument.recompute()
            FreeCAD.ActiveDocument.recompute()

    def removeBeams(self):
        for beam in fCmd.beams():
            FB = findFB(beamName=beam.Name)
            if FB:
                i = FB.Beams.index(beam.Name)
                FB.Proxy.remove(i)

    def changeProfile(self):
        # find selected FB
        try:
            FB = findFB(baseName=FreeCADGui.Selection.getSelection()[0].Name)
            if not FB:
                FB = findFB(beamName=fCmd.beams()[0].Name)
        except:
            FreeCAD.Console.PrintError("Nothing selected\n")
            return
        if FB and self.form.listSizes.selectedItems():
            if self.SType == "<by sketch>":
                profile = FreeCAD.ActiveDocument.getObjectsByLabel(
                    self.form.listSizes.currentItem().text()
                )[0]
            else:
                prop = self.sectDictList[self.form.listSizes.currentRow()]
                profile = newProfile(prop)
            name = FB.Profile.Name
            FB.Profile = profile
            FB.Proxy.redraw(FB)
            FreeCAD.ActiveDocument.removeObject(name)
            FreeCAD.ActiveDocument.recompute()
            FreeCAD.ActiveDocument.recompute()
        else:
            FreeCAD.Console.PrintError("No frameBranch or profile selected\n")

    def changeHeadOffset(self):
        for beam in fCmd.beams():
            if hasattr(beam, "headOffset"):
                beam.headOffset = float(self.form.editHead.text())
                FB = findFB(beam.Name)
                FB.touch()
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.ActiveDocument.recompute()

    def changeTailOffset(self):
        for beam in fCmd.beams():
            if hasattr(beam, "tailOffset"):
                beam.tailOffset = float(self.form.editTail.text())
                FB = findFB(beam.Name)
                FB.touch()
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.ActiveDocument.recompute()

    def changeAngle(self):
        for beam in fCmd.beams():
            if hasattr(beam, "spin"):
                FB = findFB(beam.Name)
                beam.spin = float(self.form.editAngle.text())
                FB.touch()
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.ActiveDocument.recompute()

    def stretchTail(self):
        beams = fCmd.beams()
        if beams:
            L = float(beams[0].Height) / 2
            ext = L * (self.form.sliTail.value() / 100.0)
            self.form.editTail.setText("%.3f" % ext)
            self.changeTailOffset()

    def stretchHead(self):
        beams = fCmd.beams()
        if beams:
            L = float(beams[0].Height) / 2
            ext = L * (self.form.sliHead.value() / 100.0)
            self.form.editHead.setText("%.3f" % ext)
            self.changeHeadOffset()

    def spinAngle(self):
        self.form.editAngle.setText(str(self.form.dialAngle.value()))
        self.changeAngle()

    def trim(self):
        FreeCAD.ActiveDocument.openTransaction("Trim FB")
        for target in self.targets:
            for b in fCmd.beams():
                if hasattr(b, "tailOffset") and hasattr(b, "headOffset"):
                    if int(FreeCAD.Version()[0]) >= 1:
                        edge = b.AttachmentSupport[0][0].Shape.getElement(b.AttachmentSupport[0][1][0])
                    else:
                        edge = b.Support[0][0].Shape.getElement(b.Support[0][1][0])
                    ax = edge.tangentAt(0).normalize()  # fCmd.beamAx(b).normalize()
                    tail = edge.valueAt(0)  # b.Placement.Base
                    head = edge.valueAt(edge.LastParameter)  # tail+ax*float(b.Height)
                    if target.ShapeType == "Vertex":
                        P = target.Point
                    elif target.ShapeType == "Face" and not fCmd.isOrtho(target, ax):
                        P = fCmd.intersectionPlane(tail, ax, target)
                    elif hasattr(target, "CenterOfMass"):
                        P = target.CenterOfMass
                    else:
                        P = None
                    if P:
                        deltaTail = (P - tail).dot(ax)
                        deltaHead = (P - head).dot(ax)
                        if abs(deltaTail) < abs(deltaHead):
                            b.tailOffset = -deltaTail
                        else:
                            b.headOffset = deltaHead
        refresh()
        FreeCAD.ActiveDocument.commitTransaction()

    def refresh(self):
        obj = findFB(fCmd.beams()[0].Name)
        if not obj:
            obj = findFB(baseName=FreeCADGui.Selection.getSelection()[0])
        if obj:
            obj.Proxy.redraw(obj)
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.ActiveDocument.recompute()


################ CLASSES ###########################


class FrameLine(object):
    """Class for object FrameLine
    Has attributes Base (the path) and Profile to define the frame shape and
    the type section's profile.
    Creates a group to collect the Structure objects.
    Provides methods update() and purge() to redraw the Structure objects
    when the Base is modified.
    """

    def __init__(self, obj, section="IPE200", lab=None):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "FrameLine",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of frameFeature"),
        ).FType = "FrameLine"
        obj.addProperty(
            "App::PropertyString",
            "FSize",
            "FrameLine",
            QT_TRANSLATE_NOOP("App::PropertyString", "Size of frame"),
        ).FSize = section
        if lab:
            obj.Label = lab
        obj.addProperty(
            "App::PropertyString",
            "Group",
            "FrameLine",
            QT_TRANSLATE_NOOP("App::PropertyString", "The group."),
        ).Group = obj.Label + "_pieces"
        group = FreeCAD.activeDocument().addObject(
            "App::DocumentObjectGroup", obj.Group
        )
        group.addObject(obj)
        FreeCAD.Console.PrintWarning("Created group " + obj.Group + "\n")
        obj.addProperty(
            "App::PropertyLink",
            "Base",
            "FrameLine",
            QT_TRANSLATE_NOOP("App::PropertyLink", "the edges"),
        )
        obj.addProperty(
            "App::PropertyLink",
            "Profile",
            "FrameLine",
            QT_TRANSLATE_NOOP("App::PropertyLink", "the profile"),
        )

    def onChanged(self, fp, prop):
        if prop == "Label" and len(fp.InList):
            fp.InList[0].Label = fp.Label + "_pieces"
            fp.Group = fp.Label + "_pieces"
        if prop == "Base" and fp.Base:
            FreeCAD.Console.PrintWarning(
                fp.Label + " Base has changed to " + fp.Base.Label + "\n"
            )
        if prop == "Profile" and fp.Profile:
            fp.Profile.ViewObject.Visibility = False
            FreeCAD.Console.PrintWarning(
                fp.Label + " Profile has changed to " + fp.Profile.Label + "\n"
            )

    def purge(self, fp):
        group = FreeCAD.activeDocument().getObjectsByLabel(fp.Group)[0]
        beams2purge = fCmd.beams(group.OutList)
        if beams2purge:
            for b in beams2purge:
                profiles = b.OutList
                FreeCAD.ActiveDocument.removeObject(b.Name)
                for p in profiles:
                    FreeCAD.ActiveDocument.removeObject(p.Name)

    def update(self, fp, copyProfile=True):
        if hasattr(fp.Base, "Shape"):
            edges = fp.Base.Shape.Edges
            if not edges:
                FreeCAD.Console.PrintError("Base has not valid edges\n")
                return
        group = FreeCAD.activeDocument().getObjectsByLabel(fp.Group)[0]
        if fp.Profile:
            FreeCAD.activeDocument().openTransaction("Update frameLine")
            for e in edges:
                if copyProfile:
                    p = FreeCAD.activeDocument().copyObject(fp.Profile, True)
                else:
                    p = fp.Profile
                beam = makeStructure(p)
                fCmd.placeTheBeam(beam, e)
                pCmd.moveToPyLi(beam, fp.Name)
            FreeCAD.activeDocument().commitTransaction()
        FreeCAD.activeDocument().recompute()

    def execute(self, fp):
        return None


class FrameBranch(object):
    def __init__(self, obj, base=None, profile=None):
        obj.Proxy = self
        # PROXY CLASS PROPERTIES
        self.objName = obj.Name
        # FEATUREPYTHON OBJECT PROPERTIES
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "FrameBranch",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of frameFeature"),
        ).FType = "FrameBranch"
        obj.addProperty(
            "App::PropertyStringList",
            "Beams",
            "FrameBranch",
            QT_TRANSLATE_NOOP("App::PropertyStringList", "The beams names"),
        )
        obj.addProperty(
            "App::PropertyLink",
            "Base",
            "FrameBranch",
            QT_TRANSLATE_NOOP("App::PropertyLink", "The path."),
        ).Base = base
        obj.addProperty(
            "App::PropertyLink",
            "Profile",
            "FrameBranch",
            QT_TRANSLATE_NOOP("App::PropertyLink", "The profile"),
        ).Profile = profile
        self.redraw(obj)

    def execute(self, obj):
        X = FreeCAD.Vector(1, 0, 0)
        Z = FreeCAD.Vector(0, 0, 1)
        if hasattr(obj, "Base") and obj.Base and hasattr(obj, "Beams"):
            n = obj.Base.Placement.Rotation.multVec(Z)
            for i in range(len(obj.Beams)):
                if obj.Beams[i]:
                    edge = obj.Base.Shape.Edges[i]
                    beam = FreeCAD.ActiveDocument.getObject(obj.Beams[i])
                    beam.Height = (
                        float(obj.Base.Shape.Edges[i].Length)
                        + beam.tailOffset
                        + beam.headOffset
                    )
                    offset = FreeCAD.Vector(0, 0, beam.tailOffset).negative()
                    spin = FreeCAD.Rotation()
                    beam.AttachmentOffset = FreeCAD.Placement(offset, spin)
                    angle = degrees(fCmd.beamAx(beam, X).getAngle(n))
                    beam.AttachmentOffset.Rotation = FreeCAD.Rotation(
                        Z, angle + beam.spin
                    )

    def redraw(self, obj):
        # clear all
        for o in obj.Beams:
            FreeCAD.ActiveDocument.removeObject(o)
        # create new beams
        i = 0
        beamsList = []
        for e in obj.Base.Shape.Edges:
            if e.curvatureAt(0) == 0:
                beam = makeStructure(obj.Profile)
                beam.addProperty(
                    "App::PropertyFloat",
                    "tailOffset",
                    "FrameBranch",
                    QT_TRANSLATE_NOOP(
                        "App::PropertyFloat", "The extension of the tail"
                    ),
                )
                beam.addProperty(
                    "App::PropertyFloat",
                    "headOffset",
                    "FrameBranch",
                    QT_TRANSLATE_NOOP(
                        "App::PropertyFloat", "The extension of the head"
                    ),
                )
                beam.addProperty(
                    "App::PropertyFloat",
                    "spin",
                    "FrameBranch",
                    QT_TRANSLATE_NOOP(
                        "App::PropertyFloat", "The rotation of the section"
                    ),
                )
                if int(FreeCAD.Version()[1]) > 19:  # 20220704
                    beam.addExtension("Part::AttachExtensionPython")
                else:
                    beam.addExtension("Part::AttachExtensionPython", beam)
                if int(FreeCAD.Version()[0]) >= 1:
                    beam.AttachmentSupport = [(obj.Base, "Edge" + str(i + 1))]
                else:
                    beam.Support = [(obj.Base, "Edge" + str(i + 1))]
                beam.MapMode = "NormalToEdge"
                beam.MapReversed = True
                beamsList.append(str(beam.Name))
                i += 1
        obj.Beams = beamsList

    def remove(self, i):
        obj = FreeCAD.ActiveDocument.getObject(self.objName)
        FreeCAD.ActiveDocument.removeObject(obj.Beams[i])
        b = [str(n) for n in obj.Beams]
        b[i] = ""
        obj.Beams = b


class ViewProviderFrameBranch:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return join(dirname(abspath(__file__)), "iconz", "framebranch.svg")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def setEdit(self, vobj, mode):
        return False

    def unsetEdit(self, vobj, mode):
        return

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def claimChildren(self):
        children = [
            FreeCAD.ActiveDocument.getObject(name) for name in self.Object.Beams
        ]
        return children

    def onDelete(self, feature, subelements):  # subelements is a tuple of strings
        return True


######### customArchProfile ############

import Draft
from FreeCAD import Vector

if FreeCAD.GuiUp:
    # import FreeCADGui
    # from PySide import QtCore, QtGui
    from DraftGui import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond


def doProfile(
    typeS="RH", label="Square", dims=[50, 100, 5]
):  # rearrange args in a better mnemonic way
    "doProfile(typeS, label, dims)"
    if typeS in ["RH", "R", "H", "U", "L", "T", "Z", "omega", "circle"]:
        profile = [0, "SECTION", label, typeS] + dims  # for py2.6 versions
        obj = FreeCAD.ActiveDocument.addObject("Part::Part2DObjectPython", profile[2])
        obj.Label = translate("Arch", profile[2])
        if profile[3] == "RH":
            _ProfileRH(obj, profile)
        elif profile[3] == "R":
            _ProfileR(obj, profile)
        elif profile[3] == "U":
            _ProfileU(obj, profile)
        elif profile[3] == "T":
            _ProfileT(obj, profile)
        elif profile[3] == "H":
            _ProfileH(obj, profile)
        elif profile[3] == "L":
            _ProfileL(obj, profile)
        elif profile[3] == "Z":
            _ProfileZ(obj, profile)
        elif profile[3] == "omega":
            _ProfileOmega(obj, profile)
        elif profile[3] == "circle":
            _ProfileCircle(obj, profile)
        else:
            print("Profile not supported")
        if FreeCAD.GuiUp:
            Draft._ViewProviderDraft(obj.ViewObject)
        return obj
    else:
        FreeCAD.Console.PrintError("Not such section!\n")


def drawAndCenter(points):
    p = Part.makePolygon(points)
    s = Part.Face(p)
    v = s.CenterOfMass
    points2 = [point.add(v.negative()) for point in points]
    p2 = Part.makePolygon(points2)
    return Part.Face(p2)


############ pointsXXX() functions #################


def pointsH(H, W, D, t1, t2, t3):
    p1 = Vector(0, 0, 0)
    p2 = Vector(W, 0, 0)
    p3 = Vector(W, t2, 0)
    p4 = Vector(W / 2 + t1 / 2, t2, 0)
    p5 = Vector(W / 2 + t1 / 2, H - t3, 0)
    p6 = Vector(W / 2 + D / 2, H - t3, 0)
    p7 = Vector(W / 2 + D / 2, H, 0)
    p8 = Vector(W / 2 - D / 2, H, 0)
    p9 = Vector(W / 2 - D / 2, H - t3, 0)
    p10 = Vector(W / 2 - t1 / 2, H - t3, 0)
    p11 = Vector(W / 2 - t1 / 2, t2, 0)
    p12 = Vector(0, t2, 0)
    return [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p1]


def pointsL(H, W, t1, t2):
    p1 = Vector(-W / 2, -H / 2, 0)
    p2 = Vector(W / 2, -H / 2, 0)
    p3 = Vector(W / 2, H / 2, 0)
    p4 = Vector(W / 2 - t1, H / 2, 0)
    p5 = Vector(W / 2 - t1, t2 - H / 2, 0)
    p6 = Vector(-W / 2, t2 - H / 2, 0)
    return [p1, p2, p3, p4, p5, p6, p1]


def pointsOmega(H, W, D, t1, t2, t3):
    p1 = Vector(0, 0, 0)
    p2 = Vector(W, 0, 0)
    p3 = Vector(W, H - t3, 0)
    p4 = Vector(W + D - t1, H - t3, 0)
    p5 = Vector(W + D - t1, H, 0)
    p6 = Vector(W - t1, H, 0)
    p7 = Vector(W - t1, t2, 0)
    p8 = Vector(t1, t2, 0)
    p9 = Vector(t1, H, 0)
    p10 = Vector(t1 - D, H, 0)
    p11 = Vector(t1 - D, H - t3, 0)
    p12 = Vector(0, H - t3, 0)
    return [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p1]


def pointsT(H, W, t1, t2):
    p1 = Vector(-W / 2, -H / 2, 0)
    p2 = Vector(W / 2, -H / 2, 0)
    p3 = Vector(W / 2, (-H / 2) + t2, 0)
    p4 = Vector(t1 / 2, (-H / 2) + t2, 0)
    p5 = Vector(t1 / 2, H / 2, 0)
    p6 = Vector(-t1 / 2, H / 2, 0)
    p7 = Vector(-t1 / 2, (-H / 2) + t2, 0)
    p8 = Vector(-W / 2, (-H / 2) + t2, 0)
    return [p1, p2, p3, p4, p5, p6, p7, p8, p1]


def pointsU(H, W, D, t1, t2, t3):
    p1 = Vector(0, 0, 0)
    p2 = Vector(W, 0, 0)
    p3 = Vector(W, H, 0)
    p4 = Vector(W - D, H, 0)
    p5 = Vector(W - D, H - t3, 0)
    p6 = Vector(W - t1, H - t3, 0)
    p7 = Vector(W - t1, t2, 0)
    p8 = Vector(0, t2, 0)
    return [p1, p2, p3, p4, p5, p6, p7, p8, p1]


def pointsZ(H, W, t1, t2):
    p1 = Vector(-t1 / 2, -W / 2, 0)
    p2 = Vector(-t1 / 2, (W / 2) - t2, 0)
    p3 = Vector(t1 / 2 - H, (W / 2) - t2, 0)
    p4 = Vector(t1 / 2 - H, W / 2, 0)
    p5 = Vector(t1 / 2, W / 2, 0)
    p6 = Vector(t1 / 2, t2 - W / 2, 0)
    p7 = Vector(H - t1 / 2, t2 - W / 2, 0)
    p8 = Vector(H - t1 / 2, -W / 2, 0)
    return [p1, p8, p7, p6, p5, p4, p3, p2, p1]


########### _ ProfileXXX() classes ###############

# class _Profile(Draft._DraftObject):
# '''Superclass for Profile classes'''

# def __init__(self,obj, profile):
# self.Profile=profile
# Draft._DraftObject.__init__(self,obj,"Profile")
from ArchProfile import _Profile


class _ProfileRH(_Profile):
    """A parametric Rectangular hollow beam profile. Profile data: [width, height, thickness]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "RH"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the beam"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the vertical sides"),
        ).t1 = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP(
                "App::PropertyLength", "Thickness of the horizontal sides"
            ),
        ).t2 = profile[7]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, t1, t2 = obj.W.Value, obj.H.Value, obj.t1.Value, obj.t2.Value
        p1 = Vector(-W / 2, -H / 2, 0)
        p2 = Vector(W / 2, -H / 2, 0)
        p3 = Vector(W / 2, H / 2, 0)
        p4 = Vector(-W / 2, H / 2, 0)
        q1 = Vector(-W / 2 + t1, -H / 2 + t2, 0)
        q2 = Vector(W / 2 - t1, -H / 2 + t2, 0)
        q3 = Vector(W / 2 - t1, H / 2 - t2, 0)
        q4 = Vector(-W / 2 + t1, H / 2 - t2, 0)
        p = Part.makePolygon([p1, p2, p3, p4, p1])
        q = Part.makePolygon([q1, q2, q3, q4, q1])
        obj.Shape = Part.Face(p).cut(Part.Face(q))


class _ProfileR(_Profile):
    """A parametric Rectangular solid beam profile. Profile data: [width, height]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "R"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the beam"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H = obj.W.Value, obj.H.Value
        p1 = Vector(-W / 2, -H / 2, 0)
        p2 = Vector(W / 2, -H / 2, 0)
        p3 = Vector(W / 2, H / 2, 0)
        p4 = Vector(-W / 2, H / 2, 0)
        p = Part.makePolygon([p1, p2, p3, p4, p1])
        obj.Shape = Part.Face(p)


class _ProfileCircle(_Profile):
    """A parametric circular beam profile.
    Profile data:
      D: diameter
      t1: thickness (optional; "0" for solid section)"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "circle"
        obj.addProperty(
            "App::PropertyLength",
            "D",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Diameter of the beam"),
        ).D = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness"),
        ).t1 = profile[5]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        D, t1 = obj.D.Value, obj.t1.Value
        if not t1:
            obj.Shape = Part.makeFace([Part.makeCircle(D / 2)], "Part::FaceMakerSimple")
        elif t1 < D / 2:
            c1 = Part.makeFace([Part.makeCircle(D / 2)], "Part::FaceMakerSimple")
            c2 = Part.makeFace([Part.makeCircle(D / 2 - t1)], "Part::FaceMakerSimple")
            obj.Shape = c1.cut(c2)


class _ProfileL(_Profile):
    """A parametric L beam profile. Profile data: [width, height, web thickness]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "L"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the beam"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the webs"),
        ).t1 = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the webs"),
        ).t2 = profile[7]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, t1, t2 = obj.W.Value, obj.H.Value, obj.t1.Value, obj.t2.Value
        obj.Shape = drawAndCenter(pointsL(H, W, t1, t2))


class _ProfileT(_Profile):
    """A parametric T beam profile. Profile data: [width, height, web thickness]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "T"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the beam"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the web"),
        ).t1 = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the web"),
        ).t2 = profile[7]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, t1, t2 = obj.W.Value, obj.H.Value, obj.t1.Value, obj.t2.Value
        obj.Shape = drawAndCenter(pointsT(H, W, t1, t2))


class _ProfileZ(_Profile):
    """A parametric Z beam profile. Profile data: [width, height, web thickness, flange thickness]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "Z"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the beam"),
        ).W = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the web"),
        ).t1 = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness of the flanges"),
        ).t2 = profile[7]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, t1, t2 = obj.W.Value, obj.H.Value, obj.t1.Value, obj.t2.Value
        obj.Shape = drawAndCenter(pointsZ(H, W, t1, t2))


class _ProfileOmega(_Profile):
    """A parametric omega beam profile. Profile data: [W, H, D, t1,t2,t3]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "omega"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the beam"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "D",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the flanges"),
        ).D = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 1"),
        ).t1 = profile[7]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 2"),
        ).t2 = profile[8]
        obj.addProperty(
            "App::PropertyLength",
            "t3",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 3"),
        ).t3 = profile[9]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, D, t1, t2, t3 = (
            obj.W.Value,
            obj.H.Value,
            obj.D.Value,
            obj.t1.Value,
            obj.t2.Value,
            obj.t3.Value,
        )
        obj.Shape = drawAndCenter(pointsOmega(H, W, D, t1, t2, t3))


class _ProfileH(_Profile):
    """A parametric omega beam profile. Profile data: [W, H, D, t1,t2,t3]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "H"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the bottom flange"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "D",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the top flange"),
        ).D = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 1"),
        ).t1 = profile[7]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 2"),
        ).t2 = profile[8]
        obj.addProperty(
            "App::PropertyLength",
            "t3",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 3"),
        ).t3 = profile[9]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, D, t1, t2, t3 = (
            obj.W.Value,
            obj.H.Value,
            obj.D.Value,
            obj.t1.Value,
            obj.t2.Value,
            obj.t3.Value,
        )
        obj.Shape = drawAndCenter(pointsH(H, W, D, t1, t2, t3))


class _ProfileU(_Profile):
    """A parametric U beam profile. Profile data: [W, H, D, t1,t2,t3]"""

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyString",
            "FType",
            "Profile",
            QT_TRANSLATE_NOOP("App::PropertyString", "Type of section"),
        ).FType = "U"
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the bottom flange"),
        ).W = profile[4]
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Height of the beam"),
        ).H = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "D",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Width of the top flange"),
        ).D = profile[6]
        obj.addProperty(
            "App::PropertyLength",
            "t1",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 1"),
        ).t1 = profile[7]
        obj.addProperty(
            "App::PropertyLength",
            "t2",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 2"),
        ).t2 = profile[8]
        obj.addProperty(
            "App::PropertyLength",
            "t3",
            "Draft",
            QT_TRANSLATE_NOOP("App::PropertyLength", "Thickness 3"),
        ).t3 = profile[9]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        W, H, D, t1, t2, t3 = (
            obj.W.Value,
            obj.H.Value,
            obj.D.Value,
            obj.t1.Value,
            obj.t2.Value,
            obj.t3.Value,
        )
        obj.Shape = drawAndCenter(pointsU(H, W, D, t1, t2, t3))
