# SPDX-License-Identifier: LGPL-3.0-or-later

__title__ = "pypeTools functions"
import FreeCAD
import FreeCADGui
import Part
import fCmd
import pFeatures
from DraftVecUtils import rounded
from quetzal_config import get_icon_path

from math import degrees

objToPaint = ["Pipe", "Elbow", "Reduct", "Flange", "Cap", "Tee"]


__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"
X = FreeCAD.Vector(1, 0, 0)
Y = FreeCAD.Vector(0, 1, 0)
Z = FreeCAD.Vector(0, 0, 1)

translate = FreeCAD.Qt.translate
QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP

############### AUX FUNCTIONS ######################


def readTable(fileName="Pipe_SCH-STD.csv"):
    """
    readTable(fileName)
    Returns the list of dictionaries read from file in ./tablez
      fileName: the file name without path; default="Pipe_SCH-STD.csv"
    """
    from os.path import join, dirname, abspath
    import csv

    f = open(join(dirname(abspath(__file__)), "tablez", fileName), "r")
    reader = csv.DictReader(f, delimiter=";")
    table = []
    for row in reader:
        table.append(row)
    f.close()
    return table


def shapeReferenceAxis(obj=None, axObj=None):
    # function to get the reference axis of the shape for rotateTheTubeAx()
    # used in rotateTheTubeEdge() and pipeForms.rotateForm().getAxis()
    """
    shapeReferenceAxis(obj, axObj)
    Returns the direction of an axis axObj
    according the original Shape orientation of the object obj
    If arguments are None axObj is the normal to one circular edge selected
    and obj is the object selected.
    """
    if obj == None and axObj == None:
        selex = FreeCADGui.Selection.getSelectionEx()
        if len(selex) == 1 and len(selex[0].SubObjects) > 0:
            sub = selex[0].SubObjects[0]
            if sub.ShapeType == "Edge" and sub.curvatureAt(0) > 0:
                axObj = sub.tangentAt(0).cross(sub.normalAt(0))
                obj = selex[0].Object
    X = obj.Placement.Rotation.multVec(FreeCAD.Vector(1, 0, 0)).dot(axObj)
    Y = obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 1, 0)).dot(axObj)
    Z = obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1)).dot(axObj)
    axShapeRef = FreeCAD.Vector(X, Y, Z)
    return axShapeRef


def isPipe(obj):
    "True if obj is a tube"
    return hasattr(obj, "PType") and obj.PType == "Pipe"


def isElbow(obj):
    "True if obj is an elbow"
    return hasattr(obj, "PType") and obj.PType == "Elbow"

def isTee(obj):
    "True if obj is a Tee"
    return hasattr(obj, "PType") and obj.PType == "Tee"


def moveToPyLi(obj, plName):
    """
    Move obj to the group of pypeLine plName
    """
    pl = FreeCAD.ActiveDocument.getObjectsByLabel(plName)[0]
    group = FreeCAD.ActiveDocument.getObjectsByLabel(str(pl.Group))[0]
    group.addObject(obj)
    if hasattr(obj, "PType"):
        if obj.PType in objToPaint:
            obj.ViewObject.ShapeColor = pl.ViewObject.ShapeColor
        elif obj.PType == "PypeBranch":
            for e in [FreeCAD.ActiveDocument.getObject(name) for name in obj.Tubes + obj.Curves]:
                e.ViewObject.ShapeColor = pl.ViewObject.ShapeColor


def portsPos(o):
    """
    portsPos(o)
    Returns the position of Ports of the pype-object o
    """
    if hasattr(o, "Ports") and hasattr(o, "Placement"):
        return [rounded(o.Placement.multVec(p)) for p in o.Ports]


def portsDir(o):
    """
    portsDir(o)
    Returns the orientation of Ports of the pype-object o
    """
    dirs = list()
    two_ways = ["Pipe", "Reduct", "Flange"]
    if hasattr(o, "PType"):
        # Use explicit PortDirections if available
        if hasattr(o, "PortDirections") and o.PortDirections:
            # Transform port directions from local to world coordinates
            dirs = [
                rounded(o.Placement.Rotation.multVec(d).normalize())
                for d in o.PortDirections
            ]
        #fallback for objects without explicit ports
        elif o.PType in two_ways:
            dirs = [
                o.Placement.Rotation.multVec(p)
                for p in [FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)]
            ]
        elif hasattr(o, "Ports") and hasattr(o, "Placement"):
            dirs = list()
            for p in o.Ports:
                if p.Length:
                    dirs.append(rounded(o.Placement.Rotation.multVec(p).normalize()))
                else:
                    dirs.append(
                        rounded(o.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, -1)).normalize())
                    )
       
        """
        if o.PType in two_ways:
            dirs = [
                o.Placement.Rotation.multVec(p)
                for p in [FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)]
            ]
        elif hasattr(o, "Ports") and hasattr(o, "Placement"):
            dirs = list()
            for p in o.Ports:
                if p.Length:
                    dirs.append(rounded(o.Placement.Rotation.multVec(p).normalize()))
                else:
                    dirs.append(
                        rounded(o.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, -1)).normalize())
                    )
        """
    return dirs


################## COMMANDS ########################

def getSelectedPortDimensions():
    """
    Determine the OD and thickness of the selected port.
    Returns (OD, thk, PRating, PSize) or (None, None, None, None) if cannot determine.
    
    For objects with multiple port sizes (Tee, Reduct), determines which port
    is closest to the selected edge/vertex to get the correct dimensions.
    
    This is a helper function for form auto-selection features.
    """
    selex = FreeCADGui.Selection.getSelectionEx()
    if not selex:
        return None, None, None, None
    
    for sx in selex:
        obj = sx.Object
        if not hasattr(obj, "PType"):
            continue
        
        # Get object properties
        ptype = obj.PType
        
        # For objects with uniform port sizes (Pipe, Elbow, Flange, Cap, Valve)
        if ptype in ["Pipe", "Elbow", "Flange", "Cap", "Valve"]:
            if hasattr(obj, "OD") and hasattr(obj, "thk") and hasattr(obj, "PRating") and hasattr(obj, "PSize"):
                return float(obj.OD), float(obj.thk), obj.PRating, obj.PSize
        
        # For Tee: has run and branch with potentially different sizes
        elif ptype == "Tee":
            if not (hasattr(obj, "Ports") and len(obj.Ports) >= 3):
                continue
            
            # Determine which port is selected based on proximity
            selectedPort = None
            if sx.SubObjects:
                subObj = sx.SubObjects[0]
                if hasattr(subObj, "CenterOfMass"):
                    selectionPoint = subObj.CenterOfMass
                elif hasattr(subObj, "Point"):
                    selectionPoint = subObj.Point
                else:
                    selectionPoint = None
                
                if selectionPoint:
                    # Find closest port
                    minDist = float('inf')
                    for i, port in enumerate(obj.Ports):
                        portWorldPos = obj.Placement.multVec(port)
                        dist = (portWorldPos - selectionPoint).Length
                        if dist < minDist:
                            minDist = dist
                            selectedPort = i
            
            # Port 2 is the branch, ports 0 and 1 are the run
            if selectedPort == 2:
                # Branch port
                if hasattr(obj, "OD2") and hasattr(obj, "thk2"):
                    return float(obj.OD2), float(obj.thk2), obj.PRating if hasattr(obj, "PRating") else None, obj.PSize if hasattr(obj, "PSize") else None
            else:
                # Run port (0 or 1, or default if couldn't determine)
                if hasattr(obj, "OD") and hasattr(obj, "thk"):
                    return float(obj.OD), float(obj.thk), obj.PRating if hasattr(obj, "PRating") else None, obj.PSize if hasattr(obj, "PSize") else None
        
        # For Reduct: port 0 is larger end, port 1 is smaller end
        elif ptype == "Reduct":
            if not (hasattr(obj, "Ports") and len(obj.Ports) >= 2):
                continue
            
            # Determine which port is selected
            selectedPort = None
            if sx.SubObjects:
                subObj = sx.SubObjects[0]
                if hasattr(subObj, "CenterOfMass"):
                    selectionPoint = subObj.CenterOfMass
                elif hasattr(subObj, "Point"):
                    selectionPoint = subObj.Point
                else:
                    selectionPoint = None
                
                if selectionPoint:
                    # Find closest port
                    minDist = float('inf')
                    for i, port in enumerate(obj.Ports):
                        portWorldPos = obj.Placement.multVec(port)
                        dist = (portWorldPos - selectionPoint).Length
                        if dist < minDist:
                            minDist = dist
                            selectedPort = i
            
            # Port 0 is larger end (OD), port 1 is smaller end (OD2)
            if selectedPort == 1:
                # Smaller end
                if hasattr(obj, "OD2") and hasattr(obj, "thk2"):
                    return float(obj.OD2), float(obj.thk2), obj.PRating if hasattr(obj, "PRating") else None, obj.PSize if hasattr(obj, "PSize") else None
            else:
                # Larger end (0 or default)
                if hasattr(obj, "OD") and hasattr(obj, "thk"):
                    return float(obj.OD), float(obj.thk), obj.PRating if hasattr(obj, "PRating") else None, obj.PSize if hasattr(obj, "PSize") else None
    
    return None, None, None, None


def autoSelectInPipeForm(form):
    """
    Auto-select the size and rating in form lists based on selected object's port.
    
    Args:
        form: The form object (must have ratingList, sizeList, pipeDictList, PRating, fillSizes())
    
    This is a helper function for form auto-selection features.
    Works with any form that has the standard protoPypeForm structure.
    """
    from FreeCAD import Units
    pq = Units.parseQuantity

    OD, thk, PRating, PSize = getSelectedPortDimensions()
    
    if OD is None:
        return  # No valid selection, keep defaults
    
    # Try to select matching rating first
    if PRating and hasattr(form, 'ratingList'):
        for i in range(form.ratingList.count()):
            if form.ratingList.item(i).text() == PRating:
                form.ratingList.setCurrentRow(i)
                form.PRating = PRating
                if hasattr(form, 'fillSizes'):
                    form.fillSizes()
                break
    
    # Try to find matching size by OD and thk
    if not hasattr(form, 'pipeDictList') or not hasattr(form, 'sizeList'):
        return

    # If we have PSize from selection, try exact PSize match first
    if PSize:
        for i, pipeDict in enumerate(form.pipeDictList):
            # For Tees: prefer equal run/branch sizes (e.g., "DN50xDN50" over "DN50xDN40")
            # Check if PSize contains "x" (indicating Tee or Reduct with two sizes)
            dictPSize = pipeDict.get("PSize", "")
            if "x" in dictPSize:
                # Split to get run and branch sizes
                parts = dictPSize.split("x")
                if len(parts) == 2:
                    runSize = parts[0]
                    branchSize = parts[1]
                    # Prefer straight tees: if detected PSize matches run, i.e. prefer DN50xDN50 over DN50xDN40. This won't find a match here for reducers, but it should find a match later by checking OD's
                    if runSize == branchSize and runSize == PSize:
                        form.sizeList.setCurrentRow(i)
                        if hasattr(form, 'fillOD2'):
                            form.fillOD2()
                        return  # Found equal run/branch
            
            # Also check for exact PSize match (including non-Tee items)
            if dictPSize == PSize:
                form.sizeList.setCurrentRow(i)
                if hasattr(form, 'fillOD2'):
                    form.fillOD2()
                return  # Found exact PSize match
    
    # Fallback: If no PSize match, try OD/thk matching with preference for equal OD/OD2
    if OD is not None:
        bestMatch = None
        bestMatchScore = float('inf')
        
        for i, pipeDict in enumerate(form.pipeDictList):
            try:
                dictOD = float(pq(pipeDict["OD"]))
                dictThk = float(pq(pipeDict["thk"]))
                
                # Check if this is a Tee/Reducer with OD2
                hasOD2 = "OD2" in pipeDict
                if hasOD2:
                    dictOD2 = float(pq(pipeDict["OD2"]))
                    # Prefer equal-size Tees: if OD matches and OD==OD2
                    if abs(dictOD - OD) < 0.1 and abs(dictOD - dictOD2) < 0.1:
                        # Straight tee
                        score = 0.0  # Perfect match score
                    else:
                        # Calculate normal match score
                        odDiff = abs(dictOD - OD)
                        thkDiff = abs(dictThk - thk)
                        score = odDiff * 10 + thkDiff
                else:
                    # other fittings - calculate match score
                    odDiff = abs(dictOD - OD)
                    thkDiff = abs(dictThk - thk)
                    score = odDiff * 10 + thkDiff
                
                if score < bestMatchScore:
                    bestMatchScore = score
                    bestMatch = i
            except:
                continue
        
        # Select the best match if found
        if bestMatch is not None and bestMatchScore < 5.0:  # Reasonable tolerance
            form.sizeList.setCurrentRow(bestMatch)
            # Call form-specific update if it exists
            if hasattr(form, 'fillOD2'):
                form.fillOD2()

def getSelectionPortAttachment(selex=None):
    """
    Inspects the current selection and, if the selected object has Ports,
    returns the world position, outward direction, object, and port index of
    the port closest to the selection point.

    The selection point is determined as follows:
      - Vertex selected  -> vertex point
      - Curved edge      -> centerOfCurvatureAt(0)
      - Straight edge    -> CenterOfMass (midpoint)

    Returns (pos, Z, obj, portIndex) if a ported object is found, or
    (None, None, None, None) if no ported object is in the selection.

    pos : FreeCAD.Vector  - world-space port position
    Z   : FreeCAD.Vector  - outward port direction in world space (from PortDirections)
    obj : FreeCAD object  - the stationary ported object
    portIndex : int       - index of the closest port
    """
    if selex is None:
        selex = FreeCADGui.Selection.getSelectionEx()

    for sx in selex:
        obj = sx.Object
        if not (hasattr(obj, "Ports") and len(obj.Ports) > 0):
            continue  # object has no ports - skip

        # Determine the raw selection point from the sub-shape
        selPt = None
        if sx.SubObjects:
            sub = sx.SubObjects[0]
            if sub.ShapeType == "Vertex":
                selPt = sub.Point
            elif sub.ShapeType == "Edge":
                if sub.curvatureAt(0) != 0:
                    selPt = sub.centerOfCurvatureAt(0)
                else:
                    selPt = sub.CenterOfMass          # midpoint of straight edge
            else:
                selPt = sub.CenterOfMass

        if selPt is None:
            # No sub-object - use the object base as fallback
            selPt = obj.Placement.Base

        # Find the closest port (world coordinates)
        closestPort = 0
        minDist = float("inf")
        for i, portVec in enumerate(obj.Ports):
            worldPort = obj.Placement.multVec(portVec)
            dist = (worldPort - selPt).Length
            if dist < minDist:
                minDist = dist
                closestPort = i

        # Port world position
        pos = obj.Placement.multVec(obj.Ports[closestPort])

        # Port outward direction in world space
        if hasattr(obj, "PortDirections") and obj.PortDirections:
            Z = obj.Placement.Rotation.multVec(obj.PortDirections[closestPort]).normalize()
        else:
            # Fallback: infer from port vector if PortDirections not set
            pVec = obj.Ports[closestPort]
            if pVec.Length > 0:
                Z = obj.Placement.Rotation.multVec(pVec).normalize()
            else:
                Z = obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))

        return pos, Z, obj, closestPort

    return None, None, None, None

class ViewProvider:
    def __init__(self, obj, icon_fn):
        obj.Proxy = self
        self._check_attr()
        self.icon_fn = get_icon_path(icon_fn or "quetzal")

    def _check_attr(self):
        """Check for missing attributes."""

        if not hasattr(self, "icon_fn"):
            setattr(self, "icon_fn", get_icon_path("quetzal"))

    def getIcon(self):
        """Returns the path to the SVG icon."""
        self._check_attr()
        return self.icon_fn


def simpleSurfBend(path=None, profile=None):
    "select the centerline and the O.D. and let it sweep"
    curva = FreeCAD.activeDocument().addObject("Part::Feature", "Simple curve")
    if path == None or profile == None:
        curva.Shape = Part.makeSweepSurface(*fCmd.edges()[:2])
    elif path.ShapeType == profile.ShapeType == "Edge":
        curva.Shape = Part.makeSweepSurface(path, profile)

def getAttachmentPoints():
    
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port. If nothing is selected, it will go to the execption and return None's, which will insert at the origin
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        srcObj = None
        srcPort = None
        pos = None
        Z = None
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        if usablePorts:
            face = fCmd.faces([selex])
            edge = fCmd.edges([selex])
            v = fCmd.points([selex])

            if len(face) + len(edge) + len(v) > 0:
                pos, Z, srcObj, srcPort = getSelectionPortAttachment([selex])
            else:
                pos, Z, srcObj, srcPort = getSelectionPortAttachment([selex])
                #overwrite port with highest number port
                srcPort = len(selex.Object.Ports) - 1
        else:
            #insert at center of curvature for curved edges or faces, insert at vertex point for vertices
            face = fCmd.faces([selex])
            edge = fCmd.edges([selex])
            v = fCmd.points([selex])
            if face:  # Face selected...
                x = (face[0].ParameterRange[0] + face[0].ParameterRange[1]) / 2
                y = (face[0].ParameterRange[2] + face[0].ParameterRange[3]) / 2
                pos = face[0].valueAt(x, y)
                Z = face[0].normalAt(x, y)
               
            elif edge:
                if edge[0].curvatureAt(0) == 0:  # straight edge, no ports
                   pos =edge[0].valueAt(0)
                   Z =edge[0].tangentAt(0)

                else:  # curved edge, no ports
                    pos = edge[0].centerOfCurvatureAt(0)
                    Z = edge[0].tangentAt(0).cross(edge[0].normalAt(0))
                    #Note that this Z direction is a guess, it might need to be opposite. User can use Reverse button to reverse. Could try to add code to check direction against center of mass
                    
                    
            elif v:
                pos = v[0].Point
                Z = None #use default orientation with vertex, since we don't know what direction is desired

        
        return pos, Z, srcObj, srcPort
         
    except:
        #nothing selected, insert at origin
       return None, None, None, None


def makePipe(rating,propList=[], pos=None, Z=None):
    """add a Pipe object
    makePipe(rating,propList,pos,Z);
    propList is one optional list with 4 elements:
      DN (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
      H (float): length of pipe
    Default is "DN50 (SCH-STD)"
    rating pipe pressure capability
    pos (vector): position of insertion; default = 0,0,0
    Z (vector): orientation: default = 0,0,1
    Remember: property PRating must be defined afterwards
    """
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Tube")
    if len(propList) == 4:
        pFeatures.Pipe(a,rating, *propList)
    else:
        pFeatures.Pipe(a,rating)
    ViewProvider(a.ViewObject, "Quetzal_InsertPipe")
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    a.Label = translate("Objects", "Tube")
    return a



def doPipes(rating,propList=["DN50", 60.3, 3, 1000], pypeline=None):
    """
    propList = [
      DN (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
      H (float): length of pipe ]
    pypeline = string
    """
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert pipe"))
    plist = list()
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            pipe = makePipe(rating, propList, pos, Z)
            plist.append(pipe)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(pipe, 0, srcObj, srcPort)
        else:
            plist.append(makePipe(rating, propList, pos, Z))
    except:
        #nothing selected, insert at origin
        plist.append(makePipe(rating,propList))
        
    if pypeline:
        for p in plist:
            moveToPyLi(p, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist


def makeTerminalAdapter(rating,propList=[],pos=None,Z=None):
    """Add TerminalAdapter object
    """
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "TerminalAdapter")
    pFeatures.TerminalAdapter(a,rating, *propList)
    ViewProvider(a.ViewObject, "Quetzal_TerminalAdapter")
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), -Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)


def makeElbow(propList=[], pos=None, Z=None, rating="SCH-STD"):
    """Adds an Elbow object
    makeElbow(propList,pos,Z);
      propList is one optional list with 5 elements:
        DN (string): nominal diameter
        OD (float): outside diameter
        thk (float): shell thickness
        BA (float): bend angle
        BR (float): bend radius
      Default is "DN50"
      pos (vector): position of insertion; default = 0,0,0
      Z (vector): orientation: default = 0,0,1
    Remember: property PRating must be defined afterwards
    """
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Elbow")
    if len(propList) == 5:
        pFeatures.Elbow(a, rating, *propList)
    else:
        pFeatures.Elbow(a, rating)
    ViewProvider(a.ViewObject, "Quetzal_InsertElbow")
   
    # Rotate so port[0]'s local direction faces Z.
    # SocketEll port[0] direction is (1,0,0) — local +X, not +Z — so the
    # reference axis must be port[0]'s actual local direction, not (0,0,1).
    port0_local_dir = a.PortDirections[0] if a.PortDirections else FreeCAD.Vector(0, 0, 1)
    rot = FreeCAD.Rotation(port0_local_dir, Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    # After rotation the object origin is still at (0,0,0). Translate so that
    # port[0] — now in its rotated world position — lands exactly at pos.
    port0_world = a.Placement.multVec(a.Ports[0])
    a.Placement.Base = pos - port0_world
    a.Label = translate("Objects", "Elbow")
    return a


def makeElbowBetweenThings(thing1=None, thing2=None, propList=None):
    """
    makeElbowBetweenThings(thing1, thing2, propList=None):
    Place one elbow at the intersection of thing1 and thing2
    Things can be any combination of intersecting beams, pipes or edges.
    If nothing is passed as argument, the function attempts to take the
    first two edges selected in the view.
    propList is one optional list with 5 elements:
      DN (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
      BA (float): bend angle - that will be recalculated! -
      BR (float): bend radius
    Default is "DN50 (SCH-STD)"
    Remember: property PRating must be defined afterwards
    """
    if not (thing1 and thing2):
        thing1, thing2 = fCmd.edges()[:2]
    P = fCmd.intersectionCLines(thing1, thing2)
    directions = list()
    try:
        for thing in [thing1, thing2]:
            if fCmd.beams([thing]):
                directions.append(
                    rounded(
                        (fCmd.beamAx(thing).multiply(thing.Height / 2) + thing.Placement.Base) - P
                    )
                )
            elif hasattr(thing, "ShapeType") and thing.ShapeType == "Edge":
                directions.append(rounded(thing.CenterOfMass - P))
    except:
        return None
    ang = 180 - degrees(directions[0].getAngle(directions[1]))
    if ang == 0 or ang == 180:
        return None
    if not propList:
        propList = ["DN50", 60.3, 3.91, ang, 45.24]
    else:
        propList[3] = ang
    # Create the elbow in its default rest orientation (no pos/Z args).
    # Then use placeoTherElbow to set the full orientation and position in one step.
    # This avoids the old approach which tried to find the current bisect via beamAx(elb,(1,1,0))
    # after makeElbow had already applied a Z-alignment rotation -- that assumption was only
    # valid when the elbow was still in its default rest pose, causing misalignment on any
    # pipe path not lying in the world XY plane.
    # placeoTherElbow computes its rotations from the elbow's local Ports vectors, which
    # are always in shape space regardless of any prior rotation, so it is safe to call
    # even after the elbow has been created with a non-identity placement.
    # Convention: v1 is the incoming tangent (path direction entering the corner) and
    # v2 is the outgoing tangent. directions[0] points away from P along thing1 (= outgoing
    # of thing1, which is the incoming approach direction reversed), and directions[1] points
    # away from P along thing2 (= outgoing tangent). So v1 = -directions[1], v2 = directions[0].
    elb = makeElbow(propList)
    placeoTherElbow(elb, directions[0].negative(), directions[1], P)
    # trim the adjacent tubes
    # FreeCAD.activeDocument().recompute() # may delete this row?
    portA = elb.Placement.multVec(elb.Ports[0])
    portB = elb.Placement.multVec(elb.Ports[1])
    for tube in [t for t in [thing1, thing2] if fCmd.beams([t])]:
        vectA = tube.Shape.Solids[0].CenterOfMass - portA
        vectB = tube.Shape.Solids[0].CenterOfMass - portB
        if fCmd.isParallel(vectA, fCmd.beamAx(tube)):
            fCmd.extendTheBeam(tube, portA)
        else:
            fCmd.extendTheBeam(tube, portB)
    return elb


def doElbow(rating="SCH-STD", propList=["DN50", 60.3, 3, 90, 45.225], pypeline=None):
    """
    propList = [
      DN (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
      BA (float): bend angle
      BR (float): bend radius ]
    pypeline = string
    """
    elist = []
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert elbow"))
    selex = FreeCADGui.Selection.getSelectionEx()
    if len(selex) == 0:  # no selection -> insert one elbow at origin
        elist.append(makeElbow(propList, rating=rating))
    elif len(selex) == 1 and len(selex[0].SubObjects) == 1:  # one selection -> ...
               
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            elb = makeElbow(propList, pos, Z, rating=rating)
            elist.append(elb)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(elb, 0, srcObj, srcPort)
        else:
            elist.append(makeElbow(propList, pos, Z, rating=rating))

    else:  # multiple selection -> insert one elbow at intersection of two edges or beams or pipes ##
        things = []
        for objEx in selex:
            if (
                len(fCmd.beams([objEx.Object])) == 1
            ):  # if the object is a beam or pipe, append it to the "things"..
                things.append(objEx.Object)
            else:  # ..else append its edges
                for edge in fCmd.edges([objEx]):
                    things.append(edge)
            if len(things) >= 2:
                break
        try:  # create the feature
            elb = elist.append(makeElbowBetweenThings(*things[:2], propList=propList))
        except:
            FreeCAD.Console.PrintError("Creation of elbow is failed\n")
    if pypeline:
        for e in elist:
            moveToPyLi(e, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return elist


def makeFlange(propList=[], pos=None, Z=None, doOffset=None, rating="DIN-PN16", fclass=""):
    """Adds a Flange object
    makeFlange(propList,pos,Z);
      propList is one optional list with 8 elements:
        DN (string): nominal diameter
        FlangeType (string): type of Flange
        D (float): flange diameter
        d (float): bore diameter
        df (float): bolts holes distance
        f (float): bolts holes diameter
        t (float): flange thickness
        n (int): nr. of bolts
        trf (float): raised-face thickness - OPTIONAL -
        drf (float): raised-face diameter - OPTIONAL -
        twn (float): welding-neck thickness - OPTIONAL -
        dwn (float): welding-neck diameter - OPTIONAL -
        ODp (float): outside diameter of pipe for wn flanges - OPTIONAL -
      Default is "DN50 (PN16)"
      pos (vector): position of insertion; default = 0,0,0
      Z (vector): orientation: default = 0,0,1
      R Flange fillet radius
      T1 Overall flange thickness
      Y Socket depth

    Remember: property PRating must be defined afterwards
    """

    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Flange")
    if len(propList) >= 8:
        pFeatures.Flange(a, rating, *propList, FClass=fclass)
    else:
        pFeatures.Flange(a, rating, FClass=fclass)
    ViewProvider(a.ViewObject, "Quetzal_InsertFlange")
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    if not doOffset:
        if a.FlangeType == "WN":
            zpos = -a.T1 + a.trf
        elif a.FlangeType == "SW":
            zpos = -a.T1 + a.Y + a.trf
        elif a.FlangeType == "LJ":
            zpos = 0
        else:
            zpos = 0
        a.Placement = a.Placement.multiply(
            FreeCAD.Placement(FreeCAD.Vector(0, 0, zpos), FreeCAD.Rotation())
        )
    FreeCAD.ActiveDocument.recompute()
    a.Label = translate("Objects", "Flange")
    return a


def doFlanges(
    rating="DIN-PN16",
    propList=["DN50", "SO", 160, 60.3, 132, 14, 15, 4, 0, 0, 0, 0, 0, 0, 0],
    pypeline=None,
    doOffset=None,
    attachFace=None, 
    fclass="",
):
    """
    propList = [
      DN (string): nominal diameter
      FlangeType (string): type of Flange
      D (float): flange diameter
      d (float): bore diameter
      df (float): bolts holes distance
      f (float): bolts holes diameter
      t (float): flange thickness
      n (int): nr. of bolts
      trf (float): raised-face thickness - OPTIONAL -
      drf (float): raised-face diameter - OPTIONAL -
      twn (float): welding-neck thickness - OPTIONAL -
      dwn (float): welding-neck diameter - OPTIONAL -
      ODp (float): outside diameter of pipe for wn flanges - OPTIONAL -
      R Flange fillet radius
      T1 Overall flange thickness
      Y Socket depth

    pypeline = string
    """
    flist = []
    tubes = [t for t in fCmd.beams() if hasattr(t, "PSize")]
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert flange"))

    if attachFace:
        connecting_port = 0
    else:
        connecting_port = 1
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()

        if usablePorts:
            flange = makeFlange(propList, pos, Z, doOffset, rating=rating, fclass=fclass)
            flist.append(flange)
            
            #if we need to remove pipe equivalent length
            if doOffset:
                #Correct offset for raised face flanges. If flat face flanges are added, presumably a.trf would be zero?
                a=flist[-1]
                if a.FlangeType == "WN":
                    zpos = -a.T1 
                elif a.FlangeType == "SW":
                    zpos = -a.T1 + a.Y 
                elif a.FlangeType == "LJ":
                    zpos = 0
                else:
                    zpos = a.trf
                pipe = fCmd.beams()[0]
                #respos=a.Placement.multiply(FreeCAD.Placement(FreeCAD.Vector(0,0,-zpos), FreeCAD.Rotation(1, 0, 0)))
                respos=a.Placement.multiply(FreeCAD.Placement(FreeCAD.Vector(0,0,zpos), FreeCAD.Rotation()))
                fCmd.extendTheBeam(pipe,respos.Base)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
         
            alignTwoPorts(flange, connecting_port, srcObj, srcPort)


        else:
            flist.append(makeFlange(propList, pos, Z, doOffset, rating=rating, fclass=fclass))
    except:
        #nothing selected, insert at origin
        flist.append(makeFlange(propList, rating=rating, fclass=fclass))

    if pypeline:
        for f in flist:
            moveToPyLi(f, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return flist


def makeReduct(propList=[], pos=None, Z=None, conc=True, smallerEnd=False, rating="SCH-STD"):
    """Adds a Reduct object
    makeReduct(propList=[], pos=None, Z=None, conc=True)
      propList is one optional list with 6 elements:
        PSize (string): nominal diameter
        OD (float): major diameter
        OD2 (float): minor diameter
        thk (float): major thickness
        thk2 (float): minor thickness
        H (float): length of reduction
      pos (vector): position of insertion; default = 0,0,0
      Z (vector): orientation: default = 0,0,1
      conc (bool): True for concentric or False for eccentric reduction
    Remember: property PRating must be defined afterwards
    """
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Reduction")
    propList.append(conc)
    pFeatures.Reduct(a, rating, *propList)
    ViewProvider(a.ViewObject, "Quetzal_InsertReduct")
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    if smallerEnd:
        initPos = a.Placement.Base
        rotateTheTubeAx(a, FreeCAD.Vector(0, 1, 0), 180)
        finalPos = a.Placement.Base
        dist = initPos-finalPos
        a.Placement.move(dist)
        
    a.Label = translate("Objects", "Reduct")
    return a

def doReduct(rating="SCH-STD", propList=[], pypeline=None, pos=None, Z=None, conc=True, smallerEnd=False):
    """propList[] = 
      PSize (string): nominal diameter
        OD (float): major diameter
        OD2 (float): minor diameter
        thk (float): major thickness
        thk2 (float): minor thickness
        H (float): length of reduction
      pos (vector): position of insertion; default = 0,0,0
      Z (vector): orientation: default = 0,0,1
      conc (bool): True for concentric or False for eccentric reduction
    """
    
    if smallerEnd:
        connecting_port = 1
    else:
        connecting_port = 0
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert Reduct"))
    plist = list()
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            reduct = makeReduct(propList, pos, Z, conc, smallerEnd, rating=rating)
            plist.append(reduct)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(reduct, connecting_port, srcObj, srcPort)
        else:
            plist.append(makeReduct(propList, pos, Z, conc, smallerEnd, rating=rating))
    except:
        #nothing selected, insert at origin
        plist.append(makeReduct(propList, pos, Z, conc, smallerEnd, rating=rating))
        
    if pypeline:
        for p in plist:
            moveToPyLi(p, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist


def makeUbolt(propList=[], pos=None, Z=None):
    """Adds a Ubolt object:
    makeUbolt(propList,pos,Z);
      propList is one optional list with 5 elements:
        PSize (string): nominal diameter
        ClampType (string): the clamp type or standard
        C (float): the diameter of the U-bolt
        H (float): the total height of the U-bolt
        d (float): the rod diameter
      pos (vector): position of insertion; default = 0,0,0
      Z (vector): orientation: default = 0,0,1
    Remember: property PRating must be defined afterwards
    """
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "U-Bolt")
    if len(propList) == 5:
        pFeatures.Ubolt(a, *propList)
    else:
        pFeatures.Ubolt(a)
    ViewProvider(a.ViewObject, "Quetzal_InsertUBolt")
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    a.Label = translate("Objects", "U-Bolt")
    return a


def makeShell(L=1000, W=1500, H=1500, thk1=6, thk2=8):
    """
    makeShell(L,W,H,thk1,thk2)
    Adds the shell of a tank, given
      L(ength):        default=800
      W(idth):         default=400
      H(eight):        default=500
      thk (thickness): default=6
    """
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Tank")
    pFeatures.Shell(a, L, W, H, thk1, thk2)
    ViewProvider(a.ViewObject, "Quetzal_InsertTank")
    a.Placement.Base = FreeCAD.Vector(0, 0, 0)
    a.ViewObject.ShapeColor = 0.0, 0.0, 1.0
    a.ViewObject.Transparency = 85
    FreeCAD.ActiveDocument.recompute()
    a.Label = translate("Objects", "Tank")
    return a


def makeCap(propList=[], pos=None, Z=None, rating="SCH-STD"):
    """add a Cap object
    makeCap(propList,pos,Z);
    propList is one optional list with 3 elements:
      DN (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
    Default is "DN50 (SCH-STD)"
    pos (vector): position of insertion; default = 0,0,0
    Z (vector): orientation: default = 0,0,1
    Remember: property PRating must be defined afterwards
    """
    
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Cap")
    if len(propList) == 3:
        pFeatures.Cap(a, rating, *propList)
    else:
        pFeatures.Cap(a, rating)
    ViewProvider(a.ViewObject, "Quetzal_InsertCap")
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    a.Label = translate("Objects", "Cap")
    return a
    
    

def doCaps(rating="SCH-STD", propList=["DN50", 60.3, 3], pypeline=None):
    """
    propList = [
      DN (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness ]
    pypeline = string
    """
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert cap"))
    plist = list()
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            cap = makeCap(propList, pos, Z, rating=rating)
            plist.append(cap)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(cap, 0, srcObj, srcPort)
        else:
            plist.append(makeCap(propList, pos, Z, rating=rating))
    except:
        #nothing selected, insert at origin
        plist.append(makeCap(propList, rating=rating))
        
    if pypeline:
        for p in plist:
            moveToPyLi(p, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist
    
    
def makeTee(propList=[], pos=None, Z=None, insertOnBranch=False, rating="SCH-STD"):
    """add a Tee object
    makeTee(propList,pos,Z);
    propList is one optional list with 7 elements:
      DN (string): nominal diameter
      OD (float): outside diameter of run
      OD2 (float): outside diameter of branch
      thk (float): shell thickness of run
      thk (float): shell thickness of branch
      C (float): Length of run from centerline
      M (float): Length of branch from centerline
    Default is "DN50 (SCH-STD)"
    pos (vector): position of insertion; default = 0,0,0
    Z (vector): orientation: default = 0,0,1
    insertOnBranch = Boolean
    """
    if pos == None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z == None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Tee")
    if len(propList) == 7:
        pFeatures.Tee(a, rating, *propList)
    else:
        pFeatures.Tee(a, rating)
    ViewProvider(a.ViewObject, "Quetzal_InsertTee")

    a.Placement.Base = pos

    #Rotate tee to have proper port (run or branch) facing the passed orientation (Z). 
    
    if insertOnBranch:
        zpos = 0
        ypos = -a.M
        rot = FreeCAD.Rotation(FreeCAD.Vector(0, -1, 0), Z)
    else:
        zpos = a.C
        ypos = 0
        rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)

    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)

    a.Placement = a.Placement.multiply(
        FreeCAD.Placement(FreeCAD.Vector(0, ypos, zpos), FreeCAD.Rotation(0, 0, 0))
    )
    
    a.Label = translate("Objects", "Tee")
    return a


def doTees(rating="SCH-STD", propList=["DN150", 168.27, 114.3,7.11,6.02,178,156], pypeline=None, insertOnBranch=False):
    """
    propList = [
       DN (string): nominal diameter
      OD (float): outside diameter of run
      OD2 (float): outside diameter of branch
      thk (float): shell thickness of run
      thk (float): shell thickness of branch
      C (float): Length of run from centerline
      M (float): Length of branch from centerline
      Default is "DN50 (SCH-STD)"

      pypeline = string
      insertOnBranch = Boolean 
    """
    if insertOnBranch:
        insertion_port = 2
    else:
        insertion_port = 0
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert tee"))
    plist = list()
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            tee = makeTee(propList, pos, Z, insertOnBranch, rating=rating)
            plist.append(tee)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(tee, insertion_port, srcObj, srcPort)
        else:
            plist.append(makeTee(propList, pos, Z, insertOnBranch, rating=rating))
    except:
        #nothing selected, insert at origin
        plist.append(makeTee(propList, None, None, insertOnBranch))
        
    if pypeline:
        for p in plist:
            moveToPyLi(p, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist
    
def makeW():
    edges = fCmd.edges()
    if len(edges) > 1:
        first = edges[0]
        last = edges[-1]
        points = list()
        while len(edges) > 1:
            points.append(fCmd.intersectionCLines(edges.pop(0), edges[0]))
        delta1 = (first.valueAt(0) - points[0]).Length
        delta2 = (first.valueAt(first.LastParameter) - points[0]).Length
        if delta1 > delta2:
            points.insert(0, first.valueAt(0))
        else:
            points.insert(0, first.valueAt(first.LastParameter))
        delta1 = (last.valueAt(0) - points[0]).Length
        delta2 = (last.valueAt(last.LastParameter) - points[0]).Length
        if delta1 > delta2:
            points.append(last.valueAt(0))
        else:
            points.append(last.valueAt(last.LastParameter))
        from Draft import makeWire

        try:
            p = makeWire(points)
        except:
            FreeCAD.Console.PrintError("Missing intersection\n")
            return None
        p.Label = "Path"
        drawAsCenterLine(p)
        return p
    elif FreeCADGui.Selection.getSelection():
        obj = FreeCADGui.Selection.getSelection()[0]
        if hasattr(obj, "Shape") and type(obj.Shape) == Part.Wire:
            drawAsCenterLine(obj)
        return obj
    else:
        return None


def makePypeLine2(
    DN="DN50",
    PRating="SCH-STD",
    OD=60.3,
    thk=3,
    BR=None,
    lab="Tubatura",
    pl=None,
    color=(0.8, 0.8, 0.8),
):
    """
    makePypeLine2(DN="DN50",PRating="SCH-STD",OD=60.3,thk=3,BR=None, lab="Tubatura",pl=None, color=(0.8,0.8,0.8))
    Adds a PypeLine2 object creating pipes over the selected edges.
    Default tube is "DN50", "SCH-STD"
    Bending Radius is set to 0.75*OD.
    """
    if not BR:
        BR = 0.75 * OD
    # create the pypeLine group
    if not pl:
        a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", lab)
        pFeatures.PypeLine2(a, DN, PRating, OD, thk, BR, lab)
        pFeatures.ViewProviderPypeLine(a.ViewObject)  # a.ViewObject.Proxy=0
        a.ViewObject.ShapeColor = color
        if len(FreeCADGui.Selection.getSelection()) == 1:
            obj = FreeCADGui.Selection.getSelection()[0]
            isWire = hasattr(obj, "Shape") and obj.Shape.Edges  # type(obj.Shape)==Part.Wire
            isSketch = hasattr(obj, "TypeId") and obj.TypeId == "Sketcher::SketchObject"
            if isWire or isSketch:
                a.Base = obj
                a.Proxy.update(a)
            if isWire:
                drawAsCenterLine(obj)
        elif fCmd.edges():
            path = makeW()
            a.Base = path
            a.Proxy.update(a)
    else:
        a = FreeCAD.ActiveDocument.getObjectsByLabel(pl)[0]
        group = FreeCAD.ActiveDocument.getObjectsByLabel(a.Group)[0]
        a.Proxy.update(a, fCmd.edges())
        FreeCAD.Console.PrintWarning("Objects added to pypeline's group " + a.Group + "\n")
    return a


def makeBranch(
    base=None,
    DN="DN50",
    PRating="SCH-STD",
    OD=60.3,
    thk=3,
    BR=None,
    lab="Traccia",
    color=(0.8, 0.8, 0.8),
):
    """
    makeBranch(base=None, DN="DN50",PRating="SCH-STD",OD=60.3,thk=3,BR=None, lab="Traccia" color=(0.8,0.8,0.8))
    Draft function for PypeBranch.
    """
    if not BR:
        BR = 0.75 * OD
    if not base:
        if FreeCADGui.Selection.getSelection():
            obj = FreeCADGui.Selection.getSelection()[0]
            isWire = hasattr(obj, "Shape") and type(obj.Shape) == Part.Wire
            isSketch = hasattr(obj, "TypeId") and obj.TypeId == "Sketcher::SketchObject"
            if isWire or isSketch:
                base = obj
            if isWire:
                drawAsCenterLine(obj)
        elif fCmd.edges():
            base = makeW()
    if base:
        a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", lab)
        pFeatures.PypeBranch2(a,PRating, base, DN, OD, thk, BR)
        pFeatures.ViewProviderPypeBranch(a.ViewObject)
        return a
    else:
        FreeCAD.Console.PrintError("Select a valid path.\n")


def updatePLColor(sel=None, color=None):
    if not sel:
        sel = FreeCADGui.Selection.getSelection()
    if sel:
        pl = sel[0]
        if hasattr(pl, "PType") and pl.PType == "PypeLine":
            if not color:
                color = pl.ViewObject.ShapeColor
            group = FreeCAD.activeDocument().getObjectsByLabel(pl.Group)[0]
            for o in group.OutList:
                if hasattr(o, "PType"):
                    if o.PType in objToPaint:
                        o.ViewObject.ShapeColor = color
                    elif o.PType == "PypeBranch":
                        for e in [
                            FreeCAD.ActiveDocument.getObject(name) for name in o.Tubes + o.Curves
                        ]:
                            e.ViewObject.ShapeColor = color
    else:
        FreeCAD.Console.PrintError("Select first one pype line\n")


def alignTheTube():
    """
    Mates the selected 2 circular edges
    of 2 separate objects.
    """
    try:
        t1 = FreeCADGui.Selection.getSelection()[0]
        t2 = FreeCADGui.Selection.getSelection()[-1]
    except:
        FreeCAD.Console.PrintError("Select at least one object.\n")
        return None
    d1, d2 = fCmd.edges()[:2]
    if d1.curvatureAt(0) != 0 and d2.curvatureAt(0) != 0:
        n1 = d1.tangentAt(0).cross(d1.normalAt(0))
        n2 = d2.tangentAt(0).cross(d2.normalAt(0))
    else:
        FreeCAD.Console.PrintError("Select 2 curved edges.\n")
        return None
    rot = FreeCAD.Rotation(n2, n1)
    t2.Placement.Rotation = rot.multiply(t2.Placement.Rotation)
    # traslazione centri di curvatura
    d1, d2 = fCmd.edges()  # redo selection to get new positions
    dist = d1.centerOfCurvatureAt(0) - d2.centerOfCurvatureAt(0)
    t2.Placement.move(dist)
    # verifica posizione relativa
    try:
        com1, com2 = [t.Shape.Solids[0].CenterOfMass for t in [t1, t2]]
        if isElbow(t2):
            pass
        elif (com1 - d1.centerOfCurvatureAt(0)).dot(com2 - d1.centerOfCurvatureAt(0)) > 0:
            reverseTheTube(FreeCADGui.Selection.getSelectionEx()[:2][1])
    except:
        pass
    # TARGET [solved]: verify if t1 or t2 belong to App::Part and changes the Placement consequently
    if fCmd.isPartOfPart(t1):
        part = fCmd.isPartOfPart(t1)
        t2.Placement = part.Placement.multiply(t2.Placement)
    if fCmd.isPartOfPart(t2):
        part = fCmd.isPartOfPart(t2)
        t2.Placement = part.Placement.inverse().multiply(t2.Placement)

def alignTwoPorts(obj2, port2, obj1, port1):
    """
    Mates the selected 2 circular edges
    of 2 separate objects. Object 1 is stationary, Object 2 moves. port1 and port2 are port indexes, not the port vectors
    """
    """
    Mates port port2 of obj2 (moves) to port port1 of obj1 (stationary).
    The ports are brought to the same world position with their directions
    anti-parallel (face to face).
    """
    #  1. Get world-space port directions 
    dir1 = obj1.Placement.Rotation.multVec(obj1.PortDirections[port1]).normalize()
    dir2 = obj2.Placement.Rotation.multVec(obj2.PortDirections[port2]).normalize()

    # Target: obj2's port direction must be the opposite of obj1's port direction
    target = dir1.negative()

    #  2. Compute the alignment rotation 
    dot = dir2.dot(target)

    if abs(dot - 1.0) < 1e-6:
        # Ports are already anti-parallel - no axis rotation needed,
        # but we must check: are they actually anti-parallel (good) or parallel (bad)?
        # dot near +1 means anti-parallel, already aligned, skip rotation.
        pass
    elif abs(dot + 1.0) < 1e-6:
        # Ports are parallel (same direction), need a 180� flip.
        # Pick an arbitrary perpendicular axis that is not degenerate.
        perp = dir2.cross(FreeCAD.Vector(1, 0, 0))
        if perp.Length < 1e-6:
            perp = dir2.cross(FreeCAD.Vector(0, 1, 0))
        perp.normalize()
        rot180 = FreeCAD.Rotation(perp, 180)
        obj2.Placement.Rotation = rot180.multiply(obj2.Placement.Rotation)
    else:
        # General case - shortest-arc rotation from dir2 to target
        rot = FreeCAD.Rotation(dir2, target)
        obj2.Placement.Rotation = rot.multiply(obj2.Placement.Rotation)

    #  3. Translate obj2 so its port coincides with obj1's port 
    p1_world = obj1.Placement.multVec(obj1.Ports[port1])
    p2_world = obj2.Placement.multVec(obj2.Ports[port2])
    obj2.Placement.move(p1_world - p2_world)
    """
    # Get world coordinates
    p1_world = obj1.Placement.multVec(obj1.Ports[port1])
    p2_world = obj2.Placement.multVec(obj2.Ports[port2])
    dir1_world = obj1.Placement.Rotation.multVec(obj1.PortDirections[port1])
    dir2_world = obj2.Placement.Rotation.multVec(obj2.PortDirections[port2])
    
    # Ports should face opposite directions
    target_dir = dir1_world * -1
    
    # Calculate and apply rotation
    rot = FreeCAD.Rotation(dir2_world, target_dir)
    obj2.Placement.Rotation = rot.multiply(obj2.Placement.Rotation)
    
    # Calculate and apply translation
    p2_world = obj2.Placement.multVec(obj2.Ports[port2])
    dist = p1_world - p2_world
    obj2.Placement.move(dist)
    """
    
    """
    #calculate absolute positions of the two ports
    p1 = obj1.Placement.multVec(obj1.Ports[port1])
    p2 = obj2.Placement.multVec(obj2.Ports[port2])

    #calculate the local positions of the ports relative to each object's base position
    obj1PortPos = p1-obj1.Placement.Base
    obj2PortPos = p2-obj2.Placement.Base

    #calculate the rotation required of object 2
    rot = FreeCAD.Rotation(obj2PortPos.normalize(), obj1PortPos.normalize())

    #perform the rotation, which aligns the two ports
    obj2.Placement.Rotation = rot.multiply(obj2.Placement.Rotation)
    
    # get new positions of the ports after rotation (object 1 shouldn't have moved but recalculate for good measure)
    d1=obj1.Placement.multVec(obj1.Ports[port1])
    d2=obj2.Placement.multVec(obj2.Ports[port2])

    #calculate the distance between the two and move object 2
    dist = d1 - d2
    obj2.Placement.move(dist)

    #get new position of object 2's port
    d2=obj2.Placement.multVec(obj2.Ports[port2])

    #check if center of masses aligned correctly by calculating the dot product of the port vectors to the opposite object's center of mass. 
    #If the dot product >0, then the port is facing the wrong way, so flip it 180 degrees around an axis perpendicular to the port axis. 
    #This won't work properly if the object's center of mass is facing the connection point, which would be extremely unusual for most common piping components,
    # but could plausibly happen on an object with a circuitous shape
    obj1PorttoObj2COM = d1-obj2.Shape.Solids[0].CenterOfMass
    obj2PorttoObj1COM = d2-obj1.Shape.Solids[0].CenterOfMass

    
    if obj1PorttoObj2COM.dot(obj2PorttoObj1COM) > 0:
        crossVector1 = FreeCAD.Vector(1,0,0)
        crossVector2 = obj2.Ports[port2].normalize()
        #if the port is at Vector(0,0,0) or Vector(1,0,0), it will cause problems, so catch those and assign different rotation axes.
        if crossVector2 == crossVector1:
            crossVector1 = FreeCAD.Vector(0,1,0)
        if crossVector2 == FreeCAD.Vector(0,0,0):
            crossVector2 = FreeCAD.Vector(0, 1, 0)


        rotateTheTubeAx(obj=obj2,vShapeRef=crossVector2.cross(crossVector1), angle=180)
        # get new positions of the ports after rotation, again (object 1 shouldn't have moved but recalculate for good measure)
        d1=obj1.Placement.multVec(obj1.Ports[port1])
        d2=obj2.Placement.multVec(obj2.Ports[port2])

        #recalculate the distance between the two and move object 2 again
        dist = d1 - d2
        obj2.Placement.move(dist)

    """
def rotateTheTubeAx(obj=None, vShapeRef=None, angle=45):
    """
    rotateTheTubeAx(obj=None,vShapeRef=None,angle=45)
    Rotates obj around the vShapeRef axis of its Shape by an angle.
      obj: if not defined, the first in the selection set
      vShapeRef: if not defined, the Z axis of the Shape
      angle: default=45 deg
    """
    if obj == None:
        obj = FreeCADGui.Selection.getSelection()[0]
    if vShapeRef == None:
        vShapeRef = FreeCAD.Vector(0, 0, 1)
    rot = FreeCAD.Rotation(fCmd.beamAx(obj, vShapeRef), angle)
    obj.Placement.Rotation = rot.multiply(obj.Placement.Rotation)


def reverseTheTube(objEx):
    """
    reverseTheTube(objEx)
    Reverse the orientation of objEx spinning it 180 degrees around the x-axis
    of its shape.
    If an edge is selected, it's used as pivot.
    """
    disp = None
    selectedEdges = [e for e in objEx.SubObjects if e.ShapeType == "Edge"]
    if selectedEdges:
        for edge in fCmd.edges([objEx]):
            if edge.curvatureAt(0):
                disp = edge.centerOfCurvatureAt(0) - objEx.Object.Placement.Base
                break
            elif fCmd.beams([objEx.Object]):
                ax = fCmd.beamAx(objEx.Object)
                disp = ax * ((edge.CenterOfMass - objEx.Object.Placement.Base).dot(ax))
    rotateTheTubeAx(objEx.Object, FreeCAD.Vector(1, 0, 0), 180)
    if disp:
        objEx.Object.Placement.move(disp * 2)


def rotateTheTubeEdge(ang=45):
    if len(fCmd.edges()) > 0 and fCmd.edges()[0].curvatureAt(0) != 0:
        originalPos = fCmd.edges()[0].centerOfCurvatureAt(0)
        obj = FreeCADGui.Selection.getSelection()[0]
        rotateTheTubeAx(vShapeRef=shapeReferenceAxis(), angle=ang)
        newPos = fCmd.edges()[0].centerOfCurvatureAt(0)
        obj.Placement.move(originalPos - newPos)


def placeTheElbow(c, v1=None, v2=None, P=None):
    """
    placeTheElbow(c,v1,v2,P=None)
    Puts the curve C between vectors v1 and v2.
    If point P is given, translates it in there.
    NOTE: v1 and v2 oriented in the same direction along the path!
    """
    if not (v1 and v2):
        v1, v2 = [e.tangentAt(0) for e in fCmd.edges()]
        try:
            P = fCmd.intersectionCLines(*fCmd.edges())
        except:
            pass
    if hasattr(c, "PType") and hasattr(c, "BendAngle") and v1 and v2:
        v1.normalize()
        v2.normalize()
        ortho = rounded(fCmd.ortho(v1, v2))
        bisect = rounded(v2 - v1)
        ang = degrees(v1.getAngle(v2))
        c.BendAngle = ang
        rot1 = FreeCAD.Rotation(rounded(fCmd.beamAx(c, FreeCAD.Vector(0, 0, 1))), ortho)
        c.Placement.Rotation = rot1.multiply(c.Placement.Rotation)
        rot2 = FreeCAD.Rotation(rounded(fCmd.beamAx(c, FreeCAD.Vector(1, 1, 0))), bisect)
        c.Placement.Rotation = rot2.multiply(c.Placement.Rotation)
        if not P:
            P = c.Placement.Base
        c.Placement.Base = P


def placeoTherElbow(c, v1=None, v2=None, P=None):
    """
    Like placeTheElbow() but with more math.
    """
    if not (v1 and v2):
        v1, v2 = [e.tangentAt(0) for e in fCmd.edges()]
        try:
            P = fCmd.intersectionCLines(*fCmd.edges())
        except:
            pass
    if hasattr(c, "PType") and hasattr(c, "BendAngle") and v1 and v2:
        v1.normalize()
        v2.normalize()
        ortho = rounded(fCmd.ortho(v1, v2))
        bisect = rounded(v2 - v1)
        cBisect = rounded(c.Ports[1].normalize() + c.Ports[0].normalize())  # math
        cZ = c.Ports[0].cross(c.Ports[1])  # more math
        ang = degrees(v1.getAngle(v2))
        c.BendAngle = ang
        rot1 = FreeCAD.Rotation(rounded(fCmd.beamAx(c, cZ)), ortho)
        c.Placement.Rotation = rot1.multiply(c.Placement.Rotation)
        rot2 = FreeCAD.Rotation(rounded(fCmd.beamAx(c, cBisect)), bisect)
        c.Placement.Rotation = rot2.multiply(c.Placement.Rotation)
        if not P:
            P = c.Placement.Base
        c.Placement.Base = P


def placeThePype(pypeObject, port=0, target=None, targetPort=0):
    """
    placeThePype(pypeObject, port=None, target=None, targetPort=0)
      pypeObject: a FeaturePython with PType property
      port: an optional port of pypeObject
    Aligns pypeObject's Placement to the Port of another pype which is selected in the viewport.
    The pype shall be selected to the circular edge nearest to the port concerned.
    """
    pos = Z = FreeCAD.Vector()
    if target and hasattr(target, "PType") and hasattr(target, "Ports"):  # target is given
        pos = portsPos(target)[targetPort]
        Z = portsDir(target)[targetPort]
    else:  # find target
        try:
            selex = FreeCADGui.Selection.getSelectionEx()
            target = selex[0].Object
            so = selex[0].SubObjects[0]
        except:
            FreeCAD.Console.PrintError("No geometry selected\n")
            return
        if type(so) == Part.Vertex:
            pick = so.Point
        else:
            pick = so.CenterOfMass
        if hasattr(target, "PType") and hasattr(
            target, "Ports"
        ):  # ...selection is another pype-object
            pos, Z = nearestPort(target, pick)[1:]
        elif fCmd.edges([selex[0]]):  # one or more edges selected...
            edge = fCmd.edges([selex[0]])[0]
            if edge.curvatureAt(0) != 0:  # ...and the first is curve
                pos = edge.centerOfCurvatureAt(0)
                Z = edge.tangentAt(0).cross(edge.normalAt(0))
    # now place pypeObject on target
    pOport = pypeObject.Ports[port]
    if pOport == FreeCAD.Vector():
        pOport = pypeObject.Ports[port]
        if pOport == FreeCAD.Vector():
            pOport = FreeCAD.Vector(0, 0, -1)
    pypeObject.Placement = FreeCAD.Placement(
        pos + Z * pOport.Length, FreeCAD.Rotation(pOport * -1, Z)
    )


def nearestPort(pypeObject, point):
    try:
        pos = portsPos(pypeObject)[0]
        Z = portsDir(pypeObject)[0]
        i = nearest = 0
        for p in portsPos(pypeObject)[1:]:
            i += 1
            if (p - point).Length < (pos - point).Length:
                pos = p
                Z = portsDir(pypeObject)[i]
                nearest = i
        return nearest, pos, Z
    except:
        return None


def extendTheTubes2intersection(pipe1=None, pipe2=None, both=True):
    """
    Does what it says; also with beams.
    If arguments are None, it picks the first 2 selected beams().
    """
    if not (pipe1 and pipe2):
        try:
            pipe1, pipe2 = fCmd.beams()[:2]
        except:
            FreeCAD.Console.PrintError("Insufficient arguments for extendTheTubes2intersection\n")
    P = fCmd.intersectionCLines(pipe1, pipe2)
    if P != None:
        fCmd.extendTheBeam(pipe1, P)
        if both:
            fCmd.extendTheBeam(pipe2, P)


def header():  # start 20200725
    """
    creates an header with multiple branches
    """
    import BOPTools.JoinFeatures

    branches = fCmd.beams()
    for p in branches:
        if not hasattr(p, "PType"):
            branches.pop(branches.index(p))
        elif p.PType != "Pipe":
            branches.pop(branches.index(p))
    if len(branches) > 1:
        header = branches.pop(0)
        print("Header is " + header.Label)
        pl = header.Placement
        for t in [header] + branches:
            t.Placement = pl.inverse().multiply(t.Placement)
        O = FreeCAD.Vector(0, 0, 0)
        Z = FreeCAD.Vector(0, 0, 1)
        for t in branches:
            P = t.Proxy.nearestPort(FreeCAD.Vector())[1]
            if t.Proxy.nearestPort(O)[0]:
                u = fCmd.beamAx(t).negative()
            else:
                u = fCmd.beamAx(t)
            I = P.projectToPlane(O, u)
            I[2] = 0.0
            # migliorare aggiustamento delta in funzione di ang e t.OD
            delta = (
                (float(header.OD / 2) ** 2 - I.Length**2) ** 0.5
                - float(header.thk)
                - float(t.OD / 2)
            )
            if (
                round(u.dot(Z), 5) or delta.imag
            ):  # or round(I.Length+float(t.OD)/2,3)>round(float(header.OD)/2,3):
                print("%s has exception and will not be connected" % (t.Label))
                branches[branches.index(t)] = None
                t.Placement = pl.multiply(t.Placement)
            else:
                fCmd.extendTheBeam(t, I + u * delta)
            ### join and move back
        branches = [b for b in branches if b]
        if branches:
            join = BOPTools.JoinFeatures.makeConnect("Header")
            join.Objects = [header] + branches
            join.Placement = pl
            join.Refine = True
            for pipe in join.Objects:
                pipe.ViewObject.Visibility = False
        else:
            header.Placement = pl.multiply(header.Placement)
        FreeCAD.activeDocument().recompute()
    else:
        FreeCAD.Console.PrintError("Insufficient pipes selected\n")


def laydownTheTube(pipe=None, refFace=None, support=None):
    """
    laydownTheTube(pipe=None, refFace=None, support=None)
    Makes one pipe touch one face if the center-line is parallel to it.
    If support is not None, support is moved towards pipe.
    """
    if not (pipe and refFace):  # without argument take from selection set
        refFace = [f for f in fCmd.faces() if type(f.Surface) == Part.Plane][0]
        pipe = [p for p in fCmd.beams() if hasattr(p, "OD")][0]
    try:
        if (
            type(refFace.Surface) == Part.Plane
            and fCmd.isOrtho(refFace, fCmd.beamAx(pipe))
            and hasattr(pipe, "OD")
        ):
            dist = rounded(
                refFace.normalAt(0, 0).multiply(
                    refFace.normalAt(0, 0).dot(pipe.Placement.Base - refFace.CenterOfMass)
                    - float(pipe.OD) / 2
                )
            )
            if support:
                support.Placement.move(dist)
            else:
                pipe.Placement.move(dist.multiply(-1))
        else:
            FreeCAD.Console.PrintError("Face is not flat or not parallel to axis of pipe\n")
    except:
        FreeCAD.Console.PrintError("Wrong selection\n")


def breakTheTubes(point, pipes=[], gap=0):
    """
    breakTheTube(point,pipes=[],gap=0)
    Breaks the "pipes" at "point" leaving a "gap".
    """
    pipes2nd = list()
    if not pipes:
        pipes = [p for p in fCmd.beams() if isPipe(p)]
    if pipes:
        for pipe in pipes:
            if point < float(pipe.Height) and gap < (float(pipe.Height) - point):
                rating=pipe.PRating
                propList = [
                    pipe.PSize,
                    float(pipe.OD),
                    float(pipe.thk),
                    float(pipe.Height) - point - gap,
                ]
                pipe.Height = point
                Z = fCmd.beamAx(pipe)
                pos = pipe.Placement.Base + Z * (float(pipe.Height) + gap)
                pipe2nd = makePipe(rating,propList, pos, Z)
                pipes2nd.append(pipe2nd)
        # FreeCAD.activeDocument().recompute()
    return pipes2nd


def drawAsCenterLine(obj):
    try:
        obj.ViewObject.LineWidth = 4
        obj.ViewObject.LineColor = 1.0, 0.3, 0.0
        obj.ViewObject.DrawStyle = "Dashdot"
    except:
        FreeCAD.Console.PrintError("The object can not be center-lined\n")


def getElbowPort(elbow, portId=0):
    """
    getElbowPort(elbow, portId=0)
     Returns the position of the specified port of elbow.
    """
    if isElbow(elbow):
        return elbow.Placement.multVec(elbow.Ports[portId])


def rotateTheTeePort(curve=None, port=0, ang=45):
    if curve == None:
        try:
            curve = FreeCADGui.Selection.getSelection()[0]
            if not isTee(curve):
                FreeCAD.Console.PrintError("Please select a Tee.\n")
                return
        except:
            FreeCAD.Console.PrintError("Please select something before.\n")
    rotateTheTubeAx(curve, curve.Ports[port], ang)

def rotateTheElbowPort(curve=None, port=0, ang=45):
    """
    rotateTheElbowPort(curve=None, port=0, ang=45)
     Rotates one curve around one of its circular edges.
    """
    if curve == None:
        try:
            curve = FreeCADGui.Selection.getSelection()[0]
            if not isElbow(curve):
                FreeCAD.Console.PrintError("Please select an elbow.\n")
                return
        except:
            FreeCAD.Console.PrintError("Please select something before.\n")
    rotateTheTubeAx(curve, curve.Ports[port], ang)


def join(obj1, port1, obj2, port2):
    """
    join(obj1,port1,obj2,port2)
    \t obj1, obj2 = two "Pype" parts
    \t port1, port2 = their respective ports to join
    """
    if hasattr(obj1, "PType") and hasattr(obj2, "PType"):
        if port1 > len(obj1.Ports) - 1 or port2 > len(obj2.Ports) - 1:
            FreeCAD.Console.PrintError("Wrong port(s) number\n")
        else:
            v1 = portsDir(obj1)[port1]
            v2 = portsDir(obj2)[port2]
            rot = FreeCAD.Rotation(v2, v1.negative())
            obj2.Placement.Rotation = rot.multiply(obj2.Placement.Rotation)
            p1 = portsPos(obj1)[port1]
            p2 = portsPos(obj2)[port2]
            obj2.Placement.move(p1 - p2)
    else:
        FreeCAD.Console.PrintError("Object(s) are not pypes\n")


def makeValve(propList=[], pos=None, Z=None, flgPropList=None, actuator="Handle"):
    """Add a Valve object.

    makeValve(propList, pos, Z, flgPropList, actuator)

    propList elements for the basic double-cone valve rendering path:
      DN      (string): nominal diameter
      VType   (string): valve type
      ODBody  (float) : body outer diameter
      ID      (float) : bore inside diameter
      H       (float) : body length
      Kv      (float) : flow factor  [optional]

    propList elements for the socket-weld / threaded path:
      DN      (string): nominal diameter
      VType   (string): valve type
      OD      (float) : attachment pipe outer diameter
      ODBody  (float) : hex body flat-to-flat
      H       (float) : body length
      E       (float) : socket / thread engagement depth
      Conn    (string): "SW" or "TH"
      Kv      (float) : flow factor  [optional]

    propList elements for the flanged (Trunnion Ball) path:
      DN      (string): nominal diameter
      VType   (string): valve type (e.g. "Ball_LongPatternRF")
      H       (float) : body length, flange face to flange face
      Kv      (float) : flow factor  [optional]
      Conn    (string): pressure class, e.g. "150lb"

    flgPropList — list of blind-flange properties read from the matching
      Flange_ASME-BL-RF-<Conn>.csv table.  Elements in order:
      [PSize, FlangeType, D, t, f, n, df, drf, trf]
      (Same column order as the CSV, matching the Flange __init__ signature.)
      When provided the flanged construction path is used automatically.

    actuator -- "Handle" (default) or "Gearbox".  Applies to flanged valves only.

    pos (Vector): insertion point; default = origin
    Z   (Vector): flow-axis direction; default = (0,0,1)
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)

    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Valve")

    if flgPropList is not None:
        # Flanged valve path.
        # propList: [DN, VType, H, (Kv), Conn]
        DN    = propList[0] if len(propList) > 0 else "DN50"
        VType = propList[1] if len(propList) > 1 else "Ball_LongPatternRF"
        H     = float(propList[2]) if len(propList) > 2 else 200.0
        Kv    = float(propList[3]) if len(propList) > 3 else 0.0
        Conn  = str(propList[4]) if len(propList) > 4 else "150lb"
        # flgPropList: [PSize, FlangeType, D, t, f, n, df, drf, trf]
        flgD   = float(flgPropList[2]) if len(flgPropList) > 2 else 0.0
        flgt   = float(flgPropList[3]) if len(flgPropList) > 3 else 0.0
        flgf   = float(flgPropList[4]) if len(flgPropList) > 4 else 0.0
        flgn   = int(float(flgPropList[5])) if len(flgPropList) > 5 else 0
        flgdf  = float(flgPropList[6]) if len(flgPropList) > 6 else 0.0
        flgdrf = float(flgPropList[7]) if len(flgPropList) > 7 else 0.0
        flgtrf = float(flgPropList[8]) if len(flgPropList) > 8 else 0.0
        pFeatures.Valve(a, DN=DN, VType=VType, H=H, Kv=Kv, Conn=Conn,
                        flgD=flgD, flgt=flgt, flgdrf=flgdrf, flgtrf=flgtrf,
                        flgdf=flgdf, flgf=flgf, flgn=flgn,
                        actuator=actuator)
    elif propList:
        # Detect socket/threaded variant by the presence of a "Conn" field.
        # Convention: propList for the SW/TH path carries Conn as element [6]
        # (after DN, VType, OD, ODBody, H, E).
        if len(propList) >= 7 and isinstance(propList[6], str) and \
                propList[6] in ("SW", "TH"):
            # [DN, VType, OD, ODBody, H, E, Conn, (Kv)]
            DN, VType, OD, ODBody, H, E, Conn = propList[:7]
            Kv = float(propList[7]) if len(propList) >= 8 else 0.0
            pFeatures.Valve(a, DN=DN, VType=VType, ODBody=ODBody, H=H, Kv=Kv,
                            OD=OD, E=E, Conn=Conn)
        else:
            # Legacy path: [DN, VType, ODBody, ID, H, (Kv)]
            pFeatures.Valve(a, *propList)
    else:
        pFeatures.Valve(a)

    ViewProvider(a.ViewObject, "Quetzal_InsertValve")

    # Orient port 0's local direction to face Z, then place origin so that
    # port 0 lands at pos.  (Mirrors the pattern used by makeElbow / makePipe.)
    port0_local_dir = a.PortDirections[0] if a.PortDirections else FreeCAD.Vector(0, 0, 1)
    rot = FreeCAD.Rotation(port0_local_dir, Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    port0_world = a.Placement.multVec(a.Ports[0])
    a.Placement.Base = pos - port0_world

    a.Label = translate("Objects", "Valve")
    return a


def doValves(propList=["DN50", "ball", 72, 50, 40, 150], pypeline=None, pos=0,
             flgPropList=None, actuator="Handle"):
    """Insert one or more Valve objects.

    propList  -- see makeValve() for the accepted formats.
    pypeline  -- optional pypeline label to add the valve to.
    pos       -- legacy: position along pipe (0-100 %).  Kept for back-compat.
                 When a pype-object with ports is selected the new attachment
                 method (getAttachmentPoints / alignTwoPorts) is used instead.
    flgPropList -- optional list of blind-flange properties for flanged valves.
                   When supplied the flanged construction path is used.
                   Elements: [PSize, FlangeType, D, t, f, n, df, drf, trf]
    actuator    -- "Handle" (default) or "Gearbox".  Flanged valves only.
    """
    color  = 0.05, 0.3, 0.75
    vlist  = []
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert valve"))

    if 0 < pos < 100:
        # -- legacy: split a pipe and insert valve in the gap ----------------
        pipes = [p for p in FreeCADGui.Selection.getSelection() if isPipe(p)]
        if pipes:
            for p1 in pipes:
                valve = makeValve(propList, flgPropList=flgPropList, actuator=actuator)
                vlist.append(valve)
                p2 = breakTheTubes(
                    float(p1.Height) * pos / 100,
                    pipes=[p1],
                    gap=float(vlist[-1].Height),
                )
                if p2 and pypeline:
                    moveToPyLi(p2[0], pypeline)
                vlist[-1].Placement = p1.Placement
                vlist[-1].Placement.move(portsDir(p1)[1] * float(p1.Height))
                vlist[-1].ViewObject.ShapeColor = color
    else:
        try:
            selex = FreeCADGui.Selection.getSelectionEx()[0]
            usablePorts = (
                hasattr(selex.Object, "Ports")
                and hasattr(selex.Object, "PType")
                and selex.Object.PType != "Any"
            )
            pos_vec, Z_vec, srcObj, srcPort = getAttachmentPoints()

            if usablePorts:
                valve = makeValve(propList, pos_vec, Z_vec, flgPropList=flgPropList, actuator=actuator)
                vlist.append(valve)
                valve.ViewObject.ShapeColor = color
                FreeCAD.activeDocument().commitTransaction()
                FreeCAD.activeDocument().recompute()
                alignTwoPorts(valve, 0, srcObj, srcPort)
            else:
                valve = makeValve(propList, pos_vec, Z_vec, flgPropList=flgPropList, actuator=actuator)
                vlist.append(valve)
                valve.ViewObject.ShapeColor = color
        except Exception:
            # Nothing selected -- insert at origin
            valve = makeValve(propList, flgPropList=flgPropList, actuator=actuator)
            vlist.append(valve)
            valve.ViewObject.ShapeColor = color

    if pypeline:
        for v in vlist:
            moveToPyLi(v, pypeline)

    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return vlist


def makeNozzle(DN="DN50", H=200, OD=60.3, thk=3, D=160, d=62, df=132, f=14, t=15, n=4):
    """
    makeNozzle(DN,OD,thk,D,df,f,t,n)
      DN (string): nominal diameter
      OD (float): pipe outside diameter
      thk (float): pipe wall thickness
      D (float): flange diameter
      d (float): flange hole
      df (float): bolts holes distance
      f (float): bolts holes diameter
      t (float): flange thickness
      n (int): nr. of bolts
    """
    selex = FreeCADGui.Selection.getSelectionEx()
    for sx in selex:
        # e=sx.SubObjects[0]
        s = sx.Object
        curved = [e for e in fCmd.edges([sx]) if e.curvatureAt(0)]
        for e in curved:
            pipe = makePipe(
                [DN, OD, thk, H],
                pos=e.centerOfCurvatureAt(0),
                Z=e.tangentAt(0).cross(e.normalAt(0)),
            )
            FreeCAD.ActiveDocument.recompute()
            flange = makeFlange(
                [DN, "S.O.", D, d, df, f, t, n], pos=portsPos(pipe)[1], Z=portsDir(pipe)[1]
            )
            pipe.MapReversed = False
            pipe.AttachmentSupport = [(s, fCmd.edgeName(s, e)[1])]
            pipe.MapMode = "Concentric"
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(pipe)
            FreeCADGui.Selection.addSelection(flange)
            flange.AttachmentSupport = [(pipe, "Edge1")]
            flange.MapReversed = True
            flange.MapMode = "Concentric"
            FreeCAD.ActiveDocument.recompute()


def makeRoute(n=Z):
    curvedEdges = [e for e in fCmd.edges() if e.curvatureAt(0) != 0]
    if curvedEdges:
        s = FreeCAD.ActiveDocument.addObject("Sketcher::SketchObject", "pipeRoute")
        s.Label = translate("Objects", "Pipe route")
        s.MapMode = "SectionOfRevolution"
        sup = fCmd.edgeName()
        s.AttachmentSupport = [sup]
        if fCmd.isPartOfPart(
            sup[0]
        ):  # TARGET [working]: takes care if support belongs to App::Part
            part = fCmd.isPartOfPart(sup[0])
            FreeCAD.Console.PrintMessage(
                "*** " + sup[0].Label + " is part of " + part.Label + " ***\n"
            )  # debug
            # s.AttachmentOffset=part.Placement.multiply(s.AttachmentOffset)
    else:
        return None
    if fCmd.faces():
        n = fCmd.faces()[0].normalAt(0, 0)
    x = s.Placement.Rotation.multVec(X)
    z = s.Placement.Rotation.multVec(Z)
    t = x.dot(n) * x + z.dot(n) * z
    alfa = degrees(z.getAngle(t))
    if t.Length > 0.000000001:
        s.AttachmentOffset.Rotation = s.AttachmentOffset.Rotation.multiply(
            FreeCAD.Rotation(Y, alfa)
        )
    FreeCAD.ActiveDocument.recompute()
    FreeCADGui.activeDocument().setEdit(s.Name)


def flatten(p1=None, p2=None, c=None):
    if not (p1 and p2) and len(fCmd.beams()) > 1:
        p1, p2 = fCmd.beams()[:2]
    else:
        FreeCAD.Console.PrintError("Select two intersecting pipes\n")
    if not c:
        curves = [
            e
            for e in FreeCADGui.Selection.getSelection()
            if hasattr(e, "PType") and hasattr(e, "BendAngle")
        ]
        if curves:
            c = curves[0]
    else:
        FreeCAD.Console.PrintError("Select at least one elbow")
    try:
        P = fCmd.intersectionCLines(p1, p2)
        com1 = p1.Shape.Solids[0].CenterOfMass
        com2 = p2.Shape.Solids[0].CenterOfMass
        v1 = P - com1
        v2 = com2 - P
        FreeCAD.activeDocument().openTransaction(translate("Transaction", "Place one curve"))
        placeoTherElbow(curves[0], v1, v2, P)
        FreeCAD.ActiveDocument.recompute()  # recompute for the elbow
        port1, port2 = portsPos(curves[0])
        if (com1 - port1).Length < (com1 - port2).Length:
            fCmd.extendTheBeam(p1, port1)
            fCmd.extendTheBeam(p2, port2)
        else:
            fCmd.extendTheBeam(p1, port2)
            fCmd.extendTheBeam(p2, port1)
        FreeCAD.ActiveDocument.recompute()  # recompute for the pipes
        FreeCAD.ActiveDocument.commitTransaction()
    except:
        FreeCAD.Console.PrintError("Intersection point not found\n")


def makeRegularPolygon(n,r):
    """
    make a Wire with polygon shape
    n : number of sides.
    r : circunscrit radius
    """
    from math import cos, sin, pi
    vecs = [FreeCAD.Vector(cos(2*pi*i/n)*r, sin(2*pi*i/n)*r) for i in range(n+1)]
    return Part.makePolygon(vecs)

def makeGasket(propList=[], pos=None, Z=None):
    """Add a Gasket object.
    makeGasket(propList, pos, Z)
      propList is one optional list with 8 elements:
        DN (string): nominal diameter
        FClass (string): flange class / pressure rating
        IRID (float): inner ring inner diameter
        SEID (float): sealing element inner diameter
        SEOD (float): sealing element outer diameter
        CROD (float): centering ring outer diameter
        SEthk (float): sealing element thickness
        Rthk (float): inner and centering ring thickness
      pos (vector): position of insertion; defaul  t = 0,0,0
      Z (vector): orientation; default = 0,0,1
    
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Gasket")
    
    if len(propList) == 8:
        rating = propList[1]   # FClass / PRating is the second element
        pFeatures.Gasket(a, rating, *propList)
    else:
        pFeatures.Gasket(a, "150lb")

    ViewProvider(a.ViewObject, "Quetzal_InsertGasket") 
    a.ViewObject.ShapeColor = (1.0, 1.0, 0.0)   # yellow
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    a.Label = translate("Objects", "Gasket")
    return a


def doGaskets(propList=[], pypeline=None):
    """Insert one or more Gasket objects at the current selection.
    propList = [
      DN (string): nominal diameter
      FClass (string): flange class / pressure rating
      IRID (float): inner ring inner diameter
      SEID (float): sealing element inner diameter
      SEOD (float): sealing element outer diameter
      CROD (float): centering ring outer diameter
      SEthk (float): sealing element thickness
      Rthk (float): inner and centering ring thickness ]
    pypeline = string
    """
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert gasket"))
    glist = []
    connecting_port = 0  # gaskets connect via Port[0] (the -Z face) to the mating flange face
    try:
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType") and selex.Object.PType != "Any":
                usablePorts = True

        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            gasket = makeGasket(propList, pos, Z)
            glist.append(gasket)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(gasket, connecting_port, srcObj, srcPort)
        else:
            glist.append(makeGasket(propList, pos, Z))
    except:
        # nothing selected -- insert at origin
        glist.append(makeGasket(propList))

    if pypeline:
        for g in glist:
            moveToPyLi(g, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return glist


def makeBolts_Nuts(propList=[], pos=None, Z=None):
    """Add a Bolts_Nuts object.
    makeBolts_Nuts(propList, pos, Z)
      propList is one optional list with 9 elements:
        DN (string)   : nominal diameter
        FClass (string): flange class / pressure rating
        dBolt (float) : stud bolt cylinder outer diameter
        dNut (float)  : hex nut circumscribed circle outer diameter
        tNut (float)  : hex nut extruded length
        df (float)    : bolt center distance from flange centerline
        n (int)       : number of bolts per flange
        lBolt (float) : bolt length
        SEthk (float) : sealing element thickness from matching gasket
      pos (vector)    : position of insertion; default = 0,0,0
      Z (vector)      : orientation; default = 0,0,1
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Bolts_Nuts")

    if len(propList) == 9:
        rating = propList[1]  # FClass is the second element
        pFeatures.Bolts_Nuts(a, rating, *propList)
    else:
        pFeatures.Bolts_Nuts(a, "150lb")

    ViewProvider(a.ViewObject, "Quetzal_InsertGasket")
    a.ViewObject.ShapeColor = (0.7, 0.7, 0.7)   # light gray for metal
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    a.Label = translate("Objects", "Bolts_Nuts")
    return a


def doBolts_Nuts(propList=[], pypeline=None):
    """Insert one or more Bolts_Nuts objects at the current selection.
    propList = [
      DN (string)   : nominal diameter
      FClass (string): flange class / pressure rating
      dBolt (float) : stud bolt cylinder outer diameter
      dNut (float)  : hex nut circumscribed circle outer diameter
      tNut (float)  : hex nut extruded length
      df (float)    : bolt center distance from flange centerline
      n (int)       : number of bolts per flange
      lBolt (float) : bolt length
      SEthk (float) : sealing element thickness from matching gasket ]
    pypeline = string
    """
    FreeCAD.activeDocument().openTransaction(
        translate("Transaction", "Insert bolts and nuts")
    )
    blist = []
    connecting_port = 0  # bolts connect via Port[0] (the -Z face) to the mating flange face
    try:
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType") and selex.Object.PType != "Any":
                usablePorts = True

        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            bn = makeBolts_Nuts(propList, pos, Z)
            blist.append(bn)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(bn, connecting_port, srcObj, srcPort)
        else:
            blist.append(makeBolts_Nuts(propList, pos, Z))
    except:
        # nothing selected -- insert at origin
        blist.append(makeBolts_Nuts(propList))

    if pypeline:
        for b in blist:
            moveToPyLi(b, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return blist


def makeBeam(propList=[], pos=None, Z=None):
    """Add a Beam structural section object.
    makeBeam(propList, pos, Z)
      propList elements:
        rating  (str)   : section standard, e.g. "HEA"
        SSize   (str)   : section designation, e.g. "HEA200"
        stype   (str)   : profile type code: "H", "R", "RH", "U", "L", "T", "circle"
        H       (float) : section height (mm)
        W       (float) : section width (mm)
        ta      (float) : web / wall thickness (mm)
        tf      (float) : flange thickness (mm)
        Height  (float) : beam length (mm)
      pos (vector): insertion point; default = origin
      Z   (vector): axis direction; default = +Z
    """
    import fFeatures
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Beam")
    if len(propList) == 8:
        fFeatures.Beam(a, *propList)
    else:
        fFeatures.Beam(a)
    fFeatures.ViewProviderBeam(a.ViewObject)
    a.Placement.Base = pos
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    a.Label = translate("Objects", "Beam")
    return a


def doBeams(propList=[], frameline=None):
    """Insert one or more Beam objects at the current selection.
    propList: see makeBeam() for element order.
    frameline: label of a FrameLine group to add the beam to (optional).

    Selection behaviour mirrors doPipes():
      - ported object selected -> snap Port[0] to that port
      - straight edge selected -> align along edge, set Height to edge length
      - curved edge selected   -> align to edge axis at centre of curvature
      - vertex selected        -> place at vertex, default orientation
      - nothing selected       -> place at origin
    """
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert beam"))
    blist = []
    try:
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = (
            hasattr(selex.Object, "Ports")
            and hasattr(selex.Object, "FType")
            and selex.Object.FType != "Any"
        )

        pos, Z, srcObj, srcPort = getAttachmentPoints()

        # If a straight edge was selected, override Height to match edge length
        edgeLen = None
        eds = fCmd.edges([selex])
        if eds and eds[0].curvatureAt(0) == 0:
            edgeLen = eds[0].Length

        if usablePorts:
            beam = makeBeam(propList, pos, Z)
            if edgeLen is not None:
                beam.Height = edgeLen
            blist.append(beam)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(beam, 0, srcObj, srcPort)
        else:
            beam = makeBeam(propList, pos, Z)
            if edgeLen is not None:
                beam.Height = edgeLen
            blist.append(beam)

    except Exception:
        blist.append(makeBeam(propList))

    if frameline:
        for b in blist:
            _moveToFrameLine(b, frameline)

    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return blist


def _moveToFrameLine(obj, flName):
    """Move obj into the group of FrameLine flName (analogous to moveToPyLi)."""
    try:
        fl = FreeCAD.ActiveDocument.getObjectsByLabel(flName)[0]
        group = FreeCAD.ActiveDocument.getObjectsByLabel(str(fl.Group))[0]
        group.addObject(obj)
    except Exception:
        pass


def makeOutlet(propList=[], pos=None, rot=None, carrierOD=0.0):
    """
    makeOutlet(propList, pos, rot, carrierOD=0.0)

    Creates and returns a single Outlet object.

    propList elements:
      [0]  rating   str    "Sch-STD" | "3000lb" etc.
      [1]  DN       str    "DN50"
      [2]  OD       float  outside diameter at pipe end  (mm)
      [3]  thk      float  wall thickness at pipe end    (mm)
      [4]  A        float  height above run-pipe surface (mm)
      [5]  B        float  outer diameter at base        (mm)
      [6]  endType  str    "BW" or "SW"  (from CSV Conn column)
      [7]  angle    int    0 (straight) | 45 (lateral)
      [8]  E        float  socket depth (SW only)

    pos       : FreeCAD.Vector    - world position of the fitting base
    rot       : FreeCAD.Rotation  - full world rotation (replaces the old Z-only arg)
                                    If None, identity rotation is used.
    carrierOD : float             - outer diameter of the carrier (run) pipe (mm).
                                    When non-zero the fitting base is shaped to sit
                                    flush on the pipe surface rather than cut flat.
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if rot is None:
        rot = FreeCAD.Rotation()

    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Outlet")
    if len(propList) >= 9:
        pFeatures.Outlet(a, *propList, carrierOD=carrierOD)
    elif len(propList) >= 8:
        pFeatures.Outlet(a, *propList, E=0.0, carrierOD=carrierOD)
    else:
        pFeatures.Outlet(a, carrierOD=carrierOD)

    ViewProvider(a.ViewObject, "Quetzal_InsertOutlet")
    a.Placement = FreeCAD.Placement(pos, rot)
    FreeCAD.ActiveDocument.recompute()
    a.Label = translate("Objects", "Outlet")
    return a


# ---- placement helpers --------------------------------------------------------

def outletPlacementOnPipe(pipeObj, t, phi_deg, alpha_deg=0.0):
    """
    Return (pos_world, rot_world) for an outlet on a Pipe's outer surface.

    pipeObj   : FreeCAD Pipe object
    t         : float  - axial distance from Port[0] (mm).  Range 0..Height.
    phi_deg   : float  - circumferential angle (deg) from pipe local +X,
                         measured CCW when viewed from Port[1].
    alpha_deg : float  - spin of the fitting around its own outward axis (deg).
                         For straight fittings this has no visible effect.
                         For 45-deg lateral: 0 = branch points along pipe axis,
                         90 = branch points circumferentially.

    Returns (pos_world, rot_world) where rot_world is a FreeCAD.Rotation.
    """
    import math
    phi = math.radians(phi_deg)
    r   = float(pipeObj.OD) / 2.0

    # Local attachment point and outward radial direction
    local_pos = FreeCAD.Vector(r * math.cos(phi), r * math.sin(phi), t)
    local_dir = FreeCAD.Vector(math.cos(phi), math.sin(phi), 0.0)

    pos_world = pipeObj.Placement.multVec(local_pos)
    Z_world   = pipeObj.Placement.Rotation.multVec(local_dir).normalize()

    # Base rotation: align fitting local +Z with Z_world
    base_rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z_world)

    # Spin rotation around Z_world.
    # Reference (alpha=0): fitting local +Y aligns with pipe run axis.
    # Compute alpha_offset = angle from base_rot.multVec(Y) to pipe_axis_world,
    # measured around Z_world.
    pipe_axis = pipeObj.Placement.Rotation.multVec(
        FreeCAD.Vector(0, 0, 1)).normalize()
    mapped_Y  = base_rot.multVec(FreeCAD.Vector(0, 1, 0)).normalize()
    e2        = Z_world.cross(mapped_Y).normalize()
    alpha_offset = math.degrees(math.atan2(
        pipe_axis.dot(e2), pipe_axis.dot(mapped_Y)))

    spin_rot  = FreeCAD.Rotation(Z_world, alpha_deg + alpha_offset)
    final_rot = spin_rot.multiply(base_rot)

    return pos_world, final_rot


def outletPlacementOnTee(teeObj, t, phi_deg, alpha_deg=0.0):
    """
    Return (pos_world, rot_world) for an outlet on a Tee's run-pipe surface.

    t         : float  - distance from Port[0] of the run (z=-C).  Range 0..2C.
    phi_deg   : float  - circumferential angle (deg) from tee local +X.
                         Branch is at ~90 deg (+Y); opposite branch = 270 deg.
    alpha_deg : float  - spin around fitting axis.  0 = branch along run axis.
    """
    import math
    phi = math.radians(phi_deg)
    r   = float(teeObj.OD) / 2.0
    C   = float(teeObj.C)

    z_local   = -C + t
    local_pos = FreeCAD.Vector(r * math.cos(phi), r * math.sin(phi), z_local)
    local_dir = FreeCAD.Vector(math.cos(phi), math.sin(phi), 0.0)

    pos_world = teeObj.Placement.multVec(local_pos)
    Z_world   = teeObj.Placement.Rotation.multVec(local_dir).normalize()

    base_rot  = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z_world)

    # Reference: alpha=0 aligns branch with tee run axis (local +Z of tee)
    run_axis  = teeObj.Placement.Rotation.multVec(
        FreeCAD.Vector(0, 0, 1)).normalize()
    mapped_Y  = base_rot.multVec(FreeCAD.Vector(0, 1, 0)).normalize()
    e2        = Z_world.cross(mapped_Y).normalize()
    alpha_offset = math.degrees(math.atan2(
        run_axis.dot(e2), run_axis.dot(mapped_Y)))

    spin_rot  = FreeCAD.Rotation(Z_world, alpha_deg + alpha_offset)
    final_rot = spin_rot.multiply(base_rot)

    return pos_world, final_rot


def outletPlacementOnElbow(elbowObj, alpha_deg=0.0):
    """
    Return (pos_world, rot_world) for an outlet at the outer midpoint of an Elbow.

    alpha_deg : float - spin around the fitting's outward axis (deg).
                0 = lateral branch points along the elbow run direction at the
                    midpoint (arc tangent direction), consistent with the
                    pipe/tee convention where 0 = branch along run axis.
    """
    import math
    BR = float(elbowObj.BendRadius)
    BA = float(elbowObj.BendAngle)
    OD = float(elbowObj.OD)

    half_rad = math.radians(BA / 2.0)
    d        = BR * math.sqrt(2) - BR / math.cos(half_rad)
    offset   = d * math.cos(math.pi / 4.0)
    arc_cx   = BR - offset
    arc_cy   = BR - offset

    a_mid  = math.radians(225.0)
    mid_x  = arc_cx + BR * math.cos(a_mid)
    mid_y  = arc_cy + BR * math.sin(a_mid)
    nx     = math.cos(a_mid)   # outward normal components
    ny     = math.sin(a_mid)

    local_pos = FreeCAD.Vector(mid_x + (OD / 2.0) * nx,
                               mid_y + (OD / 2.0) * ny, 0.0)
    local_dir = FreeCAD.Vector(nx, ny, 0.0)

    pos_world = elbowObj.Placement.multVec(local_pos)
    Z_world   = elbowObj.Placement.Rotation.multVec(local_dir).normalize()

    # Base rotation: align fitting local +Z with Z_world
    base_rot  = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z_world)

    # Reference direction for alpha=0: arc tangent at the midpoint in local coords.
    # Arc tangent at theta = (-sin(theta), cos(theta), 0).
    # At theta=225 deg this is (sin45, -cos45, 0) = (sqrt2/2, -sqrt2/2, 0).
    local_tangent = FreeCAD.Vector(-math.sin(a_mid), math.cos(a_mid), 0.0)
    arc_tangent_world = elbowObj.Placement.Rotation.multVec(
        local_tangent).normalize()

    # Compute alpha_offset so that alpha=0 aligns local +Y with arc tangent
    mapped_Y     = base_rot.multVec(FreeCAD.Vector(0, 1, 0)).normalize()
    e2           = Z_world.cross(mapped_Y).normalize()
    alpha_offset = math.degrees(math.atan2(
        arc_tangent_world.dot(e2), arc_tangent_world.dot(mapped_Y)))

    spin_rot  = FreeCAD.Rotation(Z_world, alpha_deg + alpha_offset)
    final_rot = spin_rot.multiply(base_rot)

    return pos_world, final_rot


def doOutlets(propList=None, pypeline=None,
              srcObj=None, t=None, phi_deg=None, alpha_deg=0.0):
    """
    Insert an Outlet fitting on the outer surface of srcObj (or current selection).

    propList : list  - see makeOutlet().
    pypeline : str   - PypeLine label (optional).
    srcObj   : the host Pipe / Tee / Elbow.  None = use FreeCAD selection.
    t        : float - axial position (mm).  None = default for object type.
    phi_deg  : float - circumferential angle (deg).  None = default.
    alpha_deg: float - spin around fitting axis (deg).  0 = branch along run axis.

    The carrier pipe outer diameter is extracted automatically from srcObj and
    passed to makeOutlet so that the fitting base is shaped to sit flush on the
    pipe surface.  When srcObj is unavailable the flat-base fallback is used.
    """
    if propList is None:
        propList = ["Sch-STD", "DN50", 60.32, 3.91, 45.0, 70.0, "BW", 0, 0.0]

    if srcObj is None:
        selex = FreeCADGui.Selection.getSelectionEx()
        if selex:
            srcObj = selex[0].Object

    pos        = None
    rot        = None
    carrierOD  = 0.0

    if srcObj is not None and hasattr(srcObj, "PType"):
        ptype = srcObj.PType

        # ── Extract the carrier pipe OD from the host object ──────────────
        # Pipe and Elbow expose OD directly; Tee's run pipe OD is also OD.
        if hasattr(srcObj, "OD"):
            try:
                carrierOD = float(srcObj.OD)
            except Exception:
                carrierOD = 0.0

        if ptype == "Pipe":
            H       = float(srcObj.Height)
            t_use   = H / 2.0 if t is None else max(0.0, min(t, H))
            phi_use = 0.0     if phi_deg is None else phi_deg
            pos, rot = outletPlacementOnPipe(srcObj, t_use, phi_use, alpha_deg)

        elif ptype == "Tee":
            C       = float(srcObj.C)
            t_use   = C     if t is None else max(0.0, min(t, 2.0 * C))
            phi_use = 270.0 if phi_deg is None else phi_deg
            pos, rot = outletPlacementOnTee(srcObj, t_use, phi_use, alpha_deg)

        elif ptype == "Elbow":
            pos, rot = outletPlacementOnElbow(srcObj, alpha_deg)

    if pos is None:
        try:
            pos, Z_dir, _src, _port = getAttachmentPoints()
            if Z_dir is not None:
                rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), Z_dir)
        except Exception:
            pass
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if rot is None:
        rot = FreeCAD.Rotation()

    FreeCAD.activeDocument().openTransaction(
        translate("Transaction", "Insert outlet"))
    obj = makeOutlet(propList, pos, rot, carrierOD=carrierOD)
    if pypeline:
        moveToPyLi(obj, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return [obj]

def makeSocketElbow(propList=[], pos=None, Z=None, rating="3000lb"):
    """Adds a SocketEll object.
    makeSocketElbow(propList, pos, Z, rating=rating)
      propList is one optional list with 8 elements:
        PSize     (string): nominal diameter
        OD        (float):  connecting pipe outside diameter
        BendAngle (float):  bend angle in degrees
        A         (float):  dimension from fitting center to outer edge
        C         (float):  wall thickness in socket
        D         (float):  bore internal diameter
        E         (float):  dimension from fitting center to base of socket
        G         (float):  inner body wall thickness
        Conn      (string): connection type ("SW"=Socket Weld, "TH"=Threaded)
      Default is "DN25"
      pos (vector): position of insertion; default = 0,0,0
      Z   (vector): orientation; default = 0,0,1
    Remember: property PRating must be defined afterwards
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "SocketElbow")
    if len(propList) == 9:
        pFeatures.SocketEll(a, rating, *propList)
    else:
        pFeatures.SocketEll(a, rating)
    ViewProvider(a.ViewObject, "Quetzal_InsertElbow")
    # Rotate so port[0]'s local direction faces Z.
    # SocketEll port[0] direction is (1,0,0) — local +X, not +Z — so the
    # reference axis must be port[0]'s actual local direction, not (0,0,1).
    port0_local_dir = a.PortDirections[0] if a.PortDirections else FreeCAD.Vector(0, 0, 1)
    rot = FreeCAD.Rotation(port0_local_dir, Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)
    # After rotation the object origin is still at (0,0,0). Translate so that
    # port[0] — now in its rotated world position — lands exactly at pos.
    port0_world = a.Placement.multVec(a.Ports[0])
    a.Placement.Base = pos - port0_world
    a.Label = translate("Objects", "SocketElbow")
    return a


def doSocketElbow(rating="3000lb", propList=["DN25", 33.4, 90, 35.0, 5.0, 25.4, 22.0, 5.455, "SW"], pypeline=None):
    """
    Insert a SocketEll fitting, aligning it to the selected port when possible.

    propList = [
      PSize     (string): nominal diameter
      OD        (float):  connecting pipe outside diameter
      BendAngle (float):  bend angle in degrees
      A         (float):  dimension from fitting center to outer edge
      C         (float):  wall thickness in socket
      D         (float):  bore internal diameter
      E         (float):  dimension from fitting center to base of socket
      G         (float):  inner body wall thickness
      Conn      (string): connection type ("SW" or "TH") ]
    pypeline = string (optional PypeLine label)

      - No selection         -> insert one SocketEll at the origin.
      - One or more sub-object-> insert at the closest port of the first selected
                                object and align port[0] of the new fitting
                                to that port.
          """
    
    elist = list()
    try:
        #first, if a an object with ports is selected and edges, faces, or vertices are selected, insert the component at the closest port to the 
        #first selected object's first selected edge, face, or vertex. If none of those are present, the entire object is selected - insert
        #the component at the highest number port.
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True
        
        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            socketEll = makeSocketElbow(propList, pos, Z, rating=rating)
            elist.append(socketEll)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(socketEll, 0, srcObj, srcPort)
        else:
            elist.append(makeSocketElbow(propList, pos, Z, rating=rating))
    except:
        #nothing selected, insert at origin
        elist.append(makeSocketElbow(propList, rating=rating))
        
    if pypeline:
        for e in elist:
            moveToPyLi(e, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return elist


def makeSocketTee(propList=[], pos=None, Z=None, insertOnBranch=False, rating="3000lb"):
    """Adds a SocketTee object.
    makeSocketTee(propList, pos, Z, insertOnBranch, rating=rating)
      propList is one optional list with 10 elements:
        PSize       (string): nominal diameter of run
        PSizeBranch (string): nominal diameter of branch
        OD          (float):  run pipe outside diameter
        OD2         (float):  branch pipe outside diameter
        A           (float):  centre to outer face of socket
        C           (float):  socket boss wall thickness
        D           (float):  bore internal diameter
        E           (float):  centre to base of socket
        G           (float):  inner body wall thickness
        Conn        (string): connection type ("SW" or "TH")
      pos (vector): world position of the insertion port; default = 0,0,0
      Z   (vector): desired outward direction of the insertion port; default = 0,0,1
      insertOnBranch (bool): if True use port[2] (+Y branch) as insertion port;
                             otherwise use port[0] (-Z run end).
    Remember: property PRating must be defined afterwards.
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "SocketTee")
    if len(propList) == 10:
        pFeatures.SocketTee(a, rating, *propList)
    else:
        pFeatures.SocketTee(a, rating)
    ViewProvider(a.ViewObject, "Quetzal_InsertTee")

    # Choose the insertion port and read its local direction from the object.
    # port[0] direction = (0, 0, -1)  — run end at -Z
    # port[2] direction = (0,  1,  0) — branch end at +Y
    insertion_port = 2 if insertOnBranch else 0
    port_local_dir = a.PortDirections[insertion_port] if a.PortDirections else FreeCAD.Vector(0, 0, 1)

    # Rotate so the insertion port's local direction faces Z.
    rot = FreeCAD.Rotation(port_local_dir, Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)

    # Translate so the insertion port lands exactly at pos.
    port_world = a.Placement.multVec(a.Ports[insertion_port])
    a.Placement.Base = pos - port_world

    a.Label = translate("Objects", "SocketTee")
    return a


def doSocketTee(rating="3000lb", propList=["DN25", "DN25", 33.4, 33.4, 35.0, 5.0, 25.4, 22.0, 5.455, "SW"],
                pypeline=None, insertOnBranch=False):
    """
    Insert a SocketTee fitting, aligning it to the selected port when possible.

    propList = [
      PSize       (string): nominal diameter of run
      PSizeBranch (string): nominal diameter of branch
      OD          (float):  run pipe outside diameter
      OD2         (float):  branch pipe outside diameter
      A           (float):  centre to outer face of socket
      C           (float):  socket boss wall thickness
      D           (float):  bore internal diameter
      E           (float):  centre to base of socket
      G           (float):  inner body wall thickness
      Conn        (string): connection type ("SW" or "TH") ]
    pypeline       = string (optional PypeLine label)
    insertOnBranch = bool   (True → insert/align on the branch port)

    Behaviour:
      - No selection          → insert at origin.
      - Ported object selected → align the insertion port to the selected port
                                  via alignTwoPorts.
      - Non-ported geometry   → insert with insertion port direction matching
                                  the selected face normal / edge tangent.
    """
    insertion_port = 2 if insertOnBranch else 0
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert socket tee"))
    plist = []
    try:
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True

        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            tee = makeSocketTee(propList, pos, Z, insertOnBranch, rating=rating)
            plist.append(tee)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(tee, insertion_port, srcObj, srcPort)
        else:
            plist.append(makeSocketTee(propList, pos, Z, insertOnBranch, rating=rating))
    except Exception:
        # Nothing selected — insert at origin.
        plist.append(makeSocketTee(propList, insertOnBranch=insertOnBranch))

    if pypeline:
        for t in plist:
            moveToPyLi(t, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist
def makeSocketCap(propList=[], pos=None, Z=None):
    """Adds a SocketCap object.
    makeSocketCap(propList, pos, Z)
      propList is one optional list with 6 elements:
        PSize (string): nominal diameter
        OD    (float):  connecting pipe outside diameter
        A     (float):  cap height
        C     (float):  socket boss wall thickness
        E     (float):  socket depth
        Conn  (string): connection type ("SW"=Socket Weld, "TH"=Threaded)
      pos (vector): position of insertion; default = 0,0,0
      Z   (vector): orientation; default = 0,0,1
    Remember: property PRating must be defined afterwards.
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)
    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "SocketCap")
    if len(propList) == 6:
        pFeatures.SocketCap(a, *propList)
    else:
        pFeatures.SocketCap(a)
    ViewProvider(a.ViewObject, "Quetzal_InsertCap")

    # SocketCap port[0] direction is (0,0,-1) — same axis as BW Cap
    # Rotate so port[0]'s local direction faces Z.
    port0_local_dir = a.PortDirections[0] if a.PortDirections else FreeCAD.Vector(0, 0, 1)
    rot = FreeCAD.Rotation(port0_local_dir, Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)

    # Translate so port[0] lands exactly at pos.
    port0_world = a.Placement.multVec(a.Ports[0])
    a.Placement.Base = pos - port0_world

    a.Label = translate("Objects", "SocketCap")
    return a


def doSocketCap(propList=["DN25", 33.4, 26.0, 5.0, 13.0, "SW"],
                pypeline=None):
    """
    Insert a SocketCap fitting, aligning it to the selected port when possible.

    propList = [
      PSize (string): nominal diameter
      OD    (float):  connecting pipe outside diameter
      A     (float):  cap height
      C     (float):  socket boss wall thickness
      E     (float):  socket depth
      Conn  (string): connection type ("SW" or "TH") ]
    pypeline = string (optional PypeLine label)

    Behaviour:
      - No selection          → insert at origin.
      - Ported object selected → align port[0] to the selected port
                                  via alignTwoPorts.
      - Non-ported geometry   → insert with port[0] direction matching
                                  the selected face normal / edge tangent.
    """
    FreeCAD.activeDocument().openTransaction(translate("Transaction", "Insert socket cap"))
    plist = []
    try:
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True

        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            cap = makeSocketCap(propList, pos, Z)
            plist.append(cap)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(cap, 0, srcObj, srcPort)
        else:
            plist.append(makeSocketCap(propList, pos, Z))
    except Exception:
        # Nothing selected — insert at origin.
        plist.append(makeSocketCap(propList))

    if pypeline:
        for t in plist:
            moveToPyLi(t, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist

def _makeSocketStraight(fcClass, label, iconName, propList, expectedLen,
                        pos=None, Z=None):
    """Create a two-port, straight-axis socket fitting (coupling or union),
    rotate so port[0]'s outward direction faces Z, then translate so port[0]
    lands at pos.

    This is an internal helper called by makeSocketCoupling and makeSocketUnion.
    """
    if pos is None:
        pos = FreeCAD.Vector(0, 0, 0)
    if Z is None:
        Z = FreeCAD.Vector(0, 0, 1)

    a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", label)
    if len(propList) == expectedLen:
        fcClass(a, *propList)
    else:
        fcClass(a)
    ViewProvider(a.ViewObject, iconName)

    # port[0] local direction is (0,0,-1); rotate so it aligns with Z.
    port0_local_dir = a.PortDirections[0] if a.PortDirections else FreeCAD.Vector(0, 0, 1)
    rot = FreeCAD.Rotation(port0_local_dir, Z)
    a.Placement.Rotation = rot.multiply(a.Placement.Rotation)

    # Translate so port[0] lands exactly at pos.
    port0_world = a.Placement.multVec(a.Ports[0])
    a.Placement.Base = pos - port0_world

    a.Label = translate("Objects", label)
    return a


def _doSocketStraight(makeFn, transactionLabel, propList, pypeline=None):
    """Insert a socket coupling or union, aligning to the selected port when
    possible.  Internal helper shared by doSocketCoupling and doSocketUnion.
    """
    FreeCAD.activeDocument().openTransaction(
        translate("Transaction", transactionLabel))
    plist = []
    try:
        selex = FreeCADGui.Selection.getSelectionEx()[0]
        usablePorts = False
        if hasattr(selex.Object, "Ports"):
            if hasattr(selex.Object, "PType"):
                if selex.Object.PType != "Any":
                    usablePorts = True

        pos, Z, srcObj, srcPort = getAttachmentPoints()
        if usablePorts:
            fitting = makeFn(propList, pos, Z)
            plist.append(fitting)
            FreeCAD.activeDocument().commitTransaction()
            FreeCAD.activeDocument().recompute()
            alignTwoPorts(fitting, 0, srcObj, srcPort)
        else:
            plist.append(makeFn(propList, pos, Z))
    except Exception:
        # Nothing selected — insert at origin.
        plist.append(makeFn(propList))

    if pypeline:
        for t in plist:
            moveToPyLi(t, pypeline)
    FreeCAD.activeDocument().commitTransaction()
    FreeCAD.activeDocument().recompute()
    return plist


# ── public API: SocketCoupling ────────────────────────────────────────────────

def makeSocketCoupling(propList=[], pos=None, Z=None):
    """Add a SocketCoupling object.
    makeSocketCoupling(propList, pos, Z)
      propList is one optional list with 9 elements:
        PSize  (string): nominal diameter of port 0
        PSize2 (string): nominal diameter of port 1
        OD     (float):  port 0 pipe outside diameter
        OD2    (float):  port 1 pipe outside diameter
        A      (float):  half-length (centre to outer edge)
        C      (float):  socket boss wall thickness
        D      (float):  bore diameter at centre
        E      (float):  socket depth
        Conn   (string): connection type ("SW" or "TH")
      pos (vector): world position of port[0]; default = 0,0,0
      Z   (vector): desired outward direction of port[0]; default = 0,0,1
    Remember: property PRating must be defined afterwards.
    """
    return _makeSocketStraight(
        pFeatures.SocketCoupling, "SocketCoupling",
        "Quetzal_InsertCoupling", propList, 9, pos, Z)


def doSocketCoupling(propList=["DN25", "DN25", 33.4, 33.4, 35.0, 5.0, 25.9, 22.0, "SW"],
                     pypeline=None):
    """Insert a SocketCoupling fitting, aligning it to the selected port when possible.

    propList = [
      PSize  (string): nominal diameter of port 0
      PSize2 (string): nominal diameter of port 1
      OD     (float):  port 0 pipe outside diameter
      OD2    (float):  port 1 pipe outside diameter
      A      (float):  half-length (centre to outer edge)
      C      (float):  socket boss wall thickness
      D      (float):  bore diameter at centre
      E      (float):  socket depth
      Conn   (string): connection type ("SW" or "TH") ]
    pypeline = string (optional PypeLine label)

    Behaviour:
      - No selection          → insert at origin.
      - Ported object selected → align port[0] to the selected port.
      - Non-ported geometry   → insert with port[0] direction matching
                                 face normal / edge tangent.
    """
    return _doSocketStraight(
        makeSocketCoupling, "Insert socket coupling", propList, pypeline)


# ── public API: SocketUnion ───────────────────────────────────────────────────

def makeSocketUnion(propList=[], pos=None, Z=None):
    """Add a SocketUnion object.
    makeSocketUnion(propList, pos, Z)
      propList is one optional list with 7 elements:
        PSize (string): nominal diameter
        OD    (float):  pipe outside diameter
        A     (float):  half-length (centre to outer edge)
        C     (float):  socket boss wall thickness
        D     (float):  bore diameter
        E     (float):  socket depth
        Conn  (string): connection type ("SW" or "TH")
      pos (vector): world position of port[0]; default = 0,0,0
      Z   (vector): desired outward direction of port[0]; default = 0,0,1
    Remember: property PRating must be defined afterwards.
    """
    return _makeSocketStraight(
        pFeatures.SocketUnion, "SocketUnion",
        "Quetzal_InsertCoupling", propList, 7, pos, Z)


def doSocketUnion(propList=["DN25", 33.4, 35.0, 5.0, 25.9, 22.0, "SW"],
                  pypeline=None):
    """Insert a SocketUnion fitting, aligning it to the selected port when possible.

    propList = [
      PSize (string): nominal diameter
      OD    (float):  pipe outside diameter
      A     (float):  half-length (centre to outer edge)
      C     (float):  socket boss wall thickness
      D     (float):  bore diameter
      E     (float):  socket depth
      Conn  (string): connection type ("SW" or "TH") ]
    pypeline = string (optional PypeLine label)

    Behaviour:
      - No selection          → insert at origin.
      - Ported object selected → align port[0] to the selected port.
      - Non-ported geometry   → insert with port[0] direction matching
                                 face normal / edge tangent.
    """
    return _doSocketStraight(
        makeSocketUnion, "Insert socket union", propList, pypeline)