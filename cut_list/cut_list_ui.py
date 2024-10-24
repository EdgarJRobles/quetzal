import FreeCAD,FreeCADGui,Part
import os

from FreeCAD import Units
from PySide import QtCore

from . import RESOURCE_PATH
from . import cut_list_creation


class cutListUI:
    def __init__(self):
        uiPath = os.path.join(RESOURCE_PATH, "cut_list_dialog.ui")
        # this will create a Qt widget from our ui file
        self.form = FreeCADGui.PySideUic.loadUi(uiPath)

        # Set the Default Values and allow only Positive Values
        maxStockDefault = Units.parseQuantity("6m")
        cutWidthDefault = Units.parseQuantity("5mm")

        self.form.max_stock_length.setProperty("value",maxStockDefault)
        self.form.max_stock_length.setProperty("minimum",0.0) 

        self.form.cut_width.setProperty("value",cutWidthDefault)
        self.form.cut_width.setProperty("minimum",0.0)

        # Set Default Options
        self.form.use_nesting.stateChanged.connect(self.useNestingToggle) 

        self.form.use_nesting.setChecked(False)
    
        self.form.use_group_by_size.setChecked(True)
        
        # Update the UI
        self.useNestingToggle()
        self.UpdateProfileList()
        self.selectProfilefromSelection()
        

    def selectProfilefromSelection(self):
        """ Select the selected Profile if some is used
        """
        for selected in FreeCADGui.Selection.getSelection():
            selLabel = selected.Label
            found = self.form.profile_list.findItems(selLabel,QtCore.Qt.MatchExactly)
            if len(found)>0:
                item = found[0]
                item.setSelected(True)
                


    def useNestingToggle(self):
        """ Toggle the Nesting Options depending on the Need
        """
        state = self.form.use_nesting.checkState()
        self.form.max_stock_length.setProperty("enabled",state)
        self.form.cut_width.setProperty("enabled",state)

    def UpdateProfileList(self):
        """ Add all Sketches/Profiles/Sections that can be used for the Beam Creation
        """

        sketches = [s.Label for s in FreeCAD.ActiveDocument.Objects if s.TypeId=="Sketcher::SketchObject"]
        obj2D = [s.Label for s in FreeCAD.ActiveDocument.Objects if hasattr (s,"Shape") and s.Shape.Faces and not s.Shape.Solids]
        
        self.form.profile_list.clear()
        self.form.profile_list.addItems(sketches)          
      
        self.form.profile_list.addItems(obj2D)
    
 
    def accept(self): 
        """ Start the Creation of the Cut List
        """
        # Get all selected Profiles
        sel = self.form.profile_list.currentItem()
        profils = []
        for item in  self.form.profile_list.selectedItems():
            profils.append(item.text())

        if profils == []:
            # Do not try to create a cut list with an empty selection
            # TODO: Add Message Box
            return
        # Get the Nesting Information or set the default
        if self.form.use_nesting.checkState() == False:
            maxStockLength = Units.parseQuantity("0mm")
            cutWidth = Units.parseQuantity("0mm")
        else:
            maxStockLength = self.form.max_stock_length.property('value')
            cutWidth = self.form.cut_width.property('value')
        
        # Generate the Cut List
        cut_list_creation.createCutlist(profils,
                                     maxStockLength,
                                     cutWidth,
                                     self.form.use_group_by_size.checkState())
        
        FreeCADGui.Control.closeDialog()
    
    def reject(self):
        FreeCADGui.Control.closeDialog()
        
def openCutListDialog():
    panel = cutListUI()
    FreeCADGui.Control.showDialog(panel)