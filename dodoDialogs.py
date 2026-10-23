# SPDX-License-Identifier: LGPL-3.0-or-later

from os import listdir
from os.path import abspath, dirname, join, exists

import FreeCAD
import FreeCADGui
from PySide.QtCore import *
from PySide.QtGui import *

from quetzal.domain.errors import CatalogNotFoundError
from quetzal.domain.preview import PreviewKey
from quetzal.infrastructure.catalog import default_catalog_repository
from quetzal.infrastructure.freecad.preview import default_preview_service

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
        preview_service=None,
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
        self._preview = preview_service or default_preview_service()
        self.previewSectionsPath = str(self._preview.cache.paths.write_root) + "/"
        self.gradeimagepath = str()
        self.labImage = QLabel()
        self.fullimagepath = str()
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
        self.firstCol.layout().addStretch()
        self.firstCol.layout().addWidget(self.labImage)
        self.pipeDictList = []
        self.fileList = listdir(join(dirname(abspath(__file__)), "tablez"))
        self.fillSizes()
        # Use slice-based prefix/suffix removal instead of lstrip/rstrip.
        # lstrip and rstrip strip individual characters from a set, not a
        # literal substring, so they corrupt ratings like "generic" by also
        # removing the trailing 'c' (which appears in the ".csv" character set).
        _prefix = PType + "_"
        _suffix = ".csv"
        self.PRatingsList = [
            s[len(_prefix) : len(s) - len(_suffix)]
            for s in self.fileList
            if s.startswith(_prefix) and s.endswith(_suffix)
        ]
        self.secondCol = QWidget()
        self.secondCol.setLayout(QFormLayout())
        #create and populate combobox with existing Objects
        self.existingObjs = QComboBox()
        if FreeCAD.ActiveDocument.Objects is not None:
            self.existingObjs.addItems(self.getPL())
        self.existingObjs.addItem(translate("protoPypeForm","<none>"))
        self.existingObjs.activated.connect(self.on_activatedExistingObjects)
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
            pass 
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
        # Block signals during initial index set so that changeRating does
        # not fire before the subclass has finished building its controls.
        # Subclasses call fillSizes() explicitly after their __init__ completes.
        self.ratingList.blockSignals(True)
        self.ratingList.setCurrentIndex(0)
        self.ratingList.blockSignals(False)
        self.sizeList.setCurrentIndex(0)
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
            pl_obj=FreeCAD.ActiveDocument.getObject(FreeCAD.__activePypeLine__)
            self.ratingList.setCurrentText(pl_obj.PRating)
            sizetext=self.sizeList.itemText(self.sizeList.findText(pl_obj.PSize))
            self.sizeList.setCurrentText(sizetext)
        else:
            FreeCAD.__activePypeLine__ = None

    def getPL(self):
        "Get a name list of Ptype on active document"
        temp_ptypelist = list()
        for item in FreeCAD.ActiveDocument.Objects:
            if hasattr(item, "PType") and item.PType == self.PType:
                temp_ptypelist.append(item.Name)
        return temp_ptypelist

    def fillSizes(self):
        """Populate the size combo from the shared catalogue repository."""
        self.sizeList.clear()
        try:
            table = default_catalog_repository().get_table(self.PType, self.PRating)
        except CatalogNotFoundError as exc:
            self.pipeDictList = []
            FreeCAD.Console.PrintWarning(f"{exc}\n")
            return
        self.pipeDictList = table.to_dicts()
        for row in self.pipeDictList:
            if qu:
                label = qu.format_size_label(row)
            else:
                label = row["PSize"]
                if "OD" in row.keys():
                    label += " - " + row["OD"]
                if "thk" in row.keys():
                    label += "x" + row["thk"]
            self.sizeList.addItem(label)

    def changeRating(self, s):
        """Handle a rating (grade) selection change.

        Captures the currently selected PSize, reloads the size list inside
        sizeList.blockSignals (preventing changeSize from firing for every
        item added during reload), restores the previously selected size in
        the new list if possible, then calls onRatingChanged(s) so subclasses
        can perform any additional post-fill actions without needing to
        disconnect and reconnect this signal.
        """
        # Capture the currently selected PSize so it can be restored after
        # the size list is reloaded for the new rating.
        cur_idx = self.sizeList.currentIndex()
        cur_psize = None
        if hasattr(self, "pipeDictList") and 0 <= cur_idx < len(self.pipeDictList):
            cur_psize = self.pipeDictList[cur_idx].get("PSize")
        # Also check a _uniqueSizeList if the form uses one (Tee, Coupling)
        if cur_psize is None and hasattr(self, "_uniqueSizeList"):
            if 0 <= cur_idx < len(self._uniqueSizeList):
                cur_psize = self._uniqueSizeList[cur_idx]
        self.PRating = s
        # Reload the size list with signals blocked so that changeSize is
        # not triggered for every item added during the reload.
        self.sizeList.blockSignals(True)
        try:
            self.fillSizes()
        finally:
            self.sizeList.blockSignals(False)

        # Try to restore the previously selected PSize in the new list.
        # import here to avoid a circular dependency at module load time.
        try:
            import pCmd as _pCmd
            _pCmd.preserveSelectSizeByPSize(self, cur_psize)
        except Exception:
            self.sizeList.setCurrentIndex(-1)

        # Subclass hook: called after the size list has been reloaded and
        # the size selection restored.  Override this (not changeRating)
        # for any form-specific post-fill actions.
        self.onRatingChanged(s)

    def onRatingChanged(self, s):
        """Hook called by changeRating after the size list has been reloaded.

        Subclasses override this method to perform form-specific post-fill
        actions (e.g. refreshing a secondary list, updating visibility of
        dependent controls) without needing to disconnect and reconnect the
        ratingList.currentTextChanged signal.
        The default implementation does nothing.
        """
        pass

    def _previewReady(self):
        """Return True when enough selections have been made to generate a preview.

        The base implementation requires that both the rating list and the size
        list have a valid (>= 0) current index.  Forms that also require a
        secondary size selection (branch, OD2, port-2) override this method to
        additionally check their secondary list.

        changeSize() calls this guard before doing any cache lookup or
        image-generation work, so a partially-configured form never triggers
        an accidental insert().
        """
        if self.ratingList.currentIndex() < 0:
            return False
        if self.sizeList.currentIndex() < 0:
            return False
        return True

    def on_activatedExistingObjects(self,index):
        #check pipetype objects exist to update combobox
        if FreeCAD.ActiveDocument.Objects is not None:
            allpl=self.getPL()
            for pl in allpl:
                res=self.existingObjs.findText(pl)
                if res == -1:
                    self.existingObjs.addItem(pl)
        else:
            FreeCAD.__activePypeLine__ = None
 
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

    def _preview_variant(self):
        """Optional discriminator for families with repeated sizes (angle, type...)."""
        return ""

    def _preview_factory(self):
        return self.insert

    def _preview_key(self):
        if not self._previewReady():
            return None
        idx = self.sizeList.currentIndex()
        if hasattr(self, "_uniqueSizeList") and 0 <= idx < len(self._uniqueSizeList):
            size = self._uniqueSizeList[idx]
        elif 0 <= idx < len(self.pipeDictList):
            size = self.pipeDictList[idx].get("PSize", "")
        else:
            size = self.sizeList.currentText()

        secondary = ""
        try:
            if hasattr(self, "_branchList") and hasattr(self, "_branchDictList"):
                branch_index = self._branchList.currentRow()
                if 0 <= branch_index < len(self._branchDictList):
                    secondary = self._branchDictList[branch_index].get("PSizeBranch", "")
            elif hasattr(self, "_psize2_raw") and hasattr(self, "OD2list"):
                index = self.OD2list.currentRow()
                if 0 <= index < len(self._psize2_raw):
                    secondary = self._psize2_raw[index]
            elif hasattr(self, "_port2List") and hasattr(self, "_port2DictList"):
                port_index = self._port2List.currentRow()
                if 0 <= port_index < len(self._port2DictList):
                    secondary = self._port2DictList[port_index].get("PSize2", "")
        except Exception:
            secondary = ""

        return PreviewKey(
            family=self.PType,
            rating=self.ratingList.currentText(),
            size=str(size),
            secondary=str(secondary),
            variant=self._preview_variant(),
        )

    def changeSize(self, s):
        key = self._preview_key()
        if key is None:
            self.labImage.clear()
            return
        path = self._preview.image_for(key, self._preview_factory())
        if path is None:
            self.labImage.clear()
            return
        self.gradeimagepath = path.name
        self.fullimagepath = str(path)
        self.labImage.setPixmap(QPixmap(str(path)).scaledToWidth(180))


    def findDN(self, DN):
        result = None
        for row in self.pipeDictList:
            if row["PSize"] == DN:
                result = row
                break
        return result

    def capturePreviewProfile(self):
        doc = FreeCAD.ActiveDocument
        if not doc:
            return
        #some object classes were having trouble finding the correct path - seems to be an issue of / vs \ in the file path
        import os as _os
        _img_dir = _os.path.dirname(self.fullimagepath)
        if _img_dir:
            _os.makedirs(_img_dir, exist_ok=True)

        view = FreeCADGui.ActiveDocument.ActiveView
        preview_obj = doc.ActiveObject
        vis_state = {}

        # Hide other objects
        for obj in doc.Objects:
            if obj == preview_obj:
                if hasattr(obj,"PType") and obj.PType=="Valve":
                    obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0.0,0.7071,0.7071),180)
                    obj.touch()
                continue
            try:
                vis_state[obj.Name] = obj.Visibility
                obj.Visibility = False
            except:
                pass

        try:
            # Set to Axometric and Orthographic
            view.viewAxometric()
            view.setCameraType("Orthographic")
            
            # Fit the object to the screen
            view.fitAll() 
            
            # Allow the 3D view to update its camera 
            # before the saveImage command fires.
            from PySide.QtCore import QCoreApplication
            QCoreApplication.processEvents() 
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.updateGui()
            
            # Save the image
            view.saveImage(self.fullimagepath, 300, 300, "Transparent")
            
        finally:
            # Restore visibility
            for name, state in vis_state.items():
                try:
                    target = doc.getObject(name)
                    if target:
                        target.Visibility = state
                except:
                    pass
