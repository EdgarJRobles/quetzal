# SPDX-License-Identifier: LGPL-3.0-or-later

insert_tube_tooltip = (
    "Create a tube not referenced to a single wire\n"
    "______________________________________________________________________________________________________________________________________ \n"
	"Usage \n"
	"Preselect the following: \n"
	" • Choose one o more wire the 3D view by clicking on it. if no wire is Preselect it will create a last lenght done vertical tube \n"
	"\n"
    "Apply the function: \n"
    "A window will pop up order to select first wall pipe thickness standart follow by DN standart\n"
    "then press insert button to create tube.\n"
    "Apply button:\n"
    "It will modify preselected tubes with new choose option selected on window pop up"
    "\n"
    "Invert button:\n"
    "It will modify preselected tubes with new tube orientation rotating 180 degre tube using head tube side as pivot point\n"
    "\n"
	)
frameit_tooltip = (
    "Relocate existing & selected beam at Preselected edge\n"
    "_____________________________________________________ \n"
	"Usage \n"
    "Preselected the following:\n"
    "• Choose a existing beam at current document then select a edge target where beam will be relocated"
    "Press [ESC] to cancel relocation function"
)
framebranchmanager_tooltip = (
    "Create a framebranch object with beam nest on tree. this object create parametric frames allowing change base sketch, path or wire and adapt to new dimentions\n"
    "______________________________________________________________________________________________________________________________________ \n"
	"Usage \n"
    "Preselected the following:\n"
    "• Choose a existing sketch/path(s) then choose profile to be applied on pop up windows\n"
)
spinsect_tooltip = (
    "Spin beam object(s) selected around the Z axis of its wire/sketch shape  by 45 degrees each click\n"
    "______________________________________________________________________________________________________________________________________ \n"
	"Usage \n"
    "Preselected the following:\n"
    "• Select beam object(s) to spin\n"
)
reversebeam_tooltip = (
    "Spin beam object(s) selected around the X axis of its wire/sketch shape  by 180 degrees each click\n"
    "______________________________________________________________________________________________________________________________________ \n"
	"Usage \n"
    "Preselected the following:\n"
    "• Select beam object(s) to spin\n"
    "Note: - if one edge of the object is selected, that is used\n"
    "as the pivot of rotation."
)
shiftbeam_tooltip = (
    "Dialog to translate and copy objects.\n"
    "______________________________________________________________________________________________________________________________________ \n"
    "• [x/y/z] textboxes: direct input of amount of translation in each direction"
    "• [Multiple] textbox: the multiple coefficient of the translation amount.\n"
    "• [Steps] textbox: the denominator of the translation amount. It's used when the amount of translation is to be covered in some steps.\n"
    "• [move/copy] radiobuttons: to select if the selected objects shall be copied or only translated.\n"
    "• [Displacement] button: takes the amount and direction of translation from the distance of selected entities (points, edges, faces).\n"
    "• [Vector] button: defines the amount and direction of translation by the orientation and length of the selected edge.\n"
    "• [OK] button: execute the translation\n"
    "• [Cancel]: exits\n"
)
levelbeam_tooltip = (
    "Tool to flush the parallel faces of two objects.\n"
    "_________________________________________________ \n"
	"Usage \n"
    "Preselected the following:\n"
    "1.- Select fisrt beam face to take as reference\n"
    "2.- Select second beam face to translate and match faces coplanar\n"
    "Note: - actually the command takes to the same level, respect the position and orientation \n of the first face selected, the center-of-mass of all faces selected. Thus it translates the objects even if the faces are not parallel.\n"
)
pivotbeam_tooltip = (
    "Tool to pivot & copy around one edge or principal X/Y/Z axis\n"
    "_________________________________________________ \n"
	"Usage \n"
    "Preselected the following:\n"
    "1.- Select fisrt beam to modify rotation angle or press 's' key\n"
    "2.- Choose a principal axis with x, y , z button or select a edge then press 'assign axis' button \n"
    "3.- Press 'x' key to execute rotation\n"
    "Note: - actually the command takes to the same level, respect the position and orientation \n of the first face selected, the center-of-mass of all faces selected. Thus it translates the objects even if the faces are not parallel.\n"
)
elbow_tooltip = (
    "Tool to insert a elbow based on gui option selections\n"
    "_________________________________________________ \n"
	"Usage \n"
    "1.- Select edge or edges where you want to attach the elbow; should select circular end edges\n"
    "2.- Choose elbow type according your needs on the GUI\n"
    "3.- Press 'insert' button\n"
    "Note: - There is dial available in case inserted elbow does not have right orientation\n"
)
