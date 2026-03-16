# SPDX-License-Identifier: LGPL-3.0-or-later

import csv
from os import listdir, mkdir
from os.path import abspath, dirname, join, exists

import FreeCAD
import FreeCADGui
from PySide.QtCore import *
from PySide.QtGui import *
from pFeatures import Flange

translate = FreeCAD.Qt.translate

try:
    import quetzal_units as qu
except Exception:
    qu = None  # graceful fallback if module not yet present


class protoTypeDialog(object):
    "prototype for dialogs.ui with callback function"

    def __init__(self, dialog="anyFile.ui"):
        dialogPath = join(dirname(abspath(__file__)), "dialogz", dialog)
        self.form = FreeCADGui.PySideUic.loadUi(dialogPath)
        ### new shortcuts procedure
        self.mw = FreeCADGui.getMainWindow()
        for act in self.mw.findChildren(QAction):
            if act.objectName() in ["actionX", "actionS"]:
                self.mw.removeAction(act)
        self.actionX = QAction(self.mw)
        self.actionX.setObjectName("actionX")  # define X action
        self.actionX.setShortcut(QKeySequence("X"))
        self.actionX.triggered.connect(self.accept)
        self.mw.addAction(self.actionX)
        self.actionS = QAction(self.mw)
        self.actionS.setObjectName("actionS")  # define S action
        self.actionS.setShortcut(QKeySequence("S"))
        self.actionS.triggered.connect(self.selectAction)
        self.mw.addAction(self.actionS)
        self.actionESC = QAction(self.mw)
        FreeCAD.Console.PrintMessage(
            translate("protoTypeDialog", '"%s" to select; "%s" to execute')
            % (
                self.actionS.shortcuts()[0].toString(),
                self.actionX.shortcuts()[0].toString(),
            )
            + "\r\n"
        )
        try:
            self.view = FreeCADGui.activeDocument().activeView()
            self.call = self.view.addEventCallback(
                "SoMouseButtonEvent", self.action
            )  # SoKeyboardEvents replaced by QAction'
        except:
            FreeCAD.Console.PrintError(translate("protoTypeDialog", "No view available."))

    def action(self, arg):
        'Defines functions executed by the callback self.call when "SoMouseButtonEvent"'
        # SoKeyboardEvents replaced by QAction':
        CtrlAltShift = [arg["CtrlDown"], arg["AltDown"], arg["ShiftDown"]]
        if arg["Button"] == "BUTTON1" and arg["State"] == "DOWN":
            self.mouseActionB1(CtrlAltShift)
        elif arg["Button"] == "BUTTON2" and arg["State"] == "DOWN":
            self.mouseActionB2(CtrlAltShift)
        elif arg["Button"] == "BUTTON3" and arg["State"] == "DOWN":
            self.mouseActionB3(CtrlAltShift)

    def selectAction(self):
        "MUST be redefined in the child class"
        print('"selectAction" performed')
        pass

    def mouseActionB1(self, CtrlAltShift):
        "MUST be redefined in the child class"
        pass

    def mouseActionB2(self, CtrlAltShift):
        "MUST be redefined in the child class"
        pass

    def mouseActionB3(self, CtrlAltShift):
        "MUST be redefined in the child class"
        pass

    def reject(self):
        "CAN be redefined to remove other attributes, such as arrow()s or label()s"
        self.mw.removeAction(self.actionX)
        self.mw.removeAction(self.actionS)
        FreeCAD.Console.PrintMessage(
            translate("protoTypeDialog", 'Actions "%s" and "%s" removed')
            % (self.actionX.objectName(), self.actionS.objectName())
            + "\r\n"
        )
        try:
            self.view.removeEventCallback("SoMouseButtonEvent", self.call)
        except:
            pass
        FreeCADGui.Control.closeDialog()
        if FreeCAD.ActiveDocument:
            FreeCAD.ActiveDocument.recompute()


class protoPypeForm(QDialog):
    "prototype dialog for insert pFeatures"
    def __init__(
        self,
        winTitle="Title",
        PType="Pipe",
        PRating="SCH-STD",
        icon="dodo.svg",
        x=100,
        y=350,
    ):
        """
        __init__(self,winTitle='Title', PType='Pipe', PRating='SCH-STD')
          winTitle: the window's title
          PType: the pipeFeature type
          PRating: the pipeFeature pressure rating class
        It lookups in the directory ./tablez the file PType+"_"+PRating+".csv",
        imports it's content in a list of dictionaries -> .pipeDictList and
        shows a summary in the QListWidget -> .sizeList
        Also create a property -> PRatingsList with the list of available PRatings for the
        selected PType.
        """
        super(protoPypeForm, self).__init__()
        self.move(QPoint(x, y))
        self.mw = FreeCADGui.getMainWindow()
        self.PType = PType
        self.PRating = PRating
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(winTitle)
        iconPath = join(dirname(abspath(__file__)), "iconz", icon)
        from PySide.QtGui import QIcon

        Icon = QIcon()
        Icon.addFile(iconPath)
        self.setWindowIcon(Icon)
        self.mainHL = QHBoxLayout()
        self.setMaximumSize(350,230)
        self.setLayout(self.mainHL)
        self.firstCol = QWidget()
        self.firstCol.setLayout(QVBoxLayout())
        self.mainHL.addWidget(self.firstCol)
        self.currentRatingLab = QLabel(translate("protoPypeForm", "Rating: ") + self.PRating)
        self.previewSectionsPath = FreeCAD.getUserAppDataDir() + "Mod/quetzal/iconz/PreviewSections/"
        self.gradeimagepath = str()
        self.labImage = QLabel()
        self.fullimagepath = str()
        self.firstCol.layout().addWidget(self.currentRatingLab)
        # DN / NPS toggle row
        self._sizeSystemRow = QWidget()
        self._sizeSystemRow.setLayout(QHBoxLayout())
        self._sizeSystemRow.layout().setContentsMargins(0, 0, 0, 0)
        self._sizeSystemRow.layout().setSpacing(4)
        self._sizeSystemRow.layout().addWidget(
            QLabel(translate("protoPypeForm", "Size:")))
        self._btnDN  = QPushButton("DN")
        self._btnNPS = QPushButton("NPS")
        self._btnDN.setCheckable(True)
        self._btnNPS.setCheckable(True)
        self._btnDN.setFlat(True)
        self._btnNPS.setFlat(True)
        _ss_active   = "font-weight:bold; text-decoration:underline;"
        _ss_inactive = ""
        if qu and qu.get_size_system() == 1:
            self._btnDN.setChecked(False)
            self._btnNPS.setChecked(True)
            self._btnDN.setStyleSheet(_ss_inactive)
            self._btnNPS.setStyleSheet(_ss_active)
        else:
            self._btnDN.setChecked(True)
            self._btnNPS.setChecked(False)
            self._btnDN.setStyleSheet(_ss_active)
            self._btnNPS.setStyleSheet(_ss_inactive)
        self._sizeSystemRow.layout().addWidget(self._btnDN)
        self._sizeSystemRow.layout().addWidget(self._btnNPS)
        self._sizeSystemRow.layout().addStretch()
        self.firstCol.layout().addWidget(self._sizeSystemRow)
        self._btnDN.clicked.connect(lambda: self._setSizeSystem(0))
        self._btnNPS.clicked.connect(lambda: self._setSizeSystem(1))
        self.sizeList = QComboBox()
        self.firstCol.layout().addWidget(self.sizeList)
        self.firstCol.layout().addWidget(self.labImage)
        self.pipeDictList = []
        self.fileList = listdir(join(dirname(abspath(__file__)), "tablez"))
        self.fillSizes()
        self.PRatingsList = [
            s.lstrip(PType + "_").rstrip(".csv")
            for s in self.fileList
            if s.startswith(PType) and s.endswith(".csv")
        ]
        self.secondCol = QWidget()
        self.secondCol.setLayout(QFormLayout())
        self.existingObjs = QComboBox()
        self.existingObjs.addItem(translate("protoPypeForm","<none>"))
        try:
            self.existingObjs.addItems(
                [
                    o.Label
                    for o in FreeCAD.activeDocument().Objects
                    if hasattr(o, "PType") and o.PType == "PypeLine"
                ]
            )
        except:
            None
        self.combostandart = QComboBox()
        try:
            asmeflag = False
            dinflag = False
            apiflag = False
            asflag = False
            bsflag = False
            isoflag = False
            for fstadart in self.fileList:
                if fstadart.startswith("Flange_ASME") and asmeflag == False:
                    self.combostandart.addItem("ANSI/ASME")
                    asmeflag = True
                elif fstadart.startswith("Flange_DIN") and dinflag == False:
                    self.combostandart.addItem("DIN")
                    dinflag = True
                elif fstadart.startswith("Flange_API") and apiflag == False:
                    self.combostandart.addItem("API")
                    apiflag = True
                elif fstadart.startswith("Flange_AS") and asflag == False:
                    self.combostandart.addItem("AS")
                    asflag = True
                elif fstadart.startswith("Flange_BS") and bsflag == False:
                    self.combostandart.addItem("BS")
                    bsflag = True
                elif fstadart.startswith("Flange_ISO") and isoflag == False:
                    self.combostandart.addItem("ISO")
                    isoflag = True
            #TODO:Still doing some work here in order to sort standarts search
        except Exception as e:
            None 
        self.existingObjs.currentIndexChanged.connect(self.setCurrentPL)
        if FreeCAD.__activePypeLine__ and FreeCAD.__activePypeLine__ in [
            self.existingObjs.itemText(i) for i in range(self.existingObjs.count())
        ]:
            self.existingObjs.setCurrentIndex(self.existingObjs.findText(FreeCAD.__activePypeLine__))
        self.secondCol.layout().addRow(QLabel("Standard:"))
        self.secondCol.layout().addRow(self.combostandart)
        self.secondCol.layout().addRow(QLabel("Object to modify:"))
        self.secondCol.layout().addRow(self.existingObjs)
        # self.ratingList = QListWidget()
        self.ratingList = QComboBox()
        self.ratingList.addItems(self.PRatingsList)
        self.ratingList.setCurrentIndex(0)
        self.sizeList.setCurrentIndex(0)
        # self.ratingList.itemClicked.connect(self.changeRating)
        self.ratingList.currentTextChanged.connect(self.changeRating)
        self.sizeList.currentTextChanged.connect(self.changeSize)
        self.secondCol.layout().addRow(QLabel("Grade:"))
        self.secondCol.layout().addRow(self.ratingList)
        self.secondCol.layout().addRow(QLabel("Size:"))
        self.secondCol.layout().addRow(self.sizeList)
        self.btn_insert = QPushButton(translate("protoPypeForm", "Insert"))
        self.btn_insert.clicked.connect(self.insert)
        self.secondCol.layout().addRow(self.btn_insert)
        self.mainHL.addWidget(self.secondCol)
        self.resize(max(350, int(self.mw.width() / 4)), max(350, int(self.mw.height() / 2)))
        self.mainHL.setContentsMargins(0, 0, 0, 0)

    def insert(self):
        size_selected = self.pipeDictList[self.sizeList.currentIndex()]
        rating = self.ratingList.currentText()
        return size_selected,rating

    def setCurrentPL(self, PLName=None):
        if self.existingObjs.currentText() not in ["<none>", "<new>"]:
            FreeCAD.__activePypeLine__ = self.existingObjs.currentText()
        else:
            FreeCAD.__activePypeLine__ = None

    def fillSizes(self):
        self.sizeList.clear()
        for fileName in self.fileList:
            if fileName == self.PType + "_" + self.PRating + ".csv":
                f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
                reader = csv.DictReader(f, delimiter=";")
                self.pipeDictList = [DNx for DNx in reader]
                f.close()
                for row in self.pipeDictList:
                    if qu:
                        s = qu.format_size_label(row)
                    else:
                        s = row["PSize"]
                        if "OD" in row.keys():
                            s += " - " + row["OD"]
                        if "thk" in row.keys():
                            s += "x" + row["thk"]
                    self.sizeList.addItem(s)
                break

    def changeRating(self, s):
        self.PRating = s
        self.currentRatingLab.setText(translate("protoPypeForm", "Rating: ") + self.PRating)
        self.fillSizes()

    def _setSizeSystem(self, system):
        """Toggle the DN/NPS display on the size list without saving to prefs."""
        _ss_active   = "font-weight:bold; text-decoration:underline;"
        _ss_inactive = ""
        if system == 1:
            self._btnDN.setChecked(False)
            self._btnNPS.setChecked(True)
            self._btnDN.setStyleSheet(_ss_inactive)
            self._btnNPS.setStyleSheet(_ss_active)
        else:
            self._btnDN.setChecked(True)
            self._btnNPS.setChecked(False)
            self._btnDN.setStyleSheet(_ss_active)
            self._btnNPS.setStyleSheet(_ss_inactive)
        if qu:
            # Temporarily override the preference for this session
            qu.set_size_system(system)
        self.fillSizes()

    def changeSize(self, s):
        from os import makedirs, listdir
        from os.path import join

        idx = self.sizeList.currentIndex()
        # Always use the raw DN PSize from pipeDictList for the filename,
        # never the display label (which may be NPS or carry dimension suffixes).
        if 0 <= idx < len(self.pipeDictList):
            dn_psize = self.pipeDictList[idx].get("PSize", "")
        else:
            dn_psize = self.sizeList.currentText()

        # For two-port fittings (Tee, SocketTee, Reduct, Coupling) the
        # filename includes the secondary size: <rate><PSize>x<PSize2>.png
        dn_psize2 = ""
        try:
            # Tee / SocketTee: secondary branch list
            if hasattr(self, "_branchList") and hasattr(self, "_branchDictList"):
                bi = self._branchList.currentRow()
                if 0 <= bi < len(self._branchDictList):
                    dn_psize2 = self._branchDictList[bi].get("PSizeBranch", "")
            # Reduct: secondary OD2 list stores raw PSize2 strings
            elif hasattr(self, "_psize2_raw") and hasattr(self, "OD2list"):
                idx2 = self.OD2list.currentRow()
                if 0 <= idx2 < len(self._psize2_raw):
                    dn_psize2 = self._psize2_raw[idx2]
            # Coupling: secondary port-2 list
            elif hasattr(self, "_port2List") and hasattr(self, "_port2DictList"):
                pi = self._port2List.currentRow()
                if 0 <= pi < len(self._port2DictList):
                    dn_psize2 = self._port2DictList[pi].get("PSize2", "")
        except Exception:
            dn_psize2 = ""

        # Build the full size stem: "DN400" or "DN400xDN150"
        size_stem = str(dn_psize) + ("x" + str(dn_psize2) if dn_psize2 else "")

        rateselected = self.ratingList.currentText()
        preview_dir = self.previewSectionsPath + self.PType
        makedirs(preview_dir, exist_ok=True)

        # Canonical path: <dir>/<rating><size_stem>.png
        canonical_name = str(rateselected) + size_stem + ".png"
        self.gradeimagepath = canonical_name
        self.fullimagepath  = join(preview_dir, canonical_name)

        # Cache check: accept any file whose name starts with rate+size_stem
        prefix = str(rateselected) + size_stem
        cached_path = None
        if exists(self.fullimagepath):
            cached_path = self.fullimagepath
        else:
            try:
                for fname in listdir(preview_dir):
                    if fname.startswith(prefix) and fname.endswith(".png"):
                        cached_path = join(preview_dir, fname)
                        break
            except OSError:
                pass

        if cached_path:
            self.labImage.setPixmap(QPixmap(cached_path).scaledToWidth(180))
        else:
            # Clear selection so insert() creates at the origin, not at a port.
            saved_sel = FreeCADGui.Selection.getSelectionEx()
            FreeCADGui.Selection.clearSelection()
            self.insert()
            # Reset the created object to the origin in case
            # positionBySupport() moved it during recompute inside insert().
            preview_obj = FreeCAD.ActiveDocument.ActiveObject
            if preview_obj:
                preview_obj.Placement = FreeCAD.Placement()
                FreeCAD.ActiveDocument.recompute()
            self.capturePreviewProfile()
            last_obj = FreeCAD.ActiveDocument.ActiveObject
            if last_obj:
                FreeCAD.ActiveDocument.removeObject(last_obj.Name)
            # Restore the user's selection, skipping any objects that were
            # deleted during the preview (e.g. when the selected object was
            # the same as the preview object and got removed above).
            doc = FreeCAD.ActiveDocument
            for sx in saved_sel:
                try:
                    # Verify the object still exists in the document
                    if doc and not doc.getObject(sx.Object.Name):
                        continue
                    for sub in sx.SubElementNames:
                        FreeCADGui.Selection.addSelection(sx.Object, sub)
                    if not sx.SubElementNames:
                        FreeCADGui.Selection.addSelection(sx.Object)
                except Exception:
                    pass

    def findDN(self, DN):
        result = None
        for row in self.pipeDictList:
            if row["PSize"] == DN:
                result = row
                break
        return result

    def capturePreviewProfile(self):
        # Hide every object except the one just created (ActiveObject),
        # recording each object's previous Visibility so it can be restored.
        doc = FreeCAD.ActiveDocument
        preview_obj = doc.ActiveObject if doc else None
        vis_state = {}
        if doc:
            for obj in doc.Objects:
                if obj is preview_obj:
                    continue
                try:
                    vis_state[obj.Name] = obj.Visibility
                    if obj.Visibility:
                        obj.Visibility = False
                except Exception:
                    pass
        try:
            FreeCADGui.SendMsgToActiveView("ViewFit")
            view = FreeCADGui.ActiveDocument.ActiveView
            FreeCADGui.SendMsgToActiveView("OrthographicCamera")
            FreeCADGui.SendMsgToActiveView("ViewAxo")
            FreeCADGui.Selection.clearSelection()
            view.saveImage(self.fullimagepath, 300, 300, "Transparent")
        finally:
            # Restore visibility regardless of whether saveImage succeeded
            if doc:
                for obj in doc.Objects:
                    if obj.Name in vis_state:
                        try:
                            obj.Visibility = vis_state[obj.Name]
                        except Exception:
                            pass
