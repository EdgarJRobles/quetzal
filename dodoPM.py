# Copyright (C) 2018 oddtopus (www.github.com/oddtopus/dodo)
# Following code is derived from
# PieMenu widget for FreeCAD
#
# Copyright (C) 2016, 2017 triplus @ FreeCAD
# Copyright (C) 2015,2016 looo @ FreeCAD
# Copyright (C) 2015 microelly <microelly2@freecadbuch.de>

import FreeCAD
import FreeCADGui
import math
import platform
import csv
import pCmd
from PySide import QtCore
from PySide import QtGui
from os.path import join, dirname, abspath
from os import listdir

translate = FreeCAD.Qt.translate

# definition of style
styleButton = """
    QToolButton {
        background-color: lightGray;
        border: 1px outset silver;
    }

    QToolButton:disabled {
        background-color: darkGray;
    }

    QToolButton:hover {
        background-color: lightBlue;
    }

    QToolButton:checked {
        background-color: lightGreen;
    }

    QToolButton::menu-indicator {
        subcontrol-origin: padding;
        subcontrol-position: center center;
    }

    """
styleMenuClose = """
    QToolButton {
        background-color: rgba(60,60,60,235);
        border: 1px solid #1e1e1e;
    }

    QToolButton::menu-indicator {
        subcontrol-origin: padding;
        subcontrol-position: center center;
    }

    """
styleContainer = "QMenu{background: transparent}"
# styleCombo = ("""
# QComboBox {
# background: transparent;
# border: 1px solid transparent;
# }

# """)
# styleQuickMenu = ("padding: 5px")
iconClose = QtGui.QApplication.style().standardIcon(QtGui.QStyle.SP_DialogCloseButton)


def radiusSize(buttonSize):
    radius = str(buttonSize / 2)
    return "QToolButton {border-radius: " + radius + "px}"


def iconSize(buttonSize):
    icon = buttonSize  # / 3 * 2
    return icon


# definition of widgets
def closeButton(buttonSize=50):
    icon = iconSize(buttonSize)
    radius = radiusSize(buttonSize)
    button = QtGui.QToolButton()
    button.setProperty("ButtonX", 0)
    button.setProperty("ButtonY", 0)
    button.setGeometry(0, 0, buttonSize, buttonSize)
    button.setIconSize(QtCore.QSize(icon, icon))
    button.setIcon(iconClose)
    button.setStyleSheet(styleMenuClose + radius)
    button.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    def onButton():
        PieMenuInstance.hide()

    button.clicked.connect(onButton)
    return button


# main classes
class HoverButton(QtGui.QToolButton):
    def __init__(self, parent=None):
        super(HoverButton, self).__init__()

    def enterEvent(self, event):
        paramGet = FreeCAD.ParamGet("User parameter:BaseApp/PieMenu")
        mode = paramGet.GetString("TriggerMode")
        if self.defaultAction().isEnabled() and mode == "Hover":
            PieMenuInstance.hide()
            self.defaultAction().trigger()
        else:
            pass

    def mouseReleaseEvent(self, event):
        paramGet = FreeCAD.ParamGet("User parameter:BaseApp/PieMenu")
        mode = paramGet.GetString("TriggerMode")
        if self.defaultAction().isEnabled():
            PieMenuInstance.hide()
            self.defaultAction().trigger()
        else:
            pass


class PieMenu:
    def __init__(self):
        self.radius = 100
        self.buttons = []
        self.buttonSize = 32
        self.menu = QtGui.QMenu(mw)
        self.menuSize = 0
        self.menu.setStyleSheet(styleContainer)
        self.menu.setWindowFlags(
            self.menu.windowFlags() | QtCore.Qt.FramelessWindowHint
        )
        self.menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        if compositingManager:
            pass
        else:
            self.menu.setAttribute(QtCore.Qt.WA_PaintOnScreen)

    def add_commands(self, commands):
        # paramGet = FreeCAD.ParamGet("User parameter:BaseApp/PieMenu")
        for i in self.buttons:
            i.deleteLater()
        self.buttons = []
        if len(commands) == 0:
            commandNumber = 1
        else:
            commandNumber = len(commands)
        valueRadius = 100
        valueButton = 50
        self.radius = valueRadius
        self.buttonSize = valueButton
        if commandNumber == 1:
            angle = 0
            buttonSize = self.buttonSize
        else:
            angle = 2 * math.pi / commandNumber
            buttonRadius = math.sin(angle / 2) * self.radius
            buttonSize = math.trunc(2 * buttonRadius / math.sqrt(2))
        angleStart = 3 * math.pi / 2 - angle
        if buttonSize > self.buttonSize:
            buttonSize = self.buttonSize
        else:
            pass
        radius = radiusSize(buttonSize)
        icon = iconSize(buttonSize)
        if windowShadow:
            pass
        else:
            self.menuSize = valueRadius * 2 + buttonSize + 4
            if self.menuSize < 90:
                self.menuSize = 90
            else:
                pass
            self.menu.setMinimumWidth(self.menuSize)
            self.menu.setMinimumHeight(self.menuSize)
        num = 1
        for i in commands:
            button = HoverButton()
            button.setParent(self.menu)
            button.setAttribute(QtCore.Qt.WA_Hover)
            button.setStyleSheet(styleButton + radius)
            button.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            button.setDefaultAction(commands[commands.index(i)])
            button.setGeometry(0, 0, buttonSize, buttonSize)
            button.setIconSize(QtCore.QSize(icon, icon))
            button.setProperty(
                "ButtonX", self.radius * (math.cos(angle * num + angleStart))
            )
            button.setProperty(
                "ButtonY", self.radius * (math.sin(angle * num + angleStart))
            )
            self.buttons.append(button)
            num = num + 1
        buttonClose = closeButton()
        buttonClose.setParent(self.menu)
        self.buttons.append(buttonClose)
        if compositingManager:
            pass
        else:
            for i in self.buttons:
                i.setAttribute(QtCore.Qt.WA_PaintOnScreen)

    def hide(self):
        for i in self.buttons:
            i.hide()
        self.menu.hide()

    def showAtMouse(self):
        actionDict = dict(
            [
                (a.objectName(), a)
                for a in FreeCADGui.getMainWindow().findChildren(QtGui.QAction)
            ]
        )
        try:
            actions.pop("")
        except:
            pass
        commands = [actionDict[n] for n in toolList if n in actionDict]
        self.add_commands(commands)
        if self.menu.isVisible():
            self.hide()
        else:
            if windowShadow:
                pos = mw.mapFromGlobal(QtGui.QCursor.pos())
                self.menu.popup(QtCore.QPoint(mw.pos()))
                self.menu.setGeometry(mw.geometry())
                for i in self.buttons:
                    i.move(
                        i.property("ButtonX") + pos.x() - i.width() / 2,
                        i.property("ButtonY") + pos.y() - i.height() / 2,
                    )
                    i.setVisible(True)
                for i in self.buttons:
                    i.repaint()
            else:
                pos = QtGui.QCursor.pos()
                for i in self.buttons:
                    i.move(
                        i.property("ButtonX") + (self.menuSize - i.size().width()) / 2,
                        i.property("ButtonY") + (self.menuSize - i.size().height()) / 2,
                    )
                    i.setVisible(True)
                self.menu.popup(
                    QtCore.QPoint(
                        pos.x() - self.menuSize / 2, pos.y() - self.menuSize / 2
                    )
                )


# QkMenus:


class QkMenu(object):
    def setupUi(self, Dialog):
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.comboRating = QtGui.QComboBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboRating.sizePolicy().hasHeightForWidth())
        self.comboRating.setSizePolicy(sizePolicy)
        self.comboRating.setObjectName("comboRating")
        self.gridLayout.addWidget(self.comboRating, 1, 1, 1, 1)
        self.labRating = QtGui.QLabel("Rating:", Dialog)
        self.labRating.setAlignment(QtCore.Qt.AlignCenter)
        self.labRating.setObjectName("labRating")
        self.gridLayout.addWidget(self.labRating, 1, 0, 1, 1)
        self.comboPL = QtGui.QComboBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboPL.sizePolicy().hasHeightForWidth())
        self.comboPL.setSizePolicy(sizePolicy)
        self.comboPL.setObjectName("comboPL")
        self.comboPL.addItem("<none>")
        self.gridLayout.addWidget(self.comboPL, 0, 1, 1, 1)
        self.btnGO = QtGui.QPushButton("GO", Dialog)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.MinimumExpanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btnGO.sizePolicy().hasHeightForWidth())
        self.btnGO.setSizePolicy(sizePolicy)
        self.btnGO.setMinimumSize(QtCore.QSize(50, 50))
        self.btnGO.setMaximumSize(QtCore.QSize(80, 80))
        self.btnGO.setObjectName("btnGO")
        self.gridLayout.addWidget(self.btnGO, 0, 2, 2, 1)
        self.labPL = QtGui.QLabel("PypeLine: ", Dialog)
        self.labPL.setAlignment(QtCore.Qt.AlignCenter)
        self.labPL.setObjectName("labPL")
        self.gridLayout.addWidget(self.labPL, 0, 0, 1, 1)
        self.listSize = QtGui.QListWidget(Dialog)
        self.listSize.setStyleSheet("QListWidget{background: transparent}")
        self.listSize.setObjectName("listSize")
        for i in range(3):
            self.listSize.addItem("item " + str(i))
        self.gridLayout.addWidget(self.listSize, 2, 0, 1, 3)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        Dialog.setTabOrder(self.listSize, self.btnGO)
        Dialog.setTabOrder(self.btnGO, self.comboRating)
        Dialog.setTabOrder(self.comboRating, self.comboPL)


class DialogQM(QtGui.QDialog):
    def __init__(self, winTitle=translate("DialogQM", "Quick Insert"), PType="Pipe"):
        super(DialogQM, self).__init__(FreeCADGui.getMainWindow())
        self.setWindowTitle(winTitle)
        self.setObjectName("DQkMenu")
        self.resize(300, 300)
        self.setStyleSheet(("Qself{background: transparent}"))
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.QM = QkMenu()
        self.QM.setupUi(self)
        self.QM.btnGO.clicked.connect(self.go)
        self.QM.comboRating.currentIndexChanged.connect(self.updateSizes)
        self.QM.comboPL.currentIndexChanged.connect(self.setCurrentPL)
        ### pype stuff ###
        self.PType = PType
        self.PRating = ""
        self.dictList = list()
        self.files = listdir(join(dirname(abspath(__file__)), "tablez"))
        ratings = [
            s.lstrip(PType + "_").rstrip(".csv")
            for s in self.files
            if s.startswith(PType) and s.endswith(".csv")
        ]
        if ratings:  # adds ratings in combo
            self.QM.comboRating.addItems(ratings)
            self.updateSizes()
        self.updatePL()
        # self.show()

    def show(self):
        self.updatePL()
        super(DialogQM, self).show()

    def setCurrentPL(self, PLName=None):
        if self.QM.comboPL.currentText() not in ["<none>", "<new>"]:
            FreeCAD.__activePypeLine__ = self.QM.comboPL.currentText()
        else:
            FreeCAD.__activePypeLine__ = None

    def updateSizes(self):
        self.QM.listSize.clear()
        self.PRating = self.QM.comboRating.currentText()
        for fileName in self.files:  # adds sizes in list
            if fileName == self.PType + "_" + self.PRating + ".csv":
                f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
                reader = csv.DictReader(f, delimiter=";")
                self.dictList = [DNx for DNx in reader]
                f.close()
                for row in self.dictList:
                    s = row["PSize"]
                    if "OD" in row.keys():
                        s += " - " + row["OD"]
                    if "thk" in row.keys():
                        s += "x" + row["thk"]
                    self.QM.listSize.addItem(s)
                break

    def updatePL(self):
        if FreeCAD.activeDocument():
            pypelines = [
                o.Label
                for o in FreeCAD.activeDocument().Objects
                if hasattr(o, "PType") and o.PType == "PypeLine"
            ]
        else:
            pypelines = []
        if pypelines:  # updates pypelines in combo
            pl = FreeCAD.__activePypeLine__
            self.QM.comboPL.clear()
            pypelines.insert(0, "<none>")
            self.QM.comboPL.addItems(pypelines)
            if pl and pl in pypelines:
                self.QM.comboPL.setCurrentIndex(self.QM.comboPL.findText(pl))

    def go(self):
        self.close()


# DEFINITION OF QKMENUS DIALOGS: alternative to the commands created in CPipe.py


class pQM(DialogQM):
    def __init__(self):
        super(pQM, self).__init__("Insert pipe", "Pipe")
        self.QM.lineEdit = QtGui.QLineEdit(self)
        self.QM.lineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.QM.lineEdit.setObjectName("lineEdit")
        self.QM.gridLayout.addWidget(self.QM.lineEdit, 3, 0, 1, 3)
        self.QM.lineEdit.setPlaceholderText("<length>")
        self.QM.lineEdit.setValidator(QtGui.QDoubleValidator())
        self.QM.lineEdit.validator().setBottom(0)

    def go(self):
        d = self.dictList[self.QM.listSize.currentRow()]
        if self.QM.lineEdit.text():
            L = float(self.QM.lineEdit.text())
        else:
            L = 1000
        pCmd.doPipes(
            [d["PSize"], float(d["OD"]), float(d["thk"]), L], FreeCAD.__activePypeLine__
        )
        super(pQM, self).go()


class eQM(DialogQM):
    def __init__(self):
        super(eQM, self).__init__("Insert elbow", "Elbow")
        self.QM.lineEdit = QtGui.QLineEdit(self)
        self.QM.lineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.QM.lineEdit.setObjectName("lineEdit")
        self.QM.gridLayout.addWidget(self.QM.lineEdit, 3, 0, 1, 3)
        self.QM.lineEdit.setPlaceholderText("<angle>")
        self.QM.lineEdit.setValidator(QtGui.QDoubleValidator())
        self.QM.lineEdit.validator().setBottom(0)
        self.QM.lineEdit.validator().setTop(90)
        self.QM.lineEdit2 = QtGui.QLineEdit(self)
        self.QM.lineEdit2.setAlignment(QtCore.Qt.AlignCenter)
        self.QM.lineEdit2.setObjectName("lineEdit2")
        self.QM.gridLayout.addWidget(self.QM.lineEdit2, 4, 0, 1, 3)
        self.QM.lineEdit2.setPlaceholderText("<radius>")
        self.QM.lineEdit2.setValidator(QtGui.QDoubleValidator())

    def go(self):
        d = self.dictList[self.QM.listSize.currentRow()]
        if self.QM.lineEdit.text():
            ang = float(self.QM.lineEdit.text())
            if ang > 180:
                ang = 180
                self.QM.lineEdit.setText("180")
        else:
            ang = 90
        if self.QM.lineEdit2.text():
            rad = float(self.QM.lineEdit2.text())
            if rad < float(d["OD"]) / 2:
                rad = float(d["OD"]) / 2 * 1.1
                self.QM.lineEdit.setText(str(rad))
        else:
            rad = d["BendRadius"]
        pCmd.doElbow(
            [d["PSize"], float(d["OD"]), float(d["thk"]), ang, rad],
            FreeCAD.__activePypeLine__,
        )
        super(eQM, self).go()


class fQM(DialogQM):
    def __init__(self):
        super(fQM, self).__init__("Insert flange", "Flange")

    def go(self):
        d = self.dictList[self.QM.listSize.currentRow()]
        proplist = [
            d["PSize"],
            d["FlangeType"],
            float(d["D"]),
            float(d["d"]),
            float(d["df"]),
            float(d["f"]),
            float(d["t"]),
            int(d["n"]),
        ]
        try:  # for raised-face
            proplist.append(float(d["trf"]))
            proplist.append(float(d["drf"]))
        except:
            pass
        try:  # for welding-neck
            proplist.append(float(d["twn"]))
            proplist.append(float(d["dwn"]))
            proplist.append(float(d["ODp"]))
        except:
            pass
        pCmd.doFlanges(proplist, FreeCAD.__activePypeLine__)
        super(fQM, self).go()


class vQM(DialogQM):
    def __init__(self):
        super(vQM, self).__init__("Insert valve", "Valve")
        self.QM.slider = QtGui.QSlider(self)
        self.QM.slider.setOrientation(QtCore.Qt.Horizontal)
        self.QM.slider.setObjectName("slider")
        self.QM.gridLayout.addWidget(self.QM.slider, 4, 0, 1, 3)

    def go(self):
        d = self.dictList[self.QM.listSize.currentRow()]
        proplist = [
            d["PSize"],
            d["VType"],
            float(d["OD"]),
            float(d["ID"]),
            float(d["H"]),
            float(d["Kv"]),
        ]
        pCmd.doValves(proplist, FreeCAD.__activePypeLine__, self.QM.slider.value())
        super(vQM, self).go()


class cQM(DialogQM):
    def __init__(self):
        super(cQM, self).__init__("Insert cap", "Cap")

    def go(self):
        d = self.dictList[self.QM.listSize.currentRow()]
        proplist = []
        pCmd.doCaps(
            [d["PSize"], float(d["OD"]), float(d["thk"])], FreeCAD.__activePypeLine__
        )
        super(cQM, self).go()


# create instances of qkMenu dialogs
pqm = pQM()
eqm = eQM()
fqm = fQM()
vqm = vQM()
cqm = cQM()

# main
mw = FreeCADGui.getMainWindow()
toolList = [
    "pipeQM",
    "elbowQM",
    "flangeQM",
    "valveQM",
    "capQM",
]  # ["Quetzal_InsertPipe","Quetzal_InsertElbow","Quetzal_InsertReduct","Quetzal_InsertCap","Quetzal_InsertValve","Quetzal_InsertFlange","Quetzal_InsertUbolt"]
compositingManager = True
if QtCore.qVersion() < "5":
    windowShadow = False
else:
    windowShadow = True
if platform.system() == "Linux":
    try:
        if QtGui.QX11Info.isCompositingManagerRunning():
            windowShadow = True
        else:
            compositingManager = False
    except AttributeError:
        windowShadow = True
if platform.system() == "Windows":
    windowShadow = True
PieMenuInstance = PieMenu()
FreeCAD.__dodoPMact__ = QtGui.QAction(mw)
FreeCAD.__dodoPMact__.setObjectName("PieTest")
FreeCAD.__dodoPMact__.setShortcut(QtGui.QKeySequence("Z"))
FreeCAD.__dodoPMact__.triggered.connect(PieMenuInstance.showAtMouse)
mw.addAction(FreeCAD.__dodoPMact__)
