# SPDX-License-Identifier: LGPL-3.0-or-later

__title__ = "pypeTools objects"
__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"
objs = ["Pipe", "Elbow","DuctReduction", "DuctElbow", "Reduct", "Cap", "Flange", "Tee", "Ubolt", "Valve"]
metaObjs = ["PypeLine", "PypeBranch"]

from os.path import abspath, dirname, join

import FreeCAD
import FreeCADGui
import Part

import fCmd
import pCmd
from quetzal_config import FREECADVERSION, get_icon_path

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate

vO = FreeCAD.Vector(0, 0, 0)
vX = FreeCAD.Vector(1, 0, 0)
vY = FreeCAD.Vector(0, 1, 0)
vZ = FreeCAD.Vector(0, 0, 1)
pipe_OD = {
    "DN6" : 10.29,
    "DN8" : 13.72,
    "DN10" : 17.14,
    "DN15" : 21.34,
    "DN20" : 26.67,
    "DN25" : 33.4,
    "DN32" : 42.16,
    "DN40" : 48.26,
    "DN50" : 60.32,
    "DN65" : 73.02,
    "DN80" : 88.9,
    "DN90" : 101.6,
    "DN100" : 114.3,
    "DN125" : 141.3,
    "DN150" : 168.27,
    "DN200" : 219.07,
    "DN250" : 273.05,
    "DN300" : 323.85,
    "DN350" : 355.6,
    "DN400" : 406.4,
    "DN450" : 457.2,
    "DN500" : 508,
    "DN550" : 558.8,
    "DN600" : 609.6
}

################ CLASSES ###########################


class pypeType(object):
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyString",
            "PType",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Type of tubeFeature"),
        ).PType
        obj.addProperty(
            "App::PropertyString",
            "PRating",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Rating of pipeFeature"),
        ).PRating
        obj.addProperty(
            "App::PropertyString",
            "PSize",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Nominal diameter"),
        ).PSize
        obj.addProperty(
            "App::PropertyVectorList",
            "Ports",
            "PBase",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Ports position relative to the origin of Shape",
            ),
        )
        obj.addProperty(
            "App::PropertyVectorList",
            "PortDirections",
            "PBase",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Port direction vectors (unit vectors pointing outward from each port)",
            ),
        )
        obj.addProperty(
            "App::PropertyFloat",
            "Kv",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Flow factor (m3/h/bar)"),
        ).Kv
        if FREECADVERSION > 0.19:
            obj.addExtension("Part::AttachExtensionPython")
        else:
            obj.addExtension("Part::AttachExtensionPython", obj)  # 20220704
        self.Name = obj.Name

    def execute(self, fp):
        fp.positionBySupport()  # to recomute placement according the Support

    def nearestPort(self, point=None):
        """
        nearestPort (point=None)
          Returns the Port nearest to  point
          or to the selected geometry.
          (<portNr>, <portPos>, <portDir>)
        """
        if FreeCAD.ActiveDocument:
            obj = FreeCAD.ActiveDocument.getObject(self.Name)
            if not point and FreeCADGui.ActiveDocument:
                try:
                    selex = FreeCADGui.Selection.getSelectionEx()
                    target = selex[0].Object
                    so = selex[0].SubObjects[0]
                except:
                    FreeCAD.Console.PrintError("No geometry selected\n")
                    return None
                if type(so) == Part.Vertex:
                    point = so.Point
                else:
                    point = so.CenterOfMass
            if point:
                pos = pCmd.portsPos(obj)[0]
                Z = pCmd.portsDir(obj)[0]
                i = nearest = 0
                if len(obj.Ports) > 1:
                    for p in pCmd.portsPos(obj)[1:]:
                        i += 1
                        if (p - point).Length < (pos - point).Length:
                            pos = p
                            Z = pCmd.portsDir(obj)[i]
                            nearest = i
                return nearest, pos, Z

class Pipe(pypeType):
    """Class for object PType="Pipe"
    Pipe(obj,[PSize="DN50",OD=60.3,thk=3, H=100])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
      H (float): length of pipe"""

    def __init__(self, obj,rating, DN="DN50", OD=60.3, thk=3, H=100):
        # initialize the parent class
        super(Pipe, self).__init__(obj)
        # define common properties
        obj.PType = "Pipe"
        obj.Proxy = self
        obj.PRating = rating
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "Pipe",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "Pipe",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        obj.addProperty(
            "App::PropertyLength",
            "ID",
            "Pipe",
            QT_TRANSLATE_NOOP("App::Property", "Inside diameter"),
        ).ID = obj.OD - 2 * obj.thk
        obj.addProperty(
            "App::PropertyLength",
            "Height",
            "Pipe",
            QT_TRANSLATE_NOOP("App::Property", "Length of tube"),
        ).Height = H
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "Pipe",
            QT_TRANSLATE_NOOP("App::Property", "Section dim."),
        ).Profile = str(obj.OD) + "x" + str(obj.thk)

        self.execute(obj)

    def onChanged(self, fp, prop):
        if prop == "ID" and fp.ID < fp.OD:
            fp.thk = (fp.OD - fp.ID) / 2

    def execute(self, fp):
        from math import tan

        try:
            parent = fp.getParentGroup()
            i = parent.Tubes.index(fp.Name)
            edges = parent.Base.Shape.Edges
            L = edges[i].Length
            R = parent.BendRadius
            if i < len(parent.Curves):
                v1, v2 = [e.tangentAt(0) for e in edges[i : i + 2]]
                alfa = float(v1.getAngle(v2)) / 2
                L -= float(R * tan(alfa))
            if i:
                v1, v2 = [e.tangentAt(0) for e in edges[i - 1 : i + 1]]
                alfa = float(v1.getAngle(v2)) / 2
                tang = float(R * tan(alfa))
                L -= tang
                fp.AttachmentOffset.Base = FreeCAD.Vector(0, 0, tang)
            fp.Height = L
        except Exception:
            #  FreeCAD.Console.PrintWarning(str(e) + "\n")
            pass
        if fp.thk > fp.OD / 2:
            fp.thk = fp.OD / 2
        fp.ID = fp.OD - 2 * fp.thk
        fp.Profile = str(fp.OD) + "x" + str(fp.thk)
        if fp.ID:
            fp.Shape = Part.makeCylinder(fp.OD / 2, fp.Height).cut(
                Part.makeCylinder(fp.ID / 2, fp.Height)
            )
        else:
            fp.Shape = Part.makeCylinder(fp.OD / 2, fp.Height)
        fp.Ports = [FreeCAD.Vector(), FreeCAD.Vector(0, 0, float(fp.Height))]
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)] 
        super(Pipe, self).execute(fp)  # perform common operations

class TerminalAdapter(pypeType):
    """Class for objet Ptype="TerminalAdapter"
      obj: the "App::FeaturePython" object
      PSize (string): nominal diameter
      OD (float): outside diameter
      L (float): Overall length
      SW (float): Support width
    """
    def __init__(self,obj,rating,DN="PCV-1/2",OD=21.3,L=33.2,SW=18.7, OD2=21.33):
        super(TerminalAdapter,self).__init__(obj)
        obj.Proxy = self
        obj.PType = "TerminalAdapter"
        obj.PRating =rating
        obj.PSize = DN
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "TerminalAdapter",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "L",
            "TerminalAdapter",
            QT_TRANSLATE_NOOP("App::Property", "Overall length"),
        ).L = L
        obj.addProperty(
            "App::PropertyLength",
            "SW",
            "TerminalAdapter",
            QT_TRANSLATE_NOOP("App::Property", "Support width"),
        ).SW = SW
        obj.addProperty(
            "App::PropertyLength",
            "OD2",
            "TerminalAdapter",
            QT_TRANSLATE_NOOP("App::Property", "Outside thread side"),
        ).OD2 = OD2
        self.execute(obj)
    def onChanged(self, fp,prop):
        pass
    def execute(self, fp):
        from math import tan
        polygonthickness = fp.SW/5
        threadthickness = fp.L-fp.SW
        cyl1=Part.makeCylinder(fp.OD/2,fp.SW-polygonthickness,FreeCAD.Vector(0,0,-polygonthickness),FreeCAD.Vector(0,0,-1))
        pwire=pCmd.makeRegularPolygon(6,(fp.OD*1.2)/2)
        polygonf=Part.Face(pwire)
        extrpoly=polygonf.extrude(FreeCAD.Vector(0,0,-polygonthickness))
        result=cyl1.fuse(extrpoly)
        cone2=Part.makeCone(fp.OD2/2,(fp.OD2/2-(tan(0.0312396483)*threadthickness)),threadthickness,FreeCAD.Vector(0,0,-polygonthickness),FreeCAD.Vector(0,0,1),360)
        result2=cone2.fuse(result)
        filletres=result2.makeFillet(2.5,[result2.Edges[16],result2.Edges[12],result2.Edges[9],result2.Edges[10],result2.Edges[14],result2.Edges[18]])
        cyl2=Part.makeCylinder((fp.OD/3),fp.SW,FreeCAD.Vector(0,0,-polygonthickness),FreeCAD.Vector(0,0,-1))
        cutres=filletres.cut(cyl2)
        cone3=Part.makeCone(fp.OD2/2*0.8,(fp.OD2/2-(tan(0.0312396483)*threadthickness))*0.8,threadthickness,FreeCAD.Vector(0,0,-polygonthickness),FreeCAD.Vector(0,0,1),360)
        cutres2=cutres.cut(cone3)
        fp.Shape = cutres2
        super(TerminalAdapter, self).execute(fp)  # perform common operations

class Elbow(pypeType):
    """Class for object PType="Elbow"
      Elbow(obj,[PSize="DN50",OD=60.3,thk=3,BA=90,BR=45.225])
      obj: the "App::FeaturePython" object
      PSize (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness
      BA (float): bend angle
      BR (float): bend radius"""

    def __init__(self, obj, rating="SCH-STD", DN="DN50", OD=60.3, thk=3, BA=90, BR=45.225):
        # initialize the parent class
        super(Elbow, self).__init__(obj)
        # define common properties
        obj.Proxy=self
        obj.PType = "Elbow"
        obj.PRating = rating
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "Elbow",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "Elbow",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        obj.addProperty(
            "App::PropertyLength",
            "ID",
            "Elbow",
            QT_TRANSLATE_NOOP("App::Property", "Inside diameter"),
        ).ID = obj.OD - 2 * obj.thk
        obj.addProperty(
            "App::PropertyAngle",
            "BendAngle",
            "Elbow",
            QT_TRANSLATE_NOOP("App::Property", "Bend Angle"),
        ).BendAngle = BA
        obj.addProperty(
            "App::PropertyLength",
            "BendRadius",
            "Elbow",
            QT_TRANSLATE_NOOP("App::Property", "Bend Radius"),
        ).BendRadius = BR
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "Elbow",
            QT_TRANSLATE_NOOP("App::Property", "Section dim."),
        ).Profile = str(obj.OD) + "x" + str(obj.thk)
        # obj.Ports=[FreeCAD.Vector(1,0,0),FreeCAD.Vector(0,1,0)]
        self.execute(obj)

    def onChanged(self, fp, prop):
        if prop == "ID" and fp.ID < fp.OD:
            fp.thk = (fp.OD - fp.ID) / 2

    def execute(self, fp):
        parent = fp.getParentGroup()
        if parent:
            try:
                edges = parent.Base.Shape.Edges
                i = parent.Curves.index(fp.Name)
                v1, v2 = [e.tangentAt(0) for e in edges[i : i + 2]]
                pCmd.placeTheElbow(fp, v1, v2)
            except Exception:
                #  FreeCAD.Console.PrintWarning(str(e) + "\n")
                pass
        if fp.BendAngle < 180:
            if fp.thk > fp.OD / 2:
                fp.thk = fp.OD / 2
            fp.ID = fp.OD - 2 * fp.thk
            fp.Profile = str(fp.OD) + "x" + str(fp.thk)
            CenterOfBend = FreeCAD.Vector(fp.BendRadius, fp.BendRadius, 0)
            ## make center-line ##
            R = Part.makeCircle(
                fp.BendRadius,
                CenterOfBend,
                FreeCAD.Vector(0, 0, 1),
                225 - float(fp.BendAngle) / 2,
                225 + float(fp.BendAngle) / 2,
            )
            ## move the cl so that Placement.Base is the center of elbow ##
            from math import pi, cos, sqrt

            d = fp.BendRadius * sqrt(2) - fp.BendRadius / cos(fp.BendAngle / 180 * pi / 2)
            P = FreeCAD.Vector(-d * cos(pi / 4), -d * cos(pi / 4), 0)
            R.translate(P)
            ## calculate Ports position ##
            fp.Ports = [R.valueAt(R.FirstParameter), R.valueAt(R.LastParameter)]
            fp.PortDirections = [
                R.tangentAt(R.FirstParameter) * -1,  #each port faces outward
                R.tangentAt(R.LastParameter)          
            ]
            ## make the shape of the elbow ##
            c = Part.makeCircle(fp.OD / 2, fp.Ports[0], R.tangentAt(R.FirstParameter) * -1)
            b = Part.makeSweepSurface(R, c)
            p1 = Part.Face(Part.Wire(c))
            p2 = Part.Face(
                Part.Wire(Part.makeCircle(fp.OD / 2, fp.Ports[1], R.tangentAt(R.LastParameter)))
            )
            try:
                sol = Part.Solid(Part.Shell([b.Faces[0], p1.Faces[0], p2.Faces[0]]))
                planeFaces = [f for f in sol.Faces if type(f.Surface) == Part.Plane]
                # elbow=sol.makeThickness(planeFaces,-fp.thk,1.e-3)
                # fp.Shape = elbow
                if fp.thk < fp.OD / 2:
                    fp.Shape = sol.makeThickness(planeFaces, -fp.thk, 1.0e-3)
                else:
                    fp.Shape = sol
                super(Elbow, self).execute(fp)  # perform common operations
            except Part.OCCError as occer:
                FreeCAD.Console.PrintWarning(str(occer) + "\n")


class DuctElbow:
    """Class for object PType="DuctElbow".
    Rectangular radius duct elbow driven by width, height, wall thickness,
    bend angle, and centerline bend radius.
    """

    def __init__(
        self,
        obj,
        rating="Rectangular",
        PSize="300x150",
        W=300,
        H=150,
        thk=0.8,
        BA=90,
        BR=450,
    ):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyString",
            "PType",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Type of duct feature"),
        ).PType = "DuctElbow"
        obj.addProperty(
            "App::PropertyString",
            "PRating",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Duct fitting family"),
        ).PRating = rating
        obj.addProperty(
            "App::PropertyString",
            "PSize",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Nominal duct size"),
        ).PSize = PSize
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Duct width"),
        ).W = W
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Duct height"),
        ).H = H
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        obj.addProperty(
            "App::PropertyAngle",
            "BendAngle",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Bend Angle"),
        ).BendAngle = BA
        obj.addProperty(
            "App::PropertyLength",
            "BendRadius",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Centerline bend radius"),
        ).BendRadius = BR
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "DuctElbow",
            QT_TRANSLATE_NOOP("App::Property", "Section dim."),
        ).Profile = str(obj.W) + "x" + str(obj.H) + "x" + str(obj.thk)
        obj.addProperty(
            "App::PropertyVectorList",
            "Ports",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Ports position relative to the origin of Shape"),
        )
        obj.addProperty(
            "App::PropertyVectorList",
            "PortDirections",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Port directions relative to the origin of Shape"),
        )
        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        from math import cos, radians, sin

        width = max(float(fp.W), 1.0)
        height = max(float(fp.H), 1.0)
        thk = max(min(float(fp.thk), width / 2 - 0.1, height / 2 - 0.1), 0.1)
        angle = max(min(float(fp.BendAngle), 170.0), 1.0)
        radius = max(float(fp.BendRadius), width / 2 + thk)
        fp.Profile = str(fp.W) + "x" + str(fp.H) + "x" + str(fp.thk)

        segments = max(6, int(angle / 7.5))
        outer_wires = []
        inner_wires = []
        for i in range(segments + 1):
            a = radians(angle * i / segments)
            center = FreeCAD.Vector(radius * sin(a), radius * (1 - cos(a)), 0)
            radial = FreeCAD.Vector(-sin(a), cos(a), 0)
            outer_wires.append(self._rect_wire(center, radial, vZ, width, height))
            inner_wires.append(self._rect_wire(center, radial, vZ, width - 2 * thk, height - 2 * thk))

        outer = Part.makeLoft(outer_wires, True, False, False)
        inner = Part.makeLoft(inner_wires, True, False, False)
        fp.Shape = outer.cut(inner)
        fp.Ports = [
            outer_wires[0].CenterOfMass,
            outer_wires[-1].CenterOfMass,
        ]
        fp.PortDirections = [
            FreeCAD.Vector(-1, 0, 0),
            FreeCAD.Vector(cos(radians(angle)), sin(radians(angle)), 0),
        ]

    def _rect_wire(self, center, xdir, ydir, width, height):
        x = xdir.normalize().multiply(width / 2)
        y = ydir.normalize().multiply(height / 2)
        pts = [
            center - x - y,
            center + x - y,
            center + x + y,
            center - x + y,
            center - x - y,
        ]
        return Part.Wire(Part.makePolygon(pts))


class Flange(pypeType):
    """Class for object PType="Flange"
    Flange(obj,[PSize="DN50",FlangeType="SO", D=160, d=60.3,df=132, f=14 t=15,n=4, trf=0, drf=0, twn=0, dwn=0, ODp=0])
      obj: the "App::FeaturePython" object
      PSize (string): nominal diameter
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
    """

    def __init__(
        self,
        obj,
        rating="DIN-PN16",
        DN="DN50",
        FlangeType="SO",
        D=160,
        d=60.3,
        df=132,
        f=14,
        t=15,
        n=4,
        trf=0,
        drf=0,
        twn=0,
        dwn=0,
        ODp=0,
        R=0,
        T1=0,
        B2=0,
        Y=0,
        FClass="",
    ):
        # initialize the parent class
        super(Flange, self).__init__(obj)
        # define common properties
        self.Type = "Flange"
        obj.Proxy = self
        obj.PType = "Flange"
        obj.PRating = rating
        obj.addProperty(
            "App::PropertyString",
            "FClass",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Flange pressure class"),
        ).FClass = FClass
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyString",
            "FlangeType",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Type of flange"),
        ).FlangeType = FlangeType
        obj.addProperty(
            "App::PropertyLength",
            "D",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Flange diameter"),
        ).D = D
        obj.addProperty(
            "App::PropertyLength",
            "d",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Bore diameter"),
        ).d = d
        obj.addProperty(
            "App::PropertyLength",
            "df",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Bolts distance"),
        ).df = df
        obj.addProperty(
            "App::PropertyLength",
            "f",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Bolts hole diameter"),
        ).f = f
        obj.addProperty(
            "App::PropertyLength",
            "t",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Thickness of flange"),
        ).t = t
        obj.addProperty(
            "App::PropertyInteger",
            "n",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Nr. of bolts"),
        ).n = n
        obj.addProperty(
            "App::PropertyLength",
            "trf",
            "Flange2",
            QT_TRANSLATE_NOOP("App::Property", "Thickness of raised face"),
        ).trf = trf
        obj.addProperty(
            "App::PropertyLength",
            "drf",
            "Flange2",
            QT_TRANSLATE_NOOP("App::Property", "Diameter of raised face"),
        ).drf = drf
        obj.addProperty(
            "App::PropertyLength",
            "twn",
            "Flange2",
            QT_TRANSLATE_NOOP("App::Property", "Length of welding neck"), #Thick part?
        ).twn = twn
        obj.addProperty(
            "App::PropertyLength",
            "dwn",
            "Flange2",
            QT_TRANSLATE_NOOP("App::Property", "Diameter of welding neck"),
        ).dwn = dwn
        obj.addProperty(
            "App::PropertyLength",
            "ODp",
            "Flange2",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter of pipe"),
        ).ODp = ODp
        obj.addProperty(
            "App::PropertyLength",
            "R",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Flange fillet radius"),
        ).R = R
        obj.addProperty(
            "App::PropertyLength",
            "T1",
            "Flange",
            QT_TRANSLATE_NOOP("App::Property", "Flange neck length"), #neck same OD as pipe?
        ).T1 = T1
        obj.addProperty(
            "App::PropertyLength",
            "B2",
            "Flange Socket welding",
            QT_TRANSLATE_NOOP("App::Property", "Socket diameter"),
        ).B2 = B2
        obj.addProperty(
            "App::PropertyLength",
            "Y",
            "Flange Socket welding",
            QT_TRANSLATE_NOOP("App::Property", "Socket depth"),
        ).Y = Y

    def onChanged(self, fp, prop):
        # FreeCAD.Console.PrintMessage(prop)
        if prop == "ODp":
            if fp.ODp > fp.D:
                FreeCAD.Console.PrintError(
                    "Raised edge diameter must be smaller than flange diameter"
                )
        return None

    def execute(self, fp):
       
        base = Part.Face(Part.Wire(Part.makeCircle(fp.D / 2)))
        if fp.d > 0:
            base = base.cut(Part.Face(Part.Wire(Part.makeCircle(fp.d / 2))))
        # Operation designed to make flange hole cylinders
        if fp.n > 0:
            hole = Part.Face(
                Part.Wire(
                    Part.makeCircle(
                        fp.f / 2,
                        FreeCAD.Vector(fp.df / 2, 0, 0),
                        FreeCAD.Vector(0, 0, 1),
                    )
                )
            )
            hole.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 360.0 / fp.n / 2)
            for i in list(range(fp.n)):
                base = base.cut(hole)
                hole.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 360.0 / fp.n)
        # creates flange thickness
        flange = base.extrude(FreeCAD.Vector(0, 0, fp.t))
        # Tessellation quality is a display setting, and ViewObject is None in
        # console mode. Setting it unguarded raised AttributeError mid-execute,
        # which recompute swallows -- so every Flange came back with a NULL
        # shape and no error, headless.
        if FreeCAD.GuiUp and fp.ViewObject is not None:
            fp.ViewObject.Deviation = 0.10
        if (
            fp.FlangeType == "SW"
            or fp.FlangeType == "WN"
            or fp.FlangeType == "LJ"
            or fp.FlangeType == "SO"
        ):
            # creates flange neck (corrected for raised face addition).
            # Only when it has real dimensions: ODp/T1 are documented OPTIONAL,
            # and building a zero-radius zero-height cylinder produced a
            # degenerate solid that fused into an invalid shape rather than
            # being skipped.
            if fp.ODp > 0 and fp.T1 > 0 and fp.ODp > fp.d:
                nn = Part.makeCylinder(fp.ODp / 2, fp.T1, vO, vZ).cut(
                    Part.makeCylinder(fp.d / 2, fp.T1, vO, vZ)
                )
                flange = flange.fuse(nn)
            if fp.trf > 0 and fp.drf < fp.D:
                rf = Part.makeCylinder(fp.drf / 2, fp.trf, vO, vZ * -1).cut(
                    Part.makeCylinder(fp.d / 2, fp.trf, vO, vZ * -1)
                )
                flange = flange.fuse(rf)

        if fp.FlangeType == "WN":
            try:  # Flange2:welding-neck
                
                if fp.dwn > 0 and fp.twn > 0 and fp.ODp > 0:
                    wn = Part.makeCone(
                        fp.dwn / 2, fp.ODp / 2, fp.twn, vZ * float(fp.t)
                    ).cut(Part.makeCylinder(fp.d / 2, fp.twn, vZ * float(fp.t)))
                    flange = flange.fuse(wn)
                    flange = flange.removeSplitter()
                    
                    flange = flange.makeFillet(fp.R, [flange.Edges[2]])
                    """ TODO Seems to be an issue with making weld neck chamfer after correcting flange thickness. 
                    Was previously edge 6 but now appears to not be consistent. Is there a better way to reliably find this edge rather than hard coding an edge number? 
                    Perhaps create the chamfer before merging with the rest of the flange object. Maybe it just doesn't need to be chamfered - none of the other components are"""
                    #flange = flange.makeChamfer((fp.ODp - fp.d) / 2 * 0.90, [flange.Edges[7]])
                    
                    
            except:
                pass
        elif fp.FlangeType == "LJ":
            edge = []
            flange = flange.removeSplitter()
            if fp.n == 4:
                edge = flange.Edges[19]
            if fp.n == 8:
                edge = flange.Edges[31]
            if fp.n == 12:
                edge = flange.Edges[43]
            if fp.n == 16:
                edge = flange.Edges[55]
            if fp.n == 20:
                edge = flange.Edges[67]
            flange = flange.makeFillet(fp.R, edge)
        elif fp.FlangeType == "SW":
            # creates flange neck
            if fp.B2 > 0:
                nn = flange.cut(
                    Part.makeCylinder(fp.B2 / 2, fp.Y, vZ * float(fp.T1 - fp.trf), vZ * -1)
                )
                flange = nn.removeSplitter()
        elif fp.FlangeType == "BL":
            # Blind flange: solid disc, no bore, no neck.
            # Raised face is a solid cylinder (no bore cutout).
            if fp.trf > 0 and fp.drf > 0 and fp.drf < fp.D:
                rf = Part.makeCylinder(fp.drf / 2, fp.trf, vO, vZ * -1)
                flange = flange.fuse(rf)
        fp.Shape = flange
        if fp.FlangeType == "WN":
            fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.trf)), FreeCAD.Vector(0, 0, float(fp.T1))] #weld neck flanges mate with pipe at T1, raised face is at 0,0,-RF thickness
        elif fp.FlangeType == "SW":
            fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.trf)), FreeCAD.Vector(0, 0, float(fp.T1)-float(fp.Y)-float(fp.trf))] #Socket weld flanges mate with pipe at Y - RF thickness, raised face is at 0,0,-RF thickness
        elif fp.FlangeType == "BL": #blind flange
            fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.trf)), FreeCAD.Vector(0, 0, float(fp.t))] #Blind flange: port 0 at raised face, fictitious port 1 at outer back face
        elif fp.FlangeType == "SO":
            fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.trf)), FreeCAD.Vector(0, 0, float(fp.trf))] #slip on flange: port 0 at raised face, port 1 mated to pipe back RF thickness from edge of flange hub (2 * trf back from raised face edge)
        else: #lap joint
            fp.Ports = [FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, float(fp.trf))] #lap joint flanges should be mated with pipe at 0,0,0. Raised face will be at 0,0,-RF thickness
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)] #Flange face is toward -Z direction, flange weld end faces in +Z direction
        super(Flange, self).execute(fp)  # perform common operations

    #!TODO:this method generate a PartDesign object with sketch nest, pending feature compatibility

    # def execute(self,fp):
    #     obj=FreeCAD.activeDocument().addObject('u','Flange')
    #     sketch=obj.newObject('Sketcher::SketchObject','Sketch')
    #     sketch.AttachmentSupport=(FreeCAD.activeDocument().getObject('YZ_Plane'),[''])
    #     sketch.MapMode='FlatFace'
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(-26.396620,19.420528,0),FreeCAD.Vector(37.200497,20.283836,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,0,2,fp.d/2))
    #     sketch.renameConstraint(0, u'InnerDiameter')
    #     sketch.addConstraint(Sketcher.Constraint('Symmetric',0,1,0,2,-2))
    #     sketch.addConstraint(Sketcher.Constraint('DistanceX',0,1,0,2,70))
    #     sketch.renameConstraint(2, u'OverallThickness')
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(37.200497,19.420528,0),FreeCAD.Vector(37.200497,24.312616,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('Coincident',0,2,1,1))
    #     sketch.addConstraint(Sketcher.Constraint('Vertical',1))
    #     sketch.addGeometry(Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(34.202893,24.312616,0),FreeCAD.Vector(0,0,1),2.997604),0.000000,1.287001),False)
    #     sketch.addConstraint(Sketcher.Constraint('Tangent',1,2,2,1))
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(35.042226,27.190315,0),FreeCAD.Vector(6.698068,35.457398,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('Tangent',2,2,3,1))
    #     sketch.addGeometry(Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(7.314065,37.569377,0),FreeCAD.Vector(0,0,1),2.199979),-3.132797,-1.854592),False)
    #     sketch.addConstraint(Sketcher.Constraint('Equal',2,4))
    #     sketch.addConstraint(Sketcher.Constraint('Tangent',3,2,4,2))
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(5.114171,37.550027,0),FreeCAD.Vector(4.854102,67.117138,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('Tangent',4,1,5,1))
    #     sketch.addGeometry(Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(1.818155,67.090434,0),FreeCAD.Vector(0,0,1),3.036064),0.008796,1.579592),False)
    #     sketch.addConstraint(Sketcher.Constraint('Equal',6,4))
    #     sketch.addConstraint(Sketcher.Constraint('Radius',4,3))
    #     sketch.addConstraint(Sketcher.Constraint('Tangent',5,2,6,1))
    #     sketch.addConstraint(Sketcher.Constraint('Vertical',5))
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(1.791451,70.126381,0),FreeCAD.Vector(-23.109907,69.907350,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('Horizontal',7))
    #     sketch.addConstraint(Sketcher.Constraint('Tangent',6,2,7,1))
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(-23.109907,69.907350,0),FreeCAD.Vector(-22.849606,40.313959,0)),False)
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(-22.849606,40.313959,0),FreeCAD.Vector(-27.278782,40.223301,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('Coincident',7,2,8,1))
    #     sketch.addConstraint(Sketcher.Constraint('Vertical',8))
    #     sketch.addConstraint(Sketcher.Constraint('Coincident',8,2,9,1))
    #     sketch.addConstraint(Sketcher.Constraint('DistanceY',8,1,8,2,-10))
    #     sketch.addConstraint(Sketcher.Constraint('Horizontal',9))
    #     sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(-27.278782,40.313959,0),FreeCAD.Vector(-26.396620,19.420528,0)),False)
    #     sketch.addConstraint(Sketcher.Constraint('Coincident',9,2,10,1))
    #     sketch.addConstraint(Sketcher.Constraint('Coincident',10,2,0,1))
    #     sketch.addConstraint(Sketcher.Constraint('Vertical',10))
    #     sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,7,2,fp.D/2))
    #     sketch.renameConstraint(24, u'OuterDiameter')
    #     sketch.addConstraint(Sketcher.Constraint('DistanceX',9,2,5,2,fp.t))
    #     sketch.renameConstraint(25, u'FlangeThickness')
    #     sketch.Visibility=False
    #     sketch.recompute()
    #     revolution=obj.newObject('PartDesign::Revolution','Revolution')
    #     revolution.Profile=(sketch, [''])
    #     revolution.ReferenceAxis = (sketch, ['H_Axis'])
    #     fp.Placement=fp.Placement
    #     fp.Shape= obj.Shape

class SocketEll(pypeType):
    """  
    SocketEll(obj, [PSize="DN25", OD=33.4, BendAngle=90,A=35.0,C=5.0,D=25.4,E=22.0,G=5.455,Conn="SW"])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      OD (float): Connecting pipe outside diameter
      BendAngle (float): Bend angle
      A (float): Dimension from fitting center to outer edge of ell
      C (float): Wall thickness in socket
      D (float): Bore internal diameter
      E (float): Dimension from fitting center to base of socket
      G (float): Inner body wall thickness
      Conn (string): Connection type (SW=Socket Weld, TH=Threaded)

    """
    def __init__(self, obj, rating="3000lb", PSize="DN25", OD=33.4, BendAngle=90, A=35.0, C=5.0, D=25.4, E=22.0, G=5.455, Conn="SW"):
        # initialize the parent class
        super(SocketEll, self).__init__(obj)
        # define common properties
        obj.Proxy = self
        obj.PType = "SocketEll"
        obj.PRating = rating
        obj.PSize = PSize
        # define specific properties
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Pipe OD"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyAngle",
            "BendAngle",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Bend Angle"),
        ).BendAngle = BendAngle
        obj.addProperty(
            "App::PropertyLength",
            "A",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Center to outer edge"),
        ).A = A
        obj.addProperty(
            "App::PropertyLength",
            "C",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness in socket"),
        ).C = C
        obj.addProperty(
            "App::PropertyLength",
            "D",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Bore internal diameter"),
        ).D = D
        obj.addProperty(
            "App::PropertyLength",
            "E",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Center to base of socket"),
        ).E = E
        obj.addProperty(
            "App::PropertyLength",
            "G",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Inner body wall thickness"),
        ).G = G
        obj.addProperty(
            "App::PropertyString",
            "Conn",
            "SocketEll",
            QT_TRANSLATE_NOOP("App::Property", "Connection type (SW=Socket Weld, TH=Threaded)"),
        ).Conn = Conn
        self.execute(obj)

    def onChanged(self, fp, prop):
        return None
    
    def execute(self, fp):
        from math import pi, cos, sin
        bendRadius = fp.D/2+fp.G

        #make centerline quarter sphere and rotate 180 degrees, so ports will appear in +x and +y directions (for 90 degree ell) consistent with butt weld ell
        bendOD = Part.makeSphere(bendRadius, FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), -90,90,90) 
        bendOD.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0),FreeCAD.Rotation(FreeCAD.Vector(0,0,1),180)).multiply(bendOD.Placement)

        #Create sections between center and socket
        body1 = Part.makeCylinder(bendRadius, fp.E, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0,0)) 
        body2 = Part.makeCylinder(bendRadius, fp.E, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(-cos(fp.BendAngle*pi/180), sin(fp.BendAngle*pi/180), 0))
        
        #Create outer socket sections
        socket1 = Part.makeCylinder(fp.OD/2+fp.C, fp.A-(fp.E-fp.C), FreeCAD.Vector(fp.E-fp.C, 0, 0), FreeCAD.Vector(1, 0,0)) 
        socket2 = Part.makeCylinder(fp.OD/2+fp.C, fp.A-(fp.E-fp.C), FreeCAD.Vector(-cos(fp.BendAngle*pi/180)*(fp.E-fp.C), sin(fp.BendAngle*pi/180)*(fp.E-fp.C), 0),FreeCAD.Vector(-cos(fp.BendAngle*pi/180), sin(fp.BendAngle*pi/180), 0)) 

        #fuse to create outer surface
        base = bendOD.fuse(body1)
        base = base.fuse(body2)
        base = base.fuse(socket1)
        base = base.fuse(socket2)

        #create inner cutout, repeating same steps as above
        bendRadius = fp.D/2

        bendOD = Part.makeSphere(bendRadius, FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), -90,90,90) 
        bendOD.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0),FreeCAD.Rotation(FreeCAD.Vector(0,0,1),180)).multiply(bendOD.Placement)

        body1 = Part.makeCylinder(bendRadius, fp.E, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0,0)) 
        body2 = Part.makeCylinder(bendRadius, fp.E, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(-cos(fp.BendAngle*pi/180), sin(fp.BendAngle*pi/180), 0)) 

        socket1 = Part.makeCylinder(fp.OD/2, fp.A-(fp.E-fp.C), FreeCAD.Vector(fp.E, 0, 0), FreeCAD.Vector(1, 0,0)) 
        socket2 = Part.makeCylinder(fp.OD/2, fp.A-(fp.E-fp.C), FreeCAD.Vector(fp.E*(-cos(fp.BendAngle*pi/180)), fp.E*(sin(fp.BendAngle*pi/180)), 0), FreeCAD.Vector(-cos(fp.BendAngle*pi/180), sin(fp.BendAngle*pi/180), 0)) 
       
        cutout = bendOD.fuse(body1)
        cutout = cutout.fuse(body2)
        cutout = cutout.fuse(socket1)
        cutout = cutout.fuse(socket2)

        #cut out inner bore; removeSplitter merges the body/socket seams where their radii match
        base = base.cut(cutout).removeSplitter()

        fp.Shape = base   

        fp.Ports = [ FreeCAD.Vector(fp.E,0,  0), FreeCAD.Vector(-fp.E * cos(fp.BendAngle*pi/180), fp.E* sin(fp.BendAngle*pi/180), 0)]
        fp.PortDirections = [FreeCAD.Vector(1,0,0), 
                      FreeCAD.Vector(-cos(fp.BendAngle*pi/180), sin(fp.BendAngle*pi/180), 0)]
        super(SocketEll, self).execute(fp)  # perform common operations

class Tee(pypeType):
    """  
    Tee(obj, [PSize="DN150", OD=168.27, OD2=114.3,thk=7.11,thk2=6.02,C=178,M=156,DN2=""])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter (run)
      OD (float): Run outside diameter
      OD2 (float): Branch outside diameter. If None, assumes same diameter as run
      thk (float): Run shell thickness
      thk2 (float): Branch shell thickness. If None, assumes same thickness as run
      C (float): Length from branch centerline to run edge
      M (float): Length from run centerline to branch edge. If None, assumes same length as run
      DN2 (string): nominal diameter of branch end; stored as PSizeBranch property
    """
    def __init__(self, obj, rating="SCH-STD", DN="DN150", OD=168.27, OD2=168.27,thk=7.11,thk2=7.11,C=178.0,M=178.0,DN2=""):
         # initialize the parent class
        super(Tee, self).__init__(obj)
         # define common properties
        obj.Proxy = self
        obj.PType = "Tee"
        obj.PRating = rating
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyString",
            "PSizeBranch",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Nominal diameter of branch end"),
        ).PSizeBranch = DN2
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Run diameter"),
        ).OD
        obj.addProperty(
            "App::PropertyLength",
            "OD2",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Branch diameter"),
        ).OD2
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Run Wall thickness"),
        ).thk
        obj.addProperty(
            "App::PropertyLength",
            "thk2",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Branch Wall thickness"),
        ).thk2
        obj.addProperty(
            "App::PropertyLength",
            "C",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Run half length"),
        ).C
        obj.addProperty(
            "App::PropertyLength",
            "M",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Branch length"),
        ).M
        obj.addProperty(
            "App::PropertyLength",
            "offset",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Straight tee offset length"),
        ).offset
        #If branch diameter is equal to run, set branch OD, thickness, and length to be equal to branch's
        if not thk2:
            obj.thk2 = thk
        else:
            obj.thk2 = thk2

        if not OD2:
            obj.OD2 = OD
        else:
            obj.OD2 = OD2

        if not M:
            obj.M = C
        else:
            obj.M = M
        obj.OD = OD
        obj.thk = thk
        obj.C = C

        obj.offset = 1.0 #mm offset for straight tee 
        
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Run and Branch Size"),
        ).Profile = str(obj.OD) + "x" + str(obj.OD2)
        self.execute(obj)

    def onChanged(self, fp, prop):
        return None
    
    def execute(self, fp):
        
        fp.Profile = str(fp.OD) + "x" + str(fp.OD2)        
        #make basic tee shape first, then add fillet (for reducing tee) or quarter torus (for straight tee)
        Base = Part.makeCylinder(fp.OD/2, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), ) #run tube
        BranchTube = Part.makeCylinder(fp.OD2/2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
        RunHole = Part.makeCylinder(fp.OD/2 - fp.thk, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), )
        BranchHole = Part.makeCylinder(fp.OD2/2 - fp.thk2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
        Base = Base.fuse(BranchTube)



        if fp.PSize == fp.PSizeBranch:
            #model as quarter torus centered 1 mm off of OD, with a diameter of OD, mirrored across XY plane. Can add internal torus at some point perhaps if you feel like it.
            #1 mm offset

            quarterTorus = Part.makeTorus((fp.OD + fp.offset)/2, fp.OD/2, FreeCAD.Vector(0,(fp.OD+fp.offset)/2,-(fp.OD+fp.offset)/2), FreeCAD.Vector(1,0,0),-180,180,90)
            box = Part.makeBox(fp.OD, (fp.OD+fp.offset)/2, (fp.OD+fp.offset)/2,FreeCAD.Vector(-fp.OD/2,0,0), FreeCAD.Vector(0,0,1))
            cutcylinder = Part.makeCylinder((fp.OD+fp.offset)/2, fp.OD, FreeCAD.Vector(-fp.OD/2,(fp.OD+fp.offset)/2,(fp.OD+fp.offset)/2),FreeCAD.Vector(1,0,0))
            box = box.cut(cutcylinder)
            quarterTorus = quarterTorus.fuse(box)
            mirror_img = quarterTorus.mirror(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1))
            centerTee = quarterTorus.fuse(mirror_img)
            Base = Part.makeCylinder(fp.OD/2, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), ) #run tube
            BranchTube = Part.makeCylinder(fp.OD2/2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
            RunHole = Part.makeCylinder(fp.OD/2 - fp.thk, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), )
            BranchHole = Part.makeCylinder(fp.OD2/2 - fp.thk2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
            Base = Base.fuse(BranchTube)
            Base = Base.fuse(centerTee)
            Base = Base.cut(RunHole)
            Base = Base.cut(BranchHole)
            Base = Base.removeSplitter()
        else:
            Base = Part.makeCylinder(fp.OD/2, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), ) #run tube
            BranchTube = Part.makeCylinder(fp.OD2/2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
            RunHole = Part.makeCylinder(fp.OD/2 - fp.thk, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), )
            BranchHole = Part.makeCylinder(fp.OD2/2 - fp.thk2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
            Base = Base.fuse(BranchTube)
            Base = Base.cut(RunHole)
            Base = Base.cut(BranchHole)
            Base = Base.removeSplitter()
        
            
            # Identify the intersection edges geometrically:
            # They are the edges shared between the run cylinder surface and the
            # branch cylinder surface -- i.e. edges whose midpoint lies on BOTH
            # the run OD surface (distance from Z-axis == OD/2) and the branch OD
            # surface (distance from Y-axis == OD2/2), within a small tolerance.
            
            import math

            tol = 0.5  # mm -- generous enough for floating-point geometry

            fillet_edges = []
            for edge in Base.Edges:
                try:
                    mid = edge.valueAt(
                        (edge.FirstParameter + edge.LastParameter) / 2.0
                    )
                    # Distance from the Z axis (run cylinder axis)
                    dist_run    = math.sqrt(mid.x ** 2 + mid.y ** 2)
                    # Distance from the Y axis (branch cylinder axis)
                    dist_branch = math.sqrt(mid.x ** 2 + mid.z ** 2)

                    on_run_od    = abs(dist_run    - float(fp.OD)  / 2) < tol
                    on_branch_od = abs(dist_branch - float(fp.OD2) / 2) < tol

                    if on_run_od and on_branch_od:
                        fillet_edges.append(edge)
                except Exception:
                    continue
            
            # Apply fillet only when valid intersection edges were found
            if fillet_edges:
                fillet_r = fp.M/2-fp.OD/4
                try:
                    Base = Base.makeFillet(fillet_r, fillet_edges)
                except Exception as e:
                    # Fillet failed -- fall back to unfilleted shape rather than
                    # crashing the whole recompute
                    # float() because fillet_r is a Base.Quantity, which has no
                    # numeric __format__ -- the fallback that exists to avoid
                    # crashing the recompute was itself raising TypeError and
                    # taking the Tee down with it.
                    FreeCAD.Console.PrintWarning(
                        "Tee fillet failed (r={:.2f}mm): {} -- using unfilleted shape\n"
                        .format(float(fillet_r), e)
                    )

        fp.Shape = Base
        fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.C)), FreeCAD.Vector(0, 0, float(fp.C)), FreeCAD.Vector(0, float(fp.M), 0)]
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1), 
                      FreeCAD.Vector(0, 0, 1), 
                      FreeCAD.Vector(0, 1, 0)]
        super(Tee, self).execute(fp)  # perform common operations

class SocketTee(pypeType):
    """
    SocketTee(obj, [PSize="DN25", PSizeBranch="DN25", OD=33.4, OD2=33.4,
                    A=35.0, C=5.0, D=25.4, E=22.0, G=4.55, Conn="SW"])
      obj           : the "App::FeaturePython" object
      PSize         (string): nominal diameter of the run
      PSizeBranch   (string): nominal diameter of the branch
      OD            (float):  run pipe outside diameter
      OD2           (float):  branch pipe outside diameter
      A             (float):  dimension from fitting centre to outer face of socket
      C             (float):  socket boss wall thickness
      D             (float):  bore internal diameter (run, at centre)
      E             (float):  dimension from fitting centre to base of socket
      G             (float):  inner body wall thickness
      Conn          (string): connection type (SW=Socket Weld, TH=Threaded)

    Local coordinate system
    ───────────────────────
      Run axis   : Z  — ports 0 (-Z end) and 1 (+Z end)
      Branch axis: Y  — port 2 (+Y end)
      Origin     : centre of the tee body
    """

    def __init__(self, obj, rating="3000lb",
                 PSize="DN25", PSizeBranch="DN25",
                 OD=33.4, OD2=33.4,
                 A=35.0, C=5.0, D=25.4, E=22.0, G=4.55,
                 Conn="SW"):
        # ── parent class ─────────────────────────────────────────────────────
        super(SocketTee, self).__init__(obj)

        # ── common pype properties ────────────────────────────────────────────
        obj.Proxy   = self
        obj.PType   = "SocketTee"
        obj.PRating = rating
        obj.PSize   = PSize

        # ── specific properties ───────────────────────────────────────────────
        obj.addProperty(
            "App::PropertyString",
            "PSizeBranch",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Nominal diameter of branch"),
        ).PSizeBranch = PSizeBranch

        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Run pipe OD"),
        ).OD = OD

        obj.addProperty(
            "App::PropertyLength",
            "OD2",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Branch pipe OD"),
        ).OD2 = OD2

        obj.addProperty(
            "App::PropertyLength",
            "A",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Centre to outer face of socket"),
        ).A = A

        obj.addProperty(
            "App::PropertyLength",
            "C",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Socket boss wall thickness"),
        ).C = C

        obj.addProperty(
            "App::PropertyLength",
            "D",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Bore internal diameter"),
        ).D = D

        obj.addProperty(
            "App::PropertyLength",
            "E",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Centre to base of socket"),
        ).E = E

        obj.addProperty(
            "App::PropertyLength",
            "G",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property", "Inner body wall thickness"),
        ).G = G

        obj.addProperty(
            "App::PropertyString",
            "Conn",
            "SocketTee",
            QT_TRANSLATE_NOOP("App::Property",
                              "Connection type (SW=Socket Weld, TH=Threaded)"),
        ).Conn = Conn

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        # ── outer body ───────────────────────────────────────────────────────
        centerBodyRadius = fp.D / 2 + fp.G

        # Run body: cylinder spanning -E to +E along Z
        base = Part.makeCylinder(
            centerBodyRadius, float(fp.E) * 2,
            FreeCAD.Vector(0, 0, -float(fp.E)), FreeCAD.Vector(0, 0, 1))

        # Branch body: cylinder from centre outward along +Y
        branchTube = Part.makeCylinder(
            centerBodyRadius, float(fp.E),
            FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))

        # Socket OD
        socket1 = Part.makeCylinder(
            float(fp.OD) / 2 + float(fp.C), float(fp.A) - (float(fp.E) - float(fp.C)),
            FreeCAD.Vector(0, 0,  float(fp.E) - float(fp.C)), FreeCAD.Vector(0, 0,  1))
        socket2 = Part.makeCylinder(
            float(fp.OD) / 2 + float(fp.C), float(fp.A) - (float(fp.E) - float(fp.C)),
            FreeCAD.Vector(0, 0, -(float(fp.E) - float(fp.C))), FreeCAD.Vector(0, 0, -1))
        socket3 = Part.makeCylinder(
            float(fp.OD) / 2 + float(fp.C), float(fp.A) - (float(fp.E) - float(fp.C)),
            FreeCAD.Vector(0, float(fp.E) - float(fp.C), 0), FreeCAD.Vector(0, 1, 0)) #branch

        base = base.fuse(branchTube)
        base = base.fuse(socket1)
        base = base.fuse(socket2)
        base = base.fuse(socket3)

        # ── inner bore cutout ────────────────────────────────────────────────
        boreRadius = fp.D / 2

        cutout = Part.makeCylinder(
            boreRadius, float(fp.E) * 2,
            FreeCAD.Vector(0, 0, -float(fp.E)), FreeCAD.Vector(0, 0, 1))
        #For reducing tee, branch bore radius is OD of branch pipe minus 3 mm for socket lip. Worthwhile to pass this or just keep hard coded?
        if fp.OD == fp.OD2:
            branchBore = Part.makeCylinder(
                boreRadius, float(fp.E),
                FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))

        else:
            branchBore = Part.makeCylinder(
                float(fp.OD2)/2-3.0, float(fp.E),
                FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))

        # Socket bores — run ports use OD/2, branch port uses OD2/2
        cut1 = Part.makeCylinder(
            float(fp.OD) / 2, float(fp.A) - (float(fp.E) - float(fp.C)),
            FreeCAD.Vector(0, 0,  float(fp.E)), FreeCAD.Vector(0, 0,  1))
        cut2 = Part.makeCylinder(
            float(fp.OD) / 2, float(fp.A) - (float(fp.E) - float(fp.C)),
            FreeCAD.Vector(0, 0, -float(fp.E)), FreeCAD.Vector(0, 0, -1))
        cut3 = Part.makeCylinder(
            float(fp.OD2) / 2, float(fp.A) - (float(fp.E) - float(fp.C)),
            FreeCAD.Vector(0, float(fp.E), 0), FreeCAD.Vector(0, 1, 0))

        cutout = cutout.fuse(branchBore)
        cutout = cutout.fuse(cut1)
        cutout = cutout.fuse(cut2)
        cutout = cutout.fuse(cut3)

        # removeSplitter merges the body/socket seams where their radii match
        base = base.cut(cutout).removeSplitter()
        fp.Shape = base

        # ── ports ─────────────────────────────────────────────────────────────
        # Port 0: run end at -Z  (primary insertion port, outward direction -Z)
        # Port 1: run end at +Z  (outward direction +Z)
        # Port 2: branch at +Y   (outward direction +Y)
        fp.Ports = [
            FreeCAD.Vector(0, 0, -float(fp.E)),
            FreeCAD.Vector(0, 0,  float(fp.E)),
            FreeCAD.Vector(0,  float(fp.E), 0),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
            FreeCAD.Vector(0,  1,  0),
        ]
        super(SocketTee, self).execute(fp)  # perform common operations

    
class Reduct(pypeType):
    """Class for object PType="Reduct"
    Reduct(obj,[PSize="DN50",OD=60.3, OD2= 48.3, thk=3, thk2=None, H=None, conc=True, DN2=""])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter (major end)
      OD (float): major outside diameter
      OD2 (float): minor outside diameter
      thk (float): major shell thickness
      thk2 (float): minor shell thickness
      H (float): length of reduction
      conc (bool): True for a concentric reduction, False for eccentric
      DN2 (string): nominal diameter (minor end); read from PSize2 column in CSV
    If thk2 is None or 0, the same thickness is used at both ends.
    If H is None or 0, the length of the reduction is calculated as 3x(OD-OD2).
    """

    def __init__(self, obj, rating="SCH-STD", DN="DN50", OD=60.3, OD2=48.3, thk=3, thk2=None, H=None, conc=True, DN2=""):
        # initialize the parent class
        super(Reduct, self).__init__(obj)
        # define common properties
        obj.Proxy = self
        obj.PType = "Reduct"
        obj.PRating = rating
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyString",
            "PSize2",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Nominal diameter (minor end)"),
        ).PSize2 = DN2
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Major diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "OD2",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Minor diameter"),
        ).OD2 = OD2
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        obj.addProperty(
            "App::PropertyLength",
            "thk2",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        )
        if not thk2:
            obj.thk2 = thk
        else:
            obj.thk2 = thk2
        obj.addProperty(
            "App::PropertyBool",
            "calcH",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Make the length variable"),
        )
        obj.addProperty(
            "App::PropertyLength",
            "Height",
            "Reduction",
            QT_TRANSLATE_NOOP("App::Property", "Length of reduction"),
        )
        if not H:
            obj.calcH = True
            obj.Height = 3 * (obj.OD - obj.OD2)
        else:
            obj.calcH = False
            obj.Height = float(H)
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Section dim."),
        ).Profile = str(obj.OD) + "x" + str(obj.OD2)
        obj.addProperty(
            "App::PropertyBool",
            "conc",
            "Reduct",
            QT_TRANSLATE_NOOP("App::Property", "Concentric or Eccentric"),
        ).conc = conc

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        if fp.OD > fp.OD2:
            if fp.calcH or fp.Height == 0:
                fp.Height = 3 * (fp.OD - fp.OD2)
            fp.Profile = str(fp.OD) + "x" + str(fp.OD2)
            if fp.conc:
                sol = Part.makeCone(fp.OD / 2, fp.OD2 / 2, fp.Height)
                if fp.thk < fp.OD / 2 and fp.thk2 < fp.OD2 / 2:
                    fp.Shape = sol.cut(
                        Part.makeCone(fp.OD / 2 - fp.thk, fp.OD2 / 2 - fp.thk2, fp.Height)
                    )
                else:
                    fp.Shape = sol
                fp.Ports = [FreeCAD.Vector(), FreeCAD.Vector(0, 0, float(fp.Height))]

            else:
                C = Part.makeCircle(fp.OD / 2, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
                c = Part.makeCircle(fp.OD2 / 2, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
                c.translate(FreeCAD.Vector((fp.OD - fp.OD2) / 2, 0, fp.Height))
                sol = Part.makeLoft([c, C], True)
                if fp.thk < fp.OD / 2 and fp.thk2 < fp.OD2 / 2:
                    C = Part.makeCircle(
                        fp.OD / 2 - fp.thk,
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(0, 0, 1),
                    )
                    c = Part.makeCircle(
                        fp.OD2 / 2 - fp.thk2,
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(0, 0, 1),
                    )
                    c.translate(FreeCAD.Vector((fp.OD - fp.OD2) / 2, 0, fp.Height))
                    fp.Shape = sol.cut(Part.makeLoft([c, C], True))
                else:
                    fp.Shape = sol
                fp.Ports = [
                    FreeCAD.Vector(),
                    FreeCAD.Vector((fp.OD - fp.OD2) / 2, 0, float(fp.Height)),
                ]
            fp.PortDirections = [FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)] #in either case, ports face +Z and -Z
        super(Reduct, self).execute(fp)  # perform common operations


class DuctReduction:
    """Class for object PType="DuctReduction".

    Rectangular duct transition/reducer driven by inlet/outlet width and
    height, wall thickness, transition length, and optional outlet offsets.
    """

    def __init__(
        self,
        obj,
        rating="Rectangular",
        PSize="600x300-400x200",
        W1=600,
        H1=300,
        W2=400,
        H2=200,
        thk=1.0,
        L=386,
        OffsetX=0,
        OffsetY=0,
    ):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyString",
            "PType",
            "DuctReduction",
            QT_TRANSLATE_NOOP("App::Property", "Type of duct feature"),
        ).PType = "DuctReduction"
        obj.addProperty(
            "App::PropertyString",
            "PRating",
            "DuctReduction",
            QT_TRANSLATE_NOOP("App::Property", "Duct fitting family"),
        ).PRating = rating
        obj.addProperty(
            "App::PropertyString",
            "PSize",
            "DuctReduction",
            QT_TRANSLATE_NOOP("App::Property", "Nominal duct transition size"),
        ).PSize = PSize
        for prop, value, text in [
            ("W1", W1, "Inlet width"),
            ("H1", H1, "Inlet height"),
            ("W2", W2, "Outlet width"),
            ("H2", H2, "Outlet height"),
            ("thk", thk, "Wall thickness"),
            ("Height", L, "Transition length"),
            ("OffsetX", OffsetX, "Outlet horizontal offset"),
            ("OffsetY", OffsetY, "Outlet vertical offset"),
        ]:
            obj.addProperty(
                "App::PropertyLength",
                prop,
                "DuctReduction",
                QT_TRANSLATE_NOOP("App::Property", text),
            )
            setattr(obj, prop, value)
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "DuctReduction",
            QT_TRANSLATE_NOOP("App::Property", "Section dim."),
        ).Profile = str(obj.W1) + "x" + str(obj.H1) + ">" + str(obj.W2) + "x" + str(obj.H2)
        obj.addProperty(
            "App::PropertyVectorList",
            "Ports",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Ports position relative to the origin of Shape"),
        )
        obj.addProperty(
            "App::PropertyVectorList",
            "PortDirections",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Port directions relative to the origin of Shape"),
        )
        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        w1 = max(float(fp.W1), 1.0)
        h1 = max(float(fp.H1), 1.0)
        w2 = max(float(fp.W2), 1.0)
        h2 = max(float(fp.H2), 1.0)
        thk = max(min(float(fp.thk), w1 / 2 - 0.1, h1 / 2 - 0.1, w2 / 2 - 0.1, h2 / 2 - 0.1), 0.1)
        length = max(float(fp.Height), 1.0)
        offset = FreeCAD.Vector(float(fp.OffsetX), float(fp.OffsetY), length)
        fp.Profile = str(fp.W1) + "x" + str(fp.H1) + ">" + str(fp.W2) + "x" + str(fp.H2)

        inlet = self._rect_wire(vO, vX, vY, w1, h1)
        outlet = self._rect_wire(offset, vX, vY, w2, h2)
        inner_inlet = self._rect_wire(vO, vX, vY, w1 - 2 * thk, h1 - 2 * thk)
        inner_outlet = self._rect_wire(offset, vX, vY, w2 - 2 * thk, h2 - 2 * thk)

        outer = Part.makeLoft([inlet, outlet], True, False, False)
        inner = Part.makeLoft([inner_inlet, inner_outlet], True, False, False)
        fp.Shape = outer.cut(inner)
        fp.Ports = [vO, offset]
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1), FreeCAD.Vector(0, 0, 1)]

    def _rect_wire(self, center, xdir, ydir, width, height):
        x = xdir.normalize().multiply(width / 2)
        y = ydir.normalize().multiply(height / 2)
        pts = [
            center - x - y,
            center + x - y,
            center + x + y,
            center - x + y,
            center - x - y,
        ]
        return Part.Wire(Part.makePolygon(pts))


class Cap(pypeType):
    """Class for object PType="Cap"
    Cap(obj,[PSize="DN50",OD=60.3,thk=3])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness"""

    def __init__(self, obj, rating="SCH-STD", DN="DN50", OD=60.3, thk=3):
        # initialize the parent class
        super(Cap, self).__init__(obj)
        # define common properties
        obj.PType = "Cap"
        obj.Proxy = self
        obj.PRating = rating
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "Cap",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "Cap",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        obj.addProperty(
            "App::PropertyLength",
            "ID",
            "Cap",
            QT_TRANSLATE_NOOP("App::Property", "Inside diameter"),
        ).ID = obj.OD - 2 * obj.thk
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "Cap",
            QT_TRANSLATE_NOOP("App::Property", "Section dim."),
        ).Profile = str(obj.OD) + "x" + str(obj.thk)

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        if fp.thk > fp.OD / 2:
            fp.thk = fp.OD / 2.1
        fp.ID = fp.OD - 2 * fp.thk
        fp.Profile = str(fp.OD) + "x" + str(fp.thk)
        D = float(fp.OD)
        s = float(fp.thk)
        sfera = Part.makeSphere(0.8 * D, FreeCAD.Vector(0, 0, -(0.55 * D - 6 * s)))
        cilindro = Part.makeCylinder(
            D / 2,
            D * 1.7,
            FreeCAD.Vector(0, 0, -(0.55 * D - 6 * s + 1)),
            FreeCAD.Vector(0, 0, 1),
        )
        common = sfera.common(cilindro)
        fil = common.makeFillet(D / 6.5, common.Edges)
        cut = fil.cut(
            Part.makeCylinder(D * 1.1, D * 2, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, -1))
        )
        cap = cut.makeThickness([f for f in cut.Faces if type(f.Surface) == Part.Plane], -s, 1.0e-3)
        fp.Shape = cap
        fp.Ports = [FreeCAD.Vector()]
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1)]
        super(Cap, self).execute(fp)  # perform common operations

class PypeLine2(pypeType):
    """Class for object PType="PypeLine2"
    This object represent a collection of objects "PType" that are updated with the
    methods defined in the Python class.
    At present time it creates, with the method obj.Proxy.update(,obj,[edges]), pipes and curves over
    the given edges and collect them in a group named according the object's .Label.
    PypeLine2 features also the optional attribute ".Base":
    - Base can be a Wire or a Sketch or any object which has edges in its Shape.
    - Running "obj.Proxy.update(obj)", without any [edges], the class attempts to render the pypeline
    (Pipe and Elbow objects) on the "obj.Base" edges: for well defined geometries
    and open paths, this usually leads to acceptable results.
    - Running "obj.Proxy.purge(obj)" deletes from the model all Pipes and Elbows
    that belongs to the pype-line.
    - It's possible to add other objects afterwards (such as Flange, Reduct...)
    using the relevant insertion dialogs but remember that these won't be updated
    when the .Base is changed and won't be deleted if the pype-line is purged.
    - If Base is None, PypeLine2 behaves like a bare container of objects,
    with possibility to group them automatically and extract the part-list.
    """

    def __init__(self, obj,rating, DN="DN50", OD=60.3, thk=3, BR=None, lab=None):
        # initialize the parent class
        super(PypeLine2, self).__init__(obj)
        # define common properties
        obj.Proxy = self
        obj.PType = "PypeLine"
        obj.PSize = DN
        obj.PRating = rating
        if lab:
            obj.Label = lab
        # define specific properties
        if not BR:
            BR = 0.75 * OD
        # OD first: onChanged("OD") resets BendRadius to 0.75 * OD.
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "PypeLine2",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "BendRadius",
            "PypeLine2",
            QT_TRANSLATE_NOOP("App::Property", "the radius of bending"),
        ).BendRadius = BR
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "PypeLine2",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        obj.addProperty(
            "App::PropertyString",
            "Group",
            "PypeLine2",
            QT_TRANSLATE_NOOP("App::Property", "The group."),
        ).Group = obj.Label + "_pieces"
        group = FreeCAD.activeDocument().addObject("App::DocumentObjectGroup", obj.Group)
        group.addObject(obj)
        FreeCAD.Console.PrintWarning("Created group " + obj.Group + "\n")
        obj.addProperty("App::PropertyLink", "Base", "PypeLine2", "the edges")

    def onChanged(self, fp, prop):
        if prop == "Label" and len(fp.InList):
            fp.InList[0].Label = fp.Label + "_pieces"
            fp.Group = fp.Label + "_pieces"
        if hasattr(fp, "Base") and prop == "Base" and fp.Base:
            FreeCAD.Console.PrintWarning(fp.Label + " Base has changed to " + fp.Base.Label + "\n")
        if prop == "OD":
            fp.BendRadius = 0.75 * fp.OD

    def purge(self, fp):
        group = FreeCAD.activeDocument().getObjectsByLabel(fp.Group)[0]
        for o in group.OutList:
            if hasattr(o, "PType") and o.PType in ["Pipe", "Elbow"]:
                FreeCAD.activeDocument().removeObject(o.Name)

    def update(self, fp, edges=None):
        from DraftVecUtils import rounded
        from math import degrees

        if not edges and hasattr(fp.Base, "Shape"):
            edges = fp.Base.Shape.Edges
            if not edges:
                FreeCAD.Console.PrintError("Base has not valid edges\n")
                return
        pipes = list()
        for e in edges:
            # ---Create the tube---
            p = pCmd.makePipe(fp.PRating,
                [fp.PSize, fp.OD, fp.thk, e.Length], pos=e.valueAt(0), Z=e.tangentAt(0)
            )
            p.PRating = fp.PRating
            p.PSize = fp.PSize
            pCmd.moveToPyLi(p, fp.Label)
            pipes.append(p)
            n = len(pipes) - 1
            if n and not fCmd.isParallel(fCmd.beamAx(pipes[n]), fCmd.beamAx(pipes[n - 1])):
                # ---Create the curve---
                propList = [fp.PSize, fp.OD, fp.thk, 90, fp.BendRadius]
                c = pCmd.makeElbowBetweenThings(edges[n], edges[n - 1], propList)
                if c:
                    c.PRating = fp.PRating
                    portA, portB = [c.Placement.multVec(port) for port in c.Ports]
                    # ---Trim the tube---
                    p1, p2 = pipes[-2:]
                    fCmd.extendTheBeam(p1, portA)
                    fCmd.extendTheBeam(p2, portB)
                    pCmd.moveToPyLi(c, fp.Label)

    def execute(self, fp):
        return None

class ViewProviderPypeLine:
    def __getstate__(self):
        return None

    def __setstate__(self, data):
        return None

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return get_icon_path("Quetzal_InsertPypeLine")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

        def getIcon(self):
            from os.path import join, dirname, abspath

            return get_icon_path("Quetzal_InsertPypeLine")

        def attach(self, vobj):
            self.ViewObject = vobj
            self.Object = vobj.Object

class Ubolt:
    """Class for object PType="Clamp"
    UBolt(obj,[PSize="DN50",ClampType="U-bolt", C=76, H=109, d=10])
      obj: the "App::FeaturePython" object
      PSize (string): nominal diameter
      ClampType (string): the clamp type or standard
      C (float): the diameter of the U-bolt
      H (float): the total height of the U-bolt
      d (float): the rod diameter
    """

    def __init__(self, obj, DN="DN50", ClampType="DIN-UBolt", C=76, H=109, d=10):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyString",
            "PType",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Type of pipeFeature"),
        ).PType = "Clamp"
        obj.addProperty(
            "App::PropertyString",
            "ClampType",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Type of clamp"),
        ).ClampType = ClampType
        obj.addProperty(
            "App::PropertyString",
            "PSize",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Size of clamp"),
        ).PSize = DN
        obj.addProperty(
            "App::PropertyLength",
            "C",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Arc diameter"),
        ).C = C
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Overall height"),
        ).H = H
        obj.addProperty(
            "App::PropertyLength",
            "d",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Rod diameter"),
        ).d = d
        obj.addProperty(
            "App::PropertyString",
            "thread",
            "Ubolt",
            QT_TRANSLATE_NOOP("App::Property", "Size of thread"),
        ).thread = "M" + str(d)
        obj.addProperty(
            "App::PropertyVectorList",
            "Ports",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Ports position relative to the origin of Shape"),
        )

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        fp.thread = "M" + str(float(fp.d))
        c = Part.makeCircle(fp.C / 2, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 0, 180)
        l1 = Part.makeLine((fp.C / 2, 0, 0), (fp.C / 2, fp.C / 2 - fp.H, 0))
        l2 = Part.makeLine((-fp.C / 2, 0, 0), (-fp.C / 2, fp.C / 2 - fp.H, 0))
        p = Part.Face(
            Part.Wire(
                Part.makeCircle(
                    fp.d / 2, c.valueAt(c.FirstParameter), c.tangentAt(c.FirstParameter)
                )
            )
        )
        path = Part.Wire([c, l1, l2])
        fp.Shape = path.makePipe(p)
        fp.Ports = [FreeCAD.Vector(0, 0, 1)] #not quite sure why a U-bolt has a port?


class BeamClamp:
    """Class for object PType="Clamp".
    BeamClamp(obj,[PSize="LA037-short", ClampType="Beam", ProductCode="LA037",
                   Bolt="M10", Y=20, X=11, V=4, T=5, W=26])
      obj: the "App::FeaturePython" object
      PSize (string): catalog size row
      ClampType (string): clamp family
      ProductCode (string): vendor product code
      Bolt (string): nominal fastener size
      Y, X, V, T, W (float): catalog dimensions in mm
    """

    def __init__(
        self,
        obj,
        PSize="LA037-short",
        ClampType="Beam",
        ProductCode="LA037",
        Bolt="M10",
        Y=20,
        X=11,
        V=4,
        T=5,
        W=26,
    ):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyString",
            "PType",
            "BeamClamp",
            QT_TRANSLATE_NOOP("App::Property", "Type of pipeFeature"),
        ).PType = "Clamp"
        obj.addProperty(
            "App::PropertyString",
            "ClampType",
            "BeamClamp",
            QT_TRANSLATE_NOOP("App::Property", "Type of clamp"),
        ).ClampType = ClampType
        obj.addProperty(
            "App::PropertyString",
            "PSize",
            "BeamClamp",
            QT_TRANSLATE_NOOP("App::Property", "Size of clamp"),
        ).PSize = PSize
        obj.addProperty(
            "App::PropertyString",
            "ProductCode",
            "BeamClamp",
            QT_TRANSLATE_NOOP("App::Property", "Catalog product code"),
        ).ProductCode = ProductCode
        obj.addProperty(
            "App::PropertyString",
            "Bolt",
            "BeamClamp",
            QT_TRANSLATE_NOOP("App::Property", "Bolt size"),
        ).Bolt = Bolt
        for prop, value, text in [
            ("Y", Y, "Clamp height"),
            ("X", X, "Clamp body length"),
            ("V", V, "Tail length"),
            ("T", T, "Clamp thickness"),
            ("W", W, "Clamp width"),
        ]:
            obj.addProperty(
                "App::PropertyLength",
                prop,
                "BeamClamp",
                QT_TRANSLATE_NOOP("App::Property", text),
            )
            setattr(obj, prop, value)
        obj.addProperty(
            "App::PropertyVectorList",
            "Ports",
            "PBase",
            QT_TRANSLATE_NOOP("App::Property", "Ports position relative to the origin of Shape"),
        )
        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        height = float(fp.Y)
        body_len = float(fp.X)
        tail_len = float(fp.V)
        thk = float(fp.T)
        width = float(fp.W)
        bolt_dia = self._bolt_diameter(fp.Bolt, max(height * 0.5, 1))

        body = Part.makeBox(
            body_len,
            width,
            height,
            FreeCAD.Vector(-body_len / 2, -width / 2, 0),
        )
        tail = Part.makeBox(
            tail_len,
            width,
            thk,
            FreeCAD.Vector(body_len / 2, -width / 2, 0),
        )
        nose = Part.makeBox(
            thk,
            width,
            thk,
            FreeCAD.Vector(-body_len / 2 - thk, -width / 2, -thk),
        )
        lower_grip = Part.makeBox(
            max(body_len * 0.45, thk),
            width,
            thk,
            FreeCAD.Vector(-body_len / 2, -width / 2, -thk),
        )
        boss = Part.makeCylinder(
            bolt_dia * 0.75,
            thk,
            FreeCAD.Vector(0, 0, height),
            vZ,
        )
        clearance = Part.makeCylinder(
            bolt_dia * 0.58,
            height + thk * 3,
            FreeCAD.Vector(0, 0, -thk * 1.5),
            vZ,
        )
        clamp = body.fuse(tail).fuse(nose).fuse(lower_grip).fuse(boss).cut(clearance)
        bolt = Part.makeCylinder(
            bolt_dia * 0.42,
            height + thk * 3,
            FreeCAD.Vector(0, 0, -thk * 1.5),
            vZ,
        )
        head = Part.makeCylinder(
            bolt_dia * 0.85,
            thk * 0.8,
            FreeCAD.Vector(0, 0, height + thk),
            vZ,
        )
        fp.Shape = clamp.fuse(bolt).fuse(head)
        fp.Ports = [FreeCAD.Vector(0, 0, 0)]

    def _bolt_diameter(self, bolt, fallback):
        try:
            return float(str(bolt).strip().upper().replace("M", ""))
        except Exception:
            return fallback


class Shell:
    """
    Class for a lateral-shell-of-tank object
    Shell(obj[,L=800,W=400,H=500,thk=6])
      obj: the "App::FeaturePython" object
      L (float): the length
      W (float): the width
      H (float): the height
      thk1 (float): the shell thickness
      thk2 (float): the top thickness
    """

    def __init__(self, obj, L=800, W=400, H=500, thk1=6, thk2=8):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyLength",
            "L",
            "Tank",
            QT_TRANSLATE_NOOP("App::Property", "Tank's length"),
        ).L = L
        obj.addProperty(
            "App::PropertyLength",
            "W",
            "Tank",
            QT_TRANSLATE_NOOP("App::Property", "Tank's width"),
        ).W = W
        obj.addProperty(
            "App::PropertyLength",
            "H",
            "Tank",
            QT_TRANSLATE_NOOP("App::Property", "Tank's height"),
        ).H = H
        obj.addProperty(
            "App::PropertyLength",
            "thk1",
            "Tank",
            QT_TRANSLATE_NOOP("App::Property", "Thickness of tank's shell"),
        ).thk1 = thk1
        obj.addProperty(
            "App::PropertyLength",
            "thk2",
            "Tank",
            QT_TRANSLATE_NOOP("App::Property", "Thickness of tank's top"),
        ).thk2 = thk2

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        O = FreeCAD.Vector(0, 0, 0)
        vectL = FreeCAD.Vector(fp.L, 0, 0)
        vectW = FreeCAD.Vector(0, fp.W, 0)
        vectH = FreeCAD.Vector(0, 0, fp.H)
        base = [vectL, vectW, vectH]
        outline = []
        for i in range(3):
            f1 = Part.Face(Part.makePolygon([O, base[0], base[0] + base[1], base[1], O]))
            outline.append(f1)
            f2 = f1.copy()
            f2.translate(base[2])
            outline.append(f2)
            base.append(base.pop(0))
        box = Part.Solid(Part.Shell(outline))
        tank = box.makeThickness([box.Faces[0], box.Faces[2]], -fp.thk1, 1.0e-3)
        top = Part.makeBox(
            fp.L - 2 * fp.thk1,
            fp.W - 2 * fp.thk1,
            fp.thk2,
            FreeCAD.Vector(fp.thk1, fp.thk1, fp.H - 2 * fp.thk2),
        )
        fp.Shape = Part.makeCompound([tank, top])

class ViewProviderPypeBranch:
    def __init__(self, vobj):
        vobj.Proxy = self
        if FREECADVERSION > 0.19:
            vobj.addExtension("Gui::ViewProviderGroupExtensionPython")
        else:
            vobj.addExtension("Gui::ViewProviderGroupExtensionPython", self)  # 20220704
        # vobj.ExtensionProxy=self #20220703

    def getIcon(self):
        return get_icon_path("Quetzal_InsertBranch")

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
            FreeCAD.ActiveDocument.getObject(name)
            for name in self.Object.Tubes + self.Object.Curves
        ]
        return children

    def onDelete(self, feature, subelements):  # subelements is a tuple of strings
        return True

class Valve(pypeType):
    """Class for object PType="Valve"

    Three construction modes selected automatically by the Conn property:

    Generic valve (two-cone construction as found on P&IDs)  (no Conn)
    ------------------------------------------------------------------
    Valve(obj, DN="DN50", VType="ball", ODBody=72, ID=50, H=40, Kv=150)

    Socket-weld / Threaded hex-body valve  (Conn == "SW" or "TH")
    ------------------------------------------------------------------
      OD      (float) : attachment pipe outer diameter
      ODBody  (float) : hex body flat-to-flat dimension
      H       (float) : total body length (symmetric +/-H/2 from center)
      E       (float) : socket / thread engagement depth
      Conn    (string): "SW" or "TH"

    Flanged Trunnion Ball valve  (Conn == "150lb", "300lb", "600lb",
                                  "900lb", "1500lb", or "2500lb")
    ------------------------------------------------------------------
      H       (float) : body length, flange face to flange face
      Conn    (string): one of the pressure class strings above
      flgD    (float) : flange outer diameter  (from blind flange table)
      flgt    (float) : flange thickness       (from blind flange table)
      flgdrf  (float) : raised-face diameter   (from blind flange table)
      flgtrf  (float) : raised-face thickness  (from blind flange table)
      flgdf   (float) : bolt-circle diameter   (from blind flange table)
      flgf    (float) : bolt-hole diameter     (from blind flange table)
      flgn    (int)   : number of bolt holes   (from blind flange table)
      BottomH (float) : lower body envelope from pipe centerline (optional)
      TopH    (float) : upper body envelope from pipe centerline (optional)

    Local coordinate system (all variants)
    ----------------------------------------
      Axis  : Z  (flow direction)
      Origin: geometric center of the valve body
      Port 0: (0, 0,  H/2)   direction (0, 0,  1)
      Port 1: (0, 0, -H/2)   direction (0, 0, -1)
    """

    # Pressure-class strings that indicate a flanged connection
    FLANGE_CONNS = ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb")

    _FLANGED_ACTUATOR_DOC = ("Actuator type: Handle, Handle-closed or Gearbox; "
                             "gate and globe valves: Handwheel, "
                             "Handwheel-closed, Gearbox or Gearbox-closed; "
                             "globe valves also Pneumatic or Pneumatic-closed")

    def __init__(self, obj, DN="DN50", VType="ball", ODBody=72, ID=50, H=40, Kv=150,
                 OD=None, E=None, Conn=None,
                 flgD=0, flgt=0, flgdrf=0, flgtrf=0,
                 flgdf=0, flgf=0, flgn=0,
                 actuator="Handle", bottomH=0, topH=0, wheelD=0,
                 E2=None, Conn2=None):
        super(Valve, self).__init__(obj)
        obj.Proxy   = self
        obj.PType   = "Valve"
        obj.PRating = VType
        obj.PSize   = DN
        obj.Kv      = Kv

        obj.addProperty(
            "App::PropertyLength", "ODBody", "Valve",
            QT_TRANSLATE_NOOP("App::Property",
                              "Outside diameter of valve body (hex flat-to-flat for SW/TH)"),
        ).ODBody = ODBody

        obj.addProperty(
            "App::PropertyLength", "Height", "Valve",
            QT_TRANSLATE_NOOP("App::Property", "Overall body length"),
        ).Height = H

        _flanged = ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb")
        if Conn is not None and Conn.strip() in _flanged:
            # -- Flanged valve properties ------------------------------------
            obj.addProperty(
                "App::PropertyString", "Conn", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Connection type / pressure class (e.g. 150lb)"),
            ).Conn = Conn
            obj.addProperty(
                "App::PropertyLength", "FlgD", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Flange outer diameter"),
            ).FlgD = flgD
            obj.addProperty(
                "App::PropertyLength", "Flgt", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Flange thickness"),
            ).Flgt = flgt
            obj.addProperty(
                "App::PropertyLength", "FlgDrf", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Raised-face diameter"),
            ).FlgDrf = flgdrf
            obj.addProperty(
                "App::PropertyLength", "FlgTrf", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Raised-face thickness"),
            ).FlgTrf = flgtrf
            obj.addProperty(
                "App::PropertyLength", "FlgDf", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Bolt-circle diameter"),
            ).FlgDf = flgdf
            obj.addProperty(
                "App::PropertyLength", "FlgF", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Bolt-hole diameter"),
            ).FlgF = flgf
            obj.addProperty(
                "App::PropertyInteger", "FlgN", "ValveFlange",
                QT_TRANSLATE_NOOP("App::Property", "Number of bolt holes"),
            ).FlgN = int(flgn)
            obj.addProperty(
                "App::PropertyString", "Actuator", "Valve",
                QT_TRANSLATE_NOOP("App::Property", self._FLANGED_ACTUATOR_DOC),
            ).Actuator = actuator
            obj.addProperty(
                "App::PropertyLength", "BottomH", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Lower body envelope from valve centerline"),
            ).BottomH = bottomH
            obj.addProperty(
                "App::PropertyLength", "TopH", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Upper body envelope from valve centerline"),
            ).TopH = topH
            obj.addProperty(
                "App::PropertyLength", "WheelD", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Handwheel diameter (gate valves), 0 = derived"),
            ).WheelD = wheelD

        elif Conn is not None:
            # -- Socket-weld / Threaded valve properties ---------------------
            if OD is None:
                OD = ODBody * 0.7
            if E is None:
                E = H * 0.2
            obj.addProperty(
                "App::PropertyLength", "OD", "Valve",
                QT_TRANSLATE_NOOP("App::Property", "Attachment pipe outer diameter"),
            ).OD = OD
            obj.addProperty(
                "App::PropertyLength", "E", "Valve",
                QT_TRANSLATE_NOOP("App::Property", "Socket / thread engagement depth"),
            ).E = E
            obj.addProperty(
                "App::PropertyString", "Conn", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Connection type: SW = Socket Weld, TH = Threaded"),
            ).Conn = Conn
            self._addPort1Conn(obj, E if E2 is None else E2,
                               Conn if Conn2 is None else Conn2)
            obj.addProperty(
                "App::PropertyString", "Actuator", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Actuator type: Handle or Handle-closed"),
            ).Actuator = actuator
        else:
            # -- Generic (legacy) valve properties --------------------------
            obj.addProperty(
                "App::PropertyLength", "ID", "Valve",
                QT_TRANSLATE_NOOP("App::Property", "Inside diameter"),
            ).ID = ID

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def onDocumentRestored(self, fp):
        # SW/TH valves created before the Actuator property existed get it
        # here (open handle) so it can be switched in the property editor.
        if str(getattr(fp, "Conn", "")).strip() in ("SW", "TH") and \
                "Actuator" not in fp.PropertiesList:
            fp.addProperty(
                "App::PropertyString", "Actuator", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Actuator type: Handle or Handle-closed"),
            ).Actuator = "Handle"
        # SW/TH valves created before port 1 had its own end connection.
        if str(getattr(fp, "Conn", "")).strip() in ("SW", "TH") and \
                "E2" not in fp.PropertiesList:
            self._addPort1Conn(fp, float(fp.E), fp.Conn)
        # Flanged valves created before the WheelD property existed.
        if str(getattr(fp, "Conn", "")).strip() in \
                ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb") and \
                "WheelD" not in fp.PropertiesList:
            fp.addProperty(
                "App::PropertyLength", "WheelD", "Valve",
                QT_TRANSLATE_NOOP("App::Property",
                                  "Handwheel diameter (gate valves), 0 = derived"),
            ).WheelD = 0

    @staticmethod
    def _addPort1Conn(obj, E2, Conn2):
        """Port 1 (-Z) end of a SW/TH valve: engagement depth and type.
        Equal to E / Conn except on a socket x threaded valve."""
        obj.addProperty(
            "App::PropertyLength", "E2", "Valve",
            QT_TRANSLATE_NOOP("App::Property",
                              "Socket / thread engagement depth at port 1"),
        ).E2 = E2
        obj.addProperty(
            "App::PropertyString", "Conn2", "Valve",
            QT_TRANSLATE_NOOP("App::Property",
                              "Connection type at port 1: SW or TH"),
        ).Conn2 = Conn2

    @staticmethod
    def _orientHandle(handle, actuator):
        """Turn the stem + paddle 90 deg about the stem (local Y) axis when
        the actuator is "Handle-closed"; the open handle lies along the flow."""
        if str(actuator).strip().lower() == "handle-closed":
            handle.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), 90)
        return handle

    @staticmethod
    def _blFlange(fp, z_face, face_up):
        """Return a solid blind flange (BL style) from the valve's Flg*
        properties, positioned so that its raised-face surface lies at
        z = z_face.
        face_up=True  -> flange body extends in +Z, raised face in -Z
        face_up=False -> flange body extends in -Z, raised face in +Z
        """
        flgD   = float(fp.FlgD)
        flgt   = float(fp.Flgt)
        flgDrf = float(fp.FlgDrf)
        flgTrf = float(fp.FlgTrf)
        flgDf  = float(fp.FlgDf)
        flgF   = float(fp.FlgF)
        flgN   = int(fp.FlgN)
        sign = 1.0 if face_up else -1.0

        # Disc (no bore for BL) with bolt holes, rotated to match the
        # standard Flange class offset
        base = Part.Face(Part.Wire(Part.makeCircle(flgD / 2.0)))
        if flgN > 0 and flgF > 0 and flgDf > 0:
            hole = Part.Face(
                Part.Wire(
                    Part.makeCircle(
                        flgF / 2.0,
                        FreeCAD.Vector(flgDf / 2.0, 0, 0),
                        FreeCAD.Vector(0, 0, 1),
                    )
                )
            )
            hole.rotate(FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(0, 0, 1), 360.0 / flgN / 2.0)
            for i in range(flgN):
                base = base.cut(hole)
                hole.rotate(FreeCAD.Vector(0, 0, 0),
                            FreeCAD.Vector(0, 0, 1), 360.0 / flgN)

        # Extrude disc body away from the face
        flange = base.extrude(FreeCAD.Vector(0, 0, sign * flgt))

        # Raised face toward the mating side
        if flgTrf > 0 and flgDrf > 0:
            rf = Part.makeCylinder(
                flgDrf / 2.0, flgTrf,
                FreeCAD.Vector(0, 0, 0),
                FreeCAD.Vector(0, 0, -sign),
            )
            flange = flange.fuse(rf)

        # Translate so the mating face lands at z_face
        flange.translate(FreeCAD.Vector(0, 0, z_face + flgTrf * sign))
        return flange

    @staticmethod
    def _gearboxWheel(axle_base, pipe_od):
        """Return the gearbox handwheel: axle, four spokes and rim.

        The axle starts at axle_base and runs pipe_od/2 along +X.  Four
        spokes (radius 10 mm) leave its far end at 60 deg from X toward
        +/-Y and +/-Z; the rim is a torus about X with radius pipe_od + 75
        and tube radius 12, centred where the spokes meet it.
        """
        import math
        # -- Handwheel axle: diameter = min(25.4, pipe_od)
        axle_r   = min(25.4, pipe_od) / 2.0
        axle_len = pipe_od / 2.0
        wheel = Part.makeCylinder(axle_r, axle_len, axle_base,
                                  FreeCAD.Vector(1, 0, 0))

        # -- Four spokes around the axle
        spoke_len    = (pipe_od + 75.0) / math.cos(math.radians(30.0))
        spoke_r      = 10.0
        spoke_origin = FreeCAD.Vector(axle_base.x + axle_len,
                                      axle_base.y, axle_base.z)
        spoke_angle = 60  # degrees
        cos60 = math.cos(math.radians(spoke_angle))
        sin60 = math.sin(math.radians(spoke_angle))
        spoke_dirs = [
            FreeCAD.Vector(cos60,  sin60, 0),   # +Y quadrant
            FreeCAD.Vector(cos60, -sin60, 0),   # -Y quadrant
            FreeCAD.Vector(cos60, 0,  sin60),   # +Z quadrant
            FreeCAD.Vector(cos60, 0, -sin60),   # -Z quadrant
        ]
        spokes = None
        for sd in spoke_dirs:
            spoke = Part.makeCylinder(spoke_r, spoke_len, spoke_origin, sd)
            spokes = spoke if spokes is None else spokes.fuse(spoke)

        # -- Handwheel torus, axis = X (same as axle)
        torus_cx = spoke_origin.x + spoke_len * math.sin(math.radians(90 - spoke_angle))
        torus = Part.makeTorus(
            pipe_od + 75.0, 12.0,
            FreeCAD.Vector(torus_cx, spoke_origin.y, spoke_origin.z),
            FreeCAD.Vector(1, 0, 0),
        )
        return wheel.fuse(spokes).fuse(torus)

    def execute(self, fp):
        H = float(fp.Height)
        conn = getattr(fp, "Conn", None)
        # Check for flanged pressure-class connection.
        # The tuple is inlined here rather than referenced via self.FLANGE_CONNS
        # to ensure correct dispatch when the proxy is reconstructed on reload.
        _flanged = ("150lb", "300lb", "600lb", "900lb", "1500lb", "2500lb")
        if conn is not None and conn.strip() in _flanged:
            rating = getattr(fp, "PRating", "").lower()
            if "check_swing" in rating or "swing_check" in rating:
                self._execute_swing_check_valve(fp, H)
            elif rating.startswith("gate"):
                self._execute_rising_flanged(fp, H, "gate")
            elif rating.startswith("globe"):
                self._execute_rising_flanged(fp, H, "globe")
            else:
                self._execute_flanged(fp, H)
        elif conn is not None:
            rating = getattr(fp, "PRating", "").lower()
            if rating.startswith("gate"):
                self._execute_rising_sw_th(fp, H, "gate")
            elif rating.startswith("globe"):
                self._execute_rising_sw_th(fp, H, "globe")
            elif rating.startswith("check"):
                self._execute_check_sw_th(fp, H)
            else:
                self._execute_sw_th(fp, H)
        else:
            self._execute_legacy(fp, H)
        super(Valve, self).execute(fp)

    def _execute_flanged(self, fp, H):
        """Build a Trunnion Ball valve body with raised-face flanges.

        Geometry (all dimensions in mm, local Z is the flow axis):

          - Two raised-face blind flanges (BL style):
              bottom flange face at z = -H/2  (raised face projects toward -Z)
              top    flange face at z = +H/2  (raised face projects toward +Z)

          - Connecting (outer) cylinder:
              diameter = flgDrf (same diameter as raised face)
              from z = -H/2+flgTrf to z = +H/2-flgTrf

          - Center body cylinder:
              diameter = connecting_cylinderOD  (same outer shell)
              from z = -H/2 + flange_t*3  to  z = +H/2 - flange_t*3
              (height = H - 6*flange_t)

          - Handle stem + paddle attached at the outer equator of the center body.

        Ports are at (0,0,-H/2) and (0,0,+H/2).
        """
        flgD   = float(fp.FlgD)    # flange outer diameter
        flgt   = float(fp.Flgt)    # flange thickness (t in the table)
        flgDrf = float(fp.FlgDrf)  # raised-face diameter

        # Pipe OD for the nominal size from the module-level dictionary
        pipe_od = pipe_OD.get(fp.PSize, float(fp.ODBody))

        # Connecting cylinder OD (average of pipe OD and flange OD)
        conn_cyl_OD = flgDrf

        # Center body height = H - 6 * flange_t
        body_h = H - 6.0 * flgt
        if body_h < 1.0:
            body_h = 1.0  # safety floor

        flange_bot = self._blFlange(fp, -H / 2.0, face_up=True)   # mating face at -H/2
        flange_top = self._blFlange(fp,  H / 2.0, face_up=False)  # mating face at +H/2

        # ── connecting (outer) cylinder ────────────────────────────────────
        conn_cyl = Part.makeCylinder(
            conn_cyl_OD / 2.0, H,
            FreeCAD.Vector(0, 0, -(H/2.0)),
            FreeCAD.Vector(0, 0, 1),
        )

        # ── center body cylinder (diameter = flgD) ────────────────────────
        body_z0 = -H / 2.0 + flgt * 3.0
        center_body = Part.makeCylinder(
            flgD / 2.0, body_h,
            FreeCAD.Vector(0, 0, body_z0),
            FreeCAD.Vector(0, 0, 1),
        )

        #bore hole along Z axis (diameter = 95% of pipe_OD, length = 2 mm longer than valve to ensure clean cut)
        bore_r = pipe_od * 0.95 / 2.0
        bore = Part.makeCylinder(
            bore_r, H + 2.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - 1.0),
            FreeCAD.Vector(0, 0, 1),
        )

        # ── fuse main shapes
        valve = flange_bot.fuse(flange_top)
        valve = valve.fuse(conn_cyl)
        valve = valve.fuse(center_body)
        

        # ── actuator (handle or gearbox) ──────────────────────────────────
        actuator = getattr(fp, "Actuator", "Handle")

        if actuator == "Gearbox":
            # -- Gearbox cylinder ---------------------------------------
            # Rises from (0,0,0) in the +Y direction, diameter = pipe_od
            gearbox_h = pipe_od + 100.0
            gearbox = Part.makeCylinder(
                pipe_od / 2.0, gearbox_h,
                FreeCAD.Vector(0, 0, 0),
                FreeCAD.Vector(0, 1, 0),
            )

            # -- Handwheel on a horizontal axle at the gearbox top -------
            wheel = self._gearboxWheel(
                FreeCAD.Vector(0, pipe_od + 100.0, -pipe_od / 2.0), pipe_od)

            valve = valve.fuse(gearbox)
            valve = valve.fuse(wheel)
            valve = valve.cut(bore)
            valve = valve.removeSplitter()
            fp.Shape = valve

        else:
            # -- Handle (stem + paddle) ---------------------------------
            # Stem extends the lesser of 25 mm or the pipe outer diameter above the valve body
            stem_y0     = 0
            stem_height = min(25.0, pipe_od) + flgD/2.0 
            stem = Part.makeCylinder(
                5.0, stem_height,
                FreeCAD.Vector(0, stem_y0, 0),
                FreeCAD.Vector(0, 1, 0),
            )

            hw            = min(25.0, pipe_od) / 2.0
            ht            = 1.5
            paddle_base_y = stem_y0 + stem_height - 5.0
            py0           = paddle_base_y
            py1           = paddle_base_y + 15.0
            pz_end        = max(50.0, H)

            P0 = FreeCAD.Vector(0, py0, -15.0)
            P1 = FreeCAD.Vector(0, py0,  15.0)
            P2 = FreeCAD.Vector(0, py1,  30.0)
            P3 = FreeCAD.Vector(0, py1,  pz_end)

            def _seg_prism(start, end):
                """Rectangular prism from start to end with cross-section 2*hw x 2*ht."""
                seg = end - start
                length = seg.Length
                if length < 1e-6:
                    return None
                d = FreeCAD.Vector(seg).normalize()
                up = FreeCAD.Vector(0, 0, 1)
                if abs(d.dot(up)) > 0.99:
                    up = FreeCAD.Vector(0, 1, 0)
                ax1 = d.cross(up).normalize()
                ax2 = d.cross(ax1).normalize()
                c0 = start + ax1 * hw + ax2 * ht
                c1 = start - ax1 * hw + ax2 * ht
                c2 = start - ax1 * hw - ax2 * ht
                c3 = start + ax1 * hw - ax2 * ht
                wire = Part.Wire([
                    Part.makeLine(c0, c1),
                    Part.makeLine(c1, c2),
                    Part.makeLine(c2, c3),
                    Part.makeLine(c3, c0),
                ])
                face = Part.Face(wire)
                return face.extrude(d * length)

            prism0 = _seg_prism(P0, P1)
            prism1 = _seg_prism(P1, P2)
            prism2 = _seg_prism(P2, P3)

            handle = prism0
            if prism1:
                handle = handle.fuse(prism1)
            if prism2:
                handle = handle.fuse(prism2)

            handle = self._orientHandle(stem.fuse(handle), actuator)
            valve = valve.fuse(handle)
            valve = valve.cut(bore)
            valve = valve.removeSplitter()
            fp.Shape = valve

        # ── ports at flange faces ─────────────────────────────────────────
        fp.Ports = [
            FreeCAD.Vector(0, 0,  H / 2.0),
            FreeCAD.Vector(0, 0, -H / 2.0),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0,  1),
            FreeCAD.Vector(0, 0, -1),
        ]

    def _execute_rising_flanged(self, fp, H, style):
        """Build a flanged OS&Y gate or globe valve (style "gate"/"globe").

        Local Z is the flow axis, +Y is the stem axis, origin at the body
        center; ports at the flange faces like the other flanged valves.
        The body, bonnet, trim, yoke and actuator come from _risingStemValve.

        Flanged mapping (pipe_od from the PSize, mm)
          bore radius   r = 0.95 pipe_od / 2 (as the other flanged valves)
          wall          max(5, 0.35 Flgt); bonnet flange max(8, 0.6 Flgt)
          body          held inside the flanges (H/2 - Flgt - FlgTrf)
          neck          r + wall, between the body and each flange
          stem          bare cylinder, radius max(6, 0.08 pipe_od)
        """
        V = FreeCAD.Vector
        flgt   = float(fp.Flgt)
        flgDrf = float(fp.FlgDrf)
        flgTrf = float(fp.FlgTrf)
        pipe_od = pipe_OD.get(fp.PSize, max(flgDrf * 0.65, 1.0))
        bore_r = max(pipe_od * 0.95 / 2.0, 1.0)
        wall = max(5.0, 0.35 * flgt)

        ends = self._blFlange(fp, -H / 2.0, face_up=True)
        ends = ends.fuse(self._blFlange(fp, H / 2.0, face_up=False))
        ends = ends.fuse(Part.makeCylinder(bore_r + wall, H, V(0, 0, -H / 2.0),
                                           V(0, 0, 1)))
        fp.Shape = self._risingStemValve(
            fp, H, ends, None, bore_r, pipe_od, wall,
            rs=max(6.0, 0.08 * pipe_od), t_bf=max(8.0, 0.6 * flgt),
            rz_max=H / 2.0 - flgt - flgTrf, style=style,
            pneumatic_ok=(style == "globe"))

        fp.Ports = [
            FreeCAD.Vector(0, 0, H / 2.0),
            FreeCAD.Vector(0, 0, -H / 2.0),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, 1),
            FreeCAD.Vector(0, 0, -1),
        ]

    def _execute_rising_sw_th(self, fp, H, style):
        """Build a socket-weld / threaded OS&Y gate or globe valve.

        Same hex end block as the SW/TH ball valve (ODBody across flats,
        bore OD - 6), with a socket or thread pocket of depth E at port 0
        (+Z) and E2 at port 1 (-Z), so FNPT x FNPT, SW x SW and SW x FNPT
        share one model.  The bonnet sits on the top flat of the hex; the
        rest comes from _risingStemValve.  Horizontal handwheel only
        (Gearbox / Pneumatic are drawn as a handwheel); WheelD and TopH are
        derived as for a flanged valve with those properties at 0.

        Mapping (mm)
          wall          max(2.5, 0.12 ODBody); bonnet flange max(4, 0.15 ODBody)
          stem          radius max(2.5, 0.08 OD + 2)
          scale         fixed minimum sizes (wedge thickness, stuffing box,
                        yoke gap, ...) times clamp(OD / 60, 0.5, 1)
        """
        import math
        V = FreeCAD.Vector
        OD     = float(fp.OD)
        ODBody = float(fp.ODBody)
        E      = float(fp.E)
        E2     = float(getattr(fp, "E2", 0)) or E
        bore_r = max((OD - 6.0) / 2.0, 1.0)

        hex_r = (ODBody / 2.0) / math.cos(math.radians(30))
        pts = [V(hex_r * math.cos(math.radians(i * 60)),
                 hex_r * math.sin(math.radians(i * 60)), 0) for i in range(6)]
        ends = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, H))
        ends.translate(V(0, 0, -H / 2.0))

        sockets = Part.makeCylinder(OD / 2.0, E + 1.0,
                                    V(0, 0, H / 2.0 + 1.0), V(0, 0, -1))
        sockets = sockets.fuse(Part.makeCylinder(OD / 2.0, E2 + 1.0,
                                                 V(0, 0, -H / 2.0 - 1.0),
                                                 V(0, 0, 1)))
        fp.Shape = self._risingStemValve(
            fp, H, ends, sockets, bore_r, OD, max(2.5, 0.12 * ODBody),
            rs=max(2.5, 0.08 * OD + 2.0), t_bf=max(4.0, 0.15 * ODBody),
            rz_max=H / 2.0 - max(E, E2) - 1.0, y_bf_min=ODBody / 2.0,
            scale=min(1.0, max(0.5, OD / 60.0)), style=style,
            gearbox_ok=False)

        fp.Ports = [
            FreeCAD.Vector(0, 0,  H / 2.0 - E),
            FreeCAD.Vector(0, 0, -H / 2.0 + E2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0,  1),
            FreeCAD.Vector(0, 0, -1),
        ]

    @staticmethod
    def _obround(r, y_center, y_top, half_z):
        """Round-bottomed slab: a cylinder along Z of radius r centred at
        y_center, plus a box up to y_top, z in +/-half_z."""
        V = FreeCAD.Vector
        cyl = Part.makeCylinder(r, 2.0 * half_z, V(0, y_center, -half_z),
                                V(0, 0, 1))
        box = Part.makeBox(2.0 * r, y_top - y_center, 2.0 * half_z,
                           V(-r, y_center, -half_z))
        return cyl.fuse(box)

    def _gateInternals(self, H, bore_r, wall, t_bf, rz_max, y_bf_min, scale,
                       closed):
        """Wedge gate, box cavity, obround body and box bonnet.

        r = bore_r, s = scale (mm)
          gate          width and height 2.2 r, round bottom of radius 1.1 r,
                        wedge thickness max(10 s, 0.44 r) at the top, 75 %
                        of that at the bottom.  Closed: round bottom
                        centred on the bore axis.  Open: bottom r + c
                        above the axis, c = 2 s + 0.02 r.
          cavity        the gate envelope plus c, from the closed bottom up
                        to the open top; the flow bore runs straight through
          body, bonnet  cavity plus wall; the body's flow-direction
                        half-length is at least 0.75 r and at most rz_max.
                        The bonnet flange sits at 2.1 r or y_bf_min.
        """
        V = FreeCAD.Vector
        c = 2.0 * scale + 0.02 * bore_r
        gr = 1.1 * bore_r                 # half width = bottom radius
        gh = 2.2 * bore_r                 # height
        t_top = max(10.0 * scale, 0.44 * bore_r)
        t_bot = 0.75 * t_top
        closed_bot = -gr
        open_bot = bore_r + c
        travel = open_bot - closed_bot
        gate_bot = closed_bot if closed else open_bot
        gate_top = gate_bot + gh

        taper = Part.Face(Part.makePolygon([
            V(-gr - 1.0, gate_bot, -t_bot / 2.0),
            V(-gr - 1.0, gate_bot,  t_bot / 2.0),
            V(-gr - 1.0, gate_top,  t_top / 2.0),
            V(-gr - 1.0, gate_top, -t_top / 2.0),
            V(-gr - 1.0, gate_bot, -t_bot / 2.0),
        ])).extrude(V(2.0 * gr + 2.0, 0, 0))
        gate = self._obround(gr, gate_bot + gr, gate_top, t_top / 2.0).common(taper)

        cav_x = gr + c
        cav_z = t_top / 2.0 + c
        cav_top = open_bot + gh + c
        cavity = self._obround(cav_x, 0.0, cav_top, cav_z)
        cavity = cavity.fuse(Part.makeCylinder(bore_r, H + 2.0,
                                               V(0, 0, -H / 2.0 - 1.0),
                                               V(0, 0, 1)))

        Rb = cav_x + wall
        Rz = min(max(cav_z + wall, 0.75 * bore_r), max(rz_max, cav_z + 1.0))
        y_bf = max(bore_r + 0.5 * gh, y_bf_min)   # bonnet flange
        body = self._obround(Rb, 0.0, y_bf, Rz)

        m = wall                          # bonnet flange margin
        bonnet_flange = Part.makeBox(2.0 * (Rb + m), t_bf, 2.0 * (Rz + m),
                                     V(-Rb - m, y_bf, -Rz - m))
        y_bt = max(cav_top, y_bf + t_bf) + wall   # bonnet top
        bonnet = Part.makeBox(2.0 * Rb, y_bt - y_bf, 2.0 * Rz,
                              V(-Rb, y_bf, -Rz))

        # Bonnet bolts: studs through the flange along both long sides and
        # one at each end.
        bolt_r = max(2.5 * scale, 0.3 * m)
        n_side = max(2, int(2.0 * Rb / max(40.0 * scale, 8.0 * bolt_r)) + 1)
        spots = [V(-Rb + 2.0 * Rb * i / (n_side - 1), 0, s * (Rz + m / 2.0))
                 for i in range(n_side) for s in (-1, 1)]
        spots += [V(s * (Rb + m / 2.0), 0, 0) for s in (-1, 1)]

        return {"body": [body, bonnet_flange, bonnet], "cavity": cavity,
                "trim": gate, "travel": travel, "y_bf": y_bf, "y_bt": y_bt,
                "Rb": Rb, "Rz": Rz, "bolt_r": bolt_r, "bolt_spots": spots,
                "trim_top": gate_top, "trim_h": gh}

    def _globeInternals(self, H, bore_r, wall, t_bf, rz_max, y_bf_min, scale,
                        closed):
        """Plug and seat, round S-pattern cavity, spherical body, round bonnet.

        r = bore_r, s = scale, tw = max(2.5 s, 0.12 r) (mm)
          cavity        round, radius rc = min(1.6 r, rz_max - wall, what the
                        sphere allows).  A deck of thickness tw at the
                        centreline splits it: the inlet (port 0, +Z,
                        "back") bore ends tw short of the upper chamber and
                        opens into the lower chamber; the outlet (port 1,
                        -Z, "front") bore opens into the upper chamber.  Lower chamber
                        r + c deep; the upper chamber above r + tw is a
                        full round of radius max(plug + c, 0.75 rc).
          seat          orifice radius min(0.75 r, rc - 2 tw - 0.1 r)
          plug          radius seat + tw/2, height 0.5 r, conical nose into
                        the seat; lift (travel) max(seat/2, 2 s).  Closed:
                        on the deck.
          body          sphere around the cavity plus wall, at most H/2 - 1;
                        neck of radius upper chamber + wall up to the
                        bonnet flange at 0.75 sphere radius or y_bf_min
          bonnet        round, flange margin = wall, bolt circle in the margin
        """
        import math
        V = FreeCAD.Vector
        c = 2.0 * scale + 0.02 * bore_r
        tw = max(2.5 * scale, 0.12 * bore_r)
        depth = bore_r + c                # lower chamber below the centreline
        rg_max = H / 2.0 - 1.0
        rc = min(1.6 * bore_r, rz_max - wall,
                 math.sqrt(max((rg_max - wall) ** 2 - depth ** 2, 0.0)))
        r_seat = max(min(0.75 * bore_r, rc - 2.0 * tw - 0.1 * bore_r),
                     0.3 * bore_r)
        s = r_seat + tw                   # chamber edges either side of the seat
        z_end = s + tw                    # bores stop / start here
        r_plug = r_seat + 0.5 * tw
        hp = max(0.5 * bore_r, 3.0 * scale)
        travel = max(0.5 * r_seat, 2.0 * scale)
        ru = max(r_plug + c, 0.75 * rc)   # upper chamber above the bores
        y_lo = bore_r + tw                # partition top (full round above)
        y_ut = max(tw / 2.0 + travel + hp + c, y_lo + tw)

        def chamber(y0, y1, r, z_min=None, z_max=None):
            ch = Part.makeCylinder(r, y1 - y0, V(0, y0, 0), V(0, 1, 0))
            if z_min is not None:
                ch = ch.common(Part.makeBox(4 * r, y1 - y0 + 2, 4 * r,
                                            V(-2 * r, y0 - 1, z_min)))
            if z_max is not None:
                ch = ch.common(Part.makeBox(4 * r, y1 - y0 + 2, 4 * r,
                                            V(-2 * r, y0 - 1, z_max - 4 * r)))
            return ch

        cavity = chamber(-depth, -tw / 2.0, rc, z_max=s)        # lower
        cavity = cavity.fuse(chamber(tw / 2.0, y_lo, rc, z_min=-s))
        cavity = cavity.fuse(chamber(y_lo - 0.01, y_ut, ru))
        cavity = cavity.fuse(Part.makeCylinder(r_seat, tw + 1.0,
                                               V(0, -tw / 2.0 - 0.5, 0),
                                               V(0, 1, 0)))
        half = H / 2.0 + 1.0
        cavity = cavity.fuse(Part.makeCylinder(bore_r, half - z_end,
                                               V(0, 0, -half), V(0, 0, 1)))
        cavity = cavity.fuse(Part.makeCylinder(bore_r, half - z_end,
                                               V(0, 0, z_end), V(0, 0, 1)))
        # Built with the inlet at -Z; mirror it so flow runs port 0 -> 1.
        cavity = cavity.mirror(V(0, 0, 0), V(0, 0, 1))

        plug_bot = tw / 2.0 + (0.0 if closed else travel)
        plug = Part.makeCylinder(r_plug, hp, V(0, plug_bot, 0), V(0, 1, 0))
        nose = min(0.4 * r_seat, tw + 0.5 * depth)
        plug = plug.fuse(Part.makeCone(0.98 * r_seat, 0.6 * r_seat, nose,
                                       V(0, plug_bot, 0), V(0, -1, 0)))

        corner = math.sqrt(rc ** 2 + max(depth, y_lo) ** 2)
        Rg = min(corner + wall, rg_max)
        rn = ru + wall                    # neck / bonnet radius
        y_bf = max(0.75 * Rg, y_bf_min, y_lo)
        body = Part.makeSphere(Rg, V(0, 0, 0))
        body = body.fuse(Part.makeCylinder(rn, y_bf, V(0, 0, 0), V(0, 1, 0)))

        m = wall
        bonnet_flange = Part.makeCylinder(rn + m, t_bf, V(0, y_bf, 0),
                                          V(0, 1, 0))
        y_bt = max(y_ut, y_bf + t_bf) + wall
        bonnet = Part.makeCylinder(rn, y_bt - y_bf, V(0, y_bf, 0), V(0, 1, 0))

        bolt_r = max(2.5 * scale, 0.3 * m)
        rbc = rn + m / 2.0
        n = max(4, 2 * int(math.pi * rbc / max(40.0 * scale, 8.0 * bolt_r)))
        spots = [V(rbc * math.cos(2 * math.pi * (i + 0.5) / n), 0,
                   rbc * math.sin(2 * math.pi * (i + 0.5) / n)) for i in range(n)]

        return {"body": [body, bonnet_flange, bonnet], "cavity": cavity,
                "trim": plug, "travel": travel, "y_bf": y_bf, "y_bt": y_bt,
                "Rb": rn, "Rz": rn, "bolt_r": bolt_r, "bolt_spots": spots,
                "trim_top": plug_bot + hp, "trim_h": hp}

    def _risingStemValve(self, fp, H, ends, end_cut, bore_r, pipe_od, wall,
                         rs, t_bf, rz_max, y_bf_min=0.0, scale=1.0,
                         style="gate", gearbox_ok=True, pneumatic_ok=False):
        """Return the solid of an OS&Y rising-stem valve (gate or globe).

        ends     : solid carrying the end connections (flanges and neck, or
                   the SW/TH hex block); fused with the body before cutting.
        end_cut  : solid cut with the cavity (sockets / threads), or None.
        style    : "gate" (_gateInternals) or "globe" (_globeInternals); they
                   supply the body, bonnet, cavity, flow bore and trim.
        Local Z is the flow axis, +Y is the stem axis.

        Actuator
          Handwheel / Handwheel-closed : horizontal handwheel on the yoke nut
          Gearbox   / Gearbox-closed   : bevel gearbox on the yoke with the
                                         ball-valve gearbox handwheel and a
                                         stem protector tube (gearbox_ok)
          Pneumatic / Pneumatic-closed : spring-diaphragm actuator on a tall
                                         yoke (pneumatic_ok)
          "-closed" seats the gate / plug and lowers the stem by the travel.
          Handle / Handle-closed (ball-valve values, found on older
          documents) and actuators a valve doesn't offer are drawn as
          Handwheel / Handwheel-closed.

        Table mapping and proportions (s = scale, mm)
          TopH   : centerline to the top of the stem with the valve open;
                   for a gearbox, to the top of its handwheel or stem
                   protector, whichever is higher.  0 or too small for the
                   body below -> the lowest stack that fits.  Not used for
                   a pneumatic actuator.
          WheelD : handwheel outside diameter; 0 -> 0.9 x face-to-face H.
          diaphragm casing  diameter clamp(1.4 pipe_od + 150, 200, 650),
                   yoke legs at least half of that or 3 x travel + 4 x stem
                   radius tall.
        """
        import math

        act = str(getattr(fp, "Actuator", "Handwheel")).strip().lower()
        gearbox = gearbox_ok and act.startswith("gearbox")
        pneumatic = pneumatic_ok and act.startswith("pneumatic")
        closed = act.endswith("-closed")

        V = FreeCAD.Vector
        build = self._globeInternals if style == "globe" else self._gateInternals
        p = build(H, bore_r, wall, t_bf, rz_max, y_bf_min, scale, closed)
        travel = p["travel"]
        y_bf, y_bt, Rb, Rz = p["y_bf"], p["y_bt"], p["Rb"], p["Rz"]

        r_sb = min(max(2.5 * rs, rs + 10.0 * scale), Rb)
        h_sb = max(20.0 * scale, 3.0 * rs)        # stuffing box
        stuffing = Part.makeCylinder(r_sb, h_sb, V(0, y_bt, 0), V(0, 1, 0))

        valve = ends
        for shape in p["body"] + [stuffing]:
            valve = valve.fuse(shape)
        cut = p["cavity"] if end_cut is None else p["cavity"].fuse(end_cut)
        valve = valve.cut(cut)

        bolt_y0 = y_bf - 0.4 * t_bf
        bolt_h = 1.9 * t_bf
        bolts = [Part.makeCylinder(p["bolt_r"], bolt_h, V(q.x, bolt_y0, q.z),
                                   V(0, 1, 0)) for q in p["bolt_spots"]]

        # -- stack above the bonnet: yoke nut, then the actuator ---------
        h_yn = max(20.0 * scale, 3.0 * rs)
        r_yn = 2.2 * rs
        y_yn0_min = y_bt + h_sb + max(2.0 * rs, 30.0 * scale)
        if pneumatic:
            dia = min(650.0, max(200.0, 1.4 * pipe_od + 150.0))
            y_yn0 = max(y_yn0_min, y_bt + max(0.5 * dia,
                                              3.0 * travel + 4.0 * rs))
            above = 0.0
        else:
            if gearbox:
                gb_h = max(60.0, 0.6 * pipe_od)
                prot_h = travel + 10.0    # stem protector above the gearbox
                # The gearbox wheel rim (radius pipe_od + 75, tube 12) is
                # centred at the gearbox top.
                above = gb_h + max(prot_h, pipe_od + 87.0)
            else:
                wheel_d = float(getattr(fp, "WheelD", 0)) or 0.9 * H
                rim_r = min(15.0, max(6.0 * scale, 0.02 * wheel_d))
                hub_h = max(15.0 * scale, 2.0 * rs, 2.0 * rim_r)
                stick = max(rs, 10.0 * scale)  # stem above the hub when closed
                above = hub_h + stick + travel
            top_h = float(getattr(fp, "TopH", 0))
            y_yn0 = max(top_h - above - h_yn, y_yn0_min)
        y_yn1 = y_yn0 + h_yn              # yoke nut top
        top_h = y_yn1 + above             # effective top of the stack

        # Yoke: two legs from the bonnet top to a crossbar holding the nut.
        leg_w = max(10.0 * scale, 1.2 * rs)
        leg_d = min(max(10.0 * scale, 2.0 * rs), 2.0 * Rz)
        x_leg = max(r_sb + leg_w, 0.6 * Rb)
        yoke = Part.makeBox(2.0 * (x_leg + leg_w / 2.0), h_yn, leg_d,
                            V(-x_leg - leg_w / 2.0, y_yn0, -leg_d / 2.0))
        for s in (-1, 1):
            yoke = yoke.fuse(Part.makeBox(
                leg_w, y_yn0 - y_bt + 1.0, leg_d,
                V(s * x_leg - leg_w / 2.0, y_bt - 1.0, -leg_d / 2.0)))
        yoke = yoke.fuse(Part.makeCylinder(r_yn, h_yn, V(0, y_yn0, 0),
                                           V(0, 1, 0)))

        stem_y0 = p["trim_top"] - min(rs, 0.25 * p["trim_h"])
        if pneumatic:
            # Spring-diaphragm casing: lower cone, bolted flange ring, upper
            # cone and a small air-connection boss.
            h1, h2 = 0.12 * dia, 0.16 * dia
            t_ring = max(6.0, 0.025 * dia)
            y_ring = y_yn1 + h1
            actuator = Part.makeCone(0.3 * dia, 0.5 * dia, h1, V(0, y_yn1, 0),
                                     V(0, 1, 0))
            actuator = actuator.fuse(Part.makeCylinder(
                0.53 * dia, t_ring, V(0, y_ring - t_ring / 2.0, 0), V(0, 1, 0)))
            actuator = actuator.fuse(Part.makeCone(
                0.5 * dia, 0.32 * dia, h2, V(0, y_ring, 0), V(0, 1, 0)))
            actuator = actuator.fuse(Part.makeCylinder(
                0.06 * dia, 0.04 * dia, V(0, y_ring + h2 - 1.0, 0), V(0, 1, 0)))
            stem_y1 = y_yn1 + 1.0         # stem ends in the yoke nut
        elif gearbox:
            gb_top = y_yn1 + gb_h
            actuator = Part.makeCylinder(pipe_od / 2.0, gb_h, V(0, y_yn1, 0),
                                         V(0, 1, 0))
            actuator = actuator.fuse(self._gearboxWheel(
                V(0, gb_top, -pipe_od / 2.0), pipe_od))
            actuator = actuator.fuse(Part.makeCylinder(
                max(1.5 * rs, rs + 5.0), prot_h, V(0, gb_top, 0),
                V(0, 1, 0)))
            stem_y1 = gb_top              # hidden in the protector above
        else:
            R = wheel_d / 2.0 - rim_r     # rim centre radius
            y_w = y_yn1 + hub_h / 2.0
            actuator = Part.makeCylinder(2.0 * rs, hub_h, V(0, y_yn1, 0),
                                         V(0, 1, 0))
            actuator = actuator.fuse(Part.makeTorus(R, rim_r, V(0, y_w, 0),
                                                    V(0, 1, 0)))
            spoke_r = max(4.0 * scale, 0.7 * rim_r)
            for k in range(4):
                a = math.radians(45.0 + 90.0 * k)
                actuator = actuator.fuse(Part.makeCylinder(
                    spoke_r, R, V(0, y_w, 0), V(math.cos(a), 0, math.sin(a))))
            stem_y1 = top_h - (travel if closed else 0.0)
        stem = Part.makeCylinder(rs, stem_y1 - stem_y0, V(0, stem_y0, 0),
                                 V(0, 1, 0))

        for shape in bolts + [yoke, stem, p["trim"], actuator]:
            valve = valve.fuse(shape)
        return valve.removeSplitter()

    def _execute_swing_check_valve(self, fp, H):
        """Build a flanged swing check valve.

        Local Z is the flow axis, +Y is up.  Flow runs from port 0 (+Z,
        inlet, "back") to port 1 (-Z, outlet, "front"); the disc is drawn
        closed on its seat.

        The disc swings about the hinge pin, so the body's inlet side is a
        quarter torus centred on the pin: the hollow the disc sweeps through
        as it opens, turning from the inlet up into a short round neck
        under the cover (the elbow shape of a cast body; the flow arrow points
        away from it).

        Shape (r = bore radius 0.95 pipe_od / 2, wall = max(5, 0.35 Flgt),
        c = 2 + 0.02 r, neck radius rn = r + wall, mm)
          sweep     quarter torus, tube radius re = 1.1 rn, bend radius
                    R = 1.25 re about the hinge pin, hollow by re - wall:
                    the body from the seat round to the cover.  A cone
                    blends it into the inlet neck over 0.5 re.  The body is
                    centred between the flanges; the cone and then the bend
                    shrink if it would not fit.
          cover neck round, 0.97 re (not tangent to the tube), from the
                    torus's upper end up to the cover
          hinge     pin at the torus centre, R above the axis, in a barrel
                    across the inside corner of the elbow that closes the
                    torus hole (hollow round the pin and arm, reaching
                    max(c, 0.1 x the sweep hollow) into it, + wall); bolted
                    hinge caps on its ends
          disc      radius min(1.12 r, tube hollow - c), thickness
                    max(6, 0.25 r), centred on the pin's plane, R below it;
                    it closes on the end of a short pocket in front of the
                    inlet bore (the seat), the only way into the sweep
          cover     flat bolted cover on a body flange above the hinge
                    corner, at least at the flange outside radius
        BottomH / TopH (catalog envelopes) are kept on the object but no
        longer drive the shape.
        """
        import math
        V = FreeCAD.Vector

        flgD   = float(fp.FlgD)
        flgt   = float(fp.Flgt)
        flgDrf = float(fp.FlgDrf)
        flgTrf = float(fp.FlgTrf)
        pipe_od = pipe_OD.get(fp.PSize, max(flgDrf * 0.65, 1.0))
        br = max(pipe_od * 0.95 / 2.0, 1.0)
        wall = max(5.0, 0.35 * flgt)
        c = 2.0 + 0.02 * br
        rn = br + wall                    # neck radius
        z_room = H / 2.0 - flgt - flgTrf  # body stays inside the flanges

        re = 1.1 * rn                     # sweep tube radius
        Rie = re - wall                   # sweep hollow radius
        rt = 0.97 * re                    # cover neck radius
        Rin = rt - wall
        r_disc = min(1.12 * br, Rie - c)
        td = max(6.0, 0.25 * br)
        t_cf = max(8.0, 0.6 * flgt)       # body flange and cover thickness
        m = max(wall, 1.2 * t_cf)         # flange margin outside the neck
        R = 1.25 * re                     # bend radius = hinge height
        Lc = 0.5 * re                     # sweep-to-inlet-neck cone
        span = 2.0 * z_room - 2.0
        hi = td / 2.0 + 0.5 * wall        # inlet end past the hinge plane
        lo = max(re, rt + m)              # outlet end past the cover centre
        if hi + Lc + R + lo > span:
            Lc = max(0.0, span - hi - R - lo)
        if hi + Lc + R + lo > span:
            R = max(1.05 * re, span - hi - lo)
        z_h = 0.5 * (R + lo - hi - Lc)    # hinge plane: body centred
        z_c = z_h - R                     # cover centre
        z_seat = z_h + td / 2.0           # disc's upstream face
        y_h = R                           # hinge pin axis height

        rp = max(4.0, 0.12 * br)          # hinge pin radius
        rbh = max(2.2 * rp, 0.25 * br)    # hinge boss radius
        rhc = R - Rie + max(c, 0.1 * Rie)  # hollow round the pin and arm
        y_cf = max(y_h + rhc + wall + t_cf / 2.0, y_h + rbh + wall + t_cf,
                   0.5 * flgD)            # cover joint
        y_top = y_cf - t_cf / 2.0         # body runs half into the flange
        y_nk = y_h                        # cover neck starts on the torus end

        def sweep(radius):
            """Quarter torus about the hinge pin, from the closed disc's
            plane up to the cover neck, tube radius `radius`."""
            ring = Part.Face(Part.Wire(Part.makeCircle(radius, V(0, 0, z_h),
                                                       V(0, 0, 1))))
            return ring.revolve(V(0, y_h, z_h), V(1, 0, 0), 90)

        def clip(shape, z_max, y_max, half_x):
            big = 10.0 * (H + y_cf)
            return shape.common(Part.makeBox(2.0 * half_x, y_max + big, big,
                                             V(-half_x, -big, z_max - big)))

        # -- body ------------------------------------------------------------
        body = self._blFlange(fp, -H / 2.0, face_up=True)
        body = body.fuse(self._blFlange(fp, H / 2.0, face_up=False))
        body = body.fuse(Part.makeCylinder(rn, H, V(0, 0, -H / 2.0), V(0, 0, 1)))
        body = body.fuse(sweep(re))
        body = body.fuse(Part.makeCylinder(rt, y_top - y_nk, V(0, y_nk, z_c),
                                           V(0, 1, 0)))
        # Seat pocket wall, then the cone down to the inlet neck.
        body = body.fuse(Part.makeCylinder(re, z_seat - z_h + 0.5 * wall,
                                           V(0, 0, z_h), V(0, 0, 1)))
        z_cone = z_seat + 0.5 * wall
        if Lc > 1.0:
            body = body.fuse(Part.makeCone(re, 0.97 * rn, Lc, V(0, 0, z_cone),
                                           V(0, 0, 1)))
        # Hinge barrel across the inside corner of the elbow, closing the
        # torus hole round the pin.  0.98 x the tube radius wide: flat ends
        # at the tube radius would be tangent to the tube.
        hw = 0.98 * re
        body = body.fuse(Part.makeCylinder(rhc + wall, 2.0 * hw,
                                           V(-hw, y_h, z_h), V(1, 0, 0)))
        body = body.fuse(Part.makeCylinder(rt + m, t_cf,
                                           V(0, y_cf - t_cf, z_c), V(0, 1, 0)))
        # External hinge caps on the flat sides of the corner.
        hb = max(0.4 * wall, 0.5 * rbh)
        cap_t = max(3.0, 0.3 * wall)
        for s in (-1, 1):
            body = body.fuse(Part.makeCylinder(rbh, hb + 1.0,
                                               V(s * (hw - 1.0), y_h, z_h),
                                               V(s, 0, 0)))
            body = body.fuse(Part.makeCylinder(1.3 * rbh, cap_t,
                                               V(s * (hw + hb - 0.5), y_h, z_h),
                                               V(s, 0, 0)))

        # -- cavity: sweep, seat pocket, hinge hollow, cover neck, bore ------------
        cavity = sweep(Rie)
        # Seat pocket, overlapping the sweep by half a wall (a thin overlap
        # leaves them as two solids), c/2 under the sweep hollow so their
        # walls are not tangent.
        cavity = cavity.fuse(Part.makeCylinder(Rie - 0.5 * c, z_seat - z_h + 0.5 * wall,
                                               V(0, 0, z_h - 0.5 * wall),
                                               V(0, 0, 1)))
        x_in = 0.8 * Rie
        # Slightly off the pin axis: coaxial with the sweep's torus the fuse
        # fails to merge them.
        off = 0.03 * rhc
        hollow = Part.makeCylinder(rhc, 2.0 * x_in,
                                   V(-x_in, y_h - off, z_h - off), V(1, 0, 0))
        # Clipped short of the hinge plane: on it, it is coplanar with the
        # sweep's start face, and overlapping the seat pocket the three-way
        # fuse fails.
        cavity = cavity.fuse(clip(hollow, z_h - 0.6 * wall, y_h + rhc + 1.0, x_in))
        # Neck hollow from the sweep's end face (starting inside the sweep
        # leaves two nearly parallel walls 0.03 re apart).
        cavity = cavity.fuse(Part.makeCylinder(Rin, y_cf + 1.0 - y_h,
                                               V(0, y_h, z_c), V(0, 1, 0)))
        cavity = cavity.fuse(Part.makeCylinder(br, H + 2.0, V(0, 0, -H / 2.0 - 1.0),
                                               V(0, 0, 1)))
        valve = body.cut(cavity)

        # -- cover and bolts ----------------------------------------------------
        valve = valve.fuse(Part.makeCylinder(rt + m, t_cf, V(0, y_cf, z_c),
                                             V(0, 1, 0)))
        bolt_r = max(2.5, 0.22 * m)
        rbc = rt + m / 2.0
        n = max(8, 4 * int(2 * math.pi * rbc / max(40.0, 10.0 * bolt_r) / 4))
        nut = max(4.0, 1.4 * bolt_r)
        for i in range(n):
            a = 2.0 * math.pi * (i + 0.5) / n
            px, pz = rbc * math.cos(a), z_c + rbc * math.sin(a)
            valve = valve.fuse(Part.makeCylinder(
                bolt_r, 2.0 * t_cf + 2.5 * bolt_r, V(px, y_cf - t_cf - bolt_r, pz),
                V(0, 1, 0)))
            valve = valve.fuse(Part.makeCylinder(
                nut, 1.2 * bolt_r, V(px, y_cf + t_cf, pz), V(0, 1, 0)))
        # Cap screws on the hinge caps.
        for s in (-1, 1):
            xc = s * (hw + hb - 0.5 + cap_t)
            for k in range(4):
                a = math.radians(45.0 + 90.0 * k)
                valve = valve.fuse(Part.makeCylinder(
                    max(1.5, 0.12 * rbh), max(1.5, 0.5 * cap_t),
                    V(xc - s * 0.2, y_h + 0.95 * rbh * math.cos(a),
                      z_h + 0.95 * rbh * math.sin(a)), V(s, 0, 0)))

        # -- disc, arm and pin -----------------------------------------------------
        disc = Part.makeCylinder(r_disc, td, V(0, 0, z_seat - td), V(0, 0, 1))
        aw = max(2.0 * rp, 0.35 * r_disc)
        at = max(2.0 * rp, 0.5 * td)
        disc = disc.fuse(Part.makeBox(aw, y_h, at + td / 2.0,
                                      V(-aw / 2.0, 0, z_h - td / 2.0 - at)))
        disc = disc.fuse(Part.makeCylinder(rp, 2.0 * x_in + wall,
                                           V(-x_in - wall / 2.0, y_h, z_h),
                                           V(1, 0, 0)))
        valve = valve.fuse(disc)
        merged = valve.removeSplitter()
        # removeSplitter can leave an invalid solid on some sizes.
        fp.Shape = merged if merged.isValid() or not valve.isValid() else valve

        fp.Ports = [
            FreeCAD.Vector(0, 0, H / 2.0),
            FreeCAD.Vector(0, 0, -H / 2.0),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, 1),
            FreeCAD.Vector(0, 0, -1),
        ]

    def _execute_check_sw_th(self, fp, H):
        """Build a socket-weld / threaded swing check valve (simplified).

        Local Z is the flow axis, +Y is up; flow runs from port 0 (+Z, inlet,
        "back") to port 1 (-Z, outlet, "front").  Hex ends (ODBody across
        flats) with a socket or thread pocket of depth E at port 0 and E2 at
        port 1, a bulbous round body between them, a round threaded cap with
        a hex boss on top and a raised flow arrow on each side.  Inside it
        is only hollow (no disc).

        Mapping (mm, F = ODBody)
          hex ends    E + 0.15 F (port 0) and E2 + 0.15 F (port 1) long,
                      joined by a neck of radius 0.42 F
          body        sphere of radius 0.55 F at the centre; hollow by
                      wall = max(2, 0.08 F), kept a wall clear of the
                      socket / thread bottoms; bore OD - 6
          cap         radius 0.38 F up to 0.15 F above the body, hex boss
                      0.45 F across flats, 0.12 F high
          arrow       0.9 x body radius long, pointing to port 1, standing
                      max(0.6, 0.03 F) proud of the body, below the middle
        """
        import math
        V = FreeCAD.Vector
        OD     = float(fp.OD)
        F      = float(fp.ODBody)
        E      = float(fp.E)
        E2     = float(getattr(fp, "E2", 0)) or E
        bore_r = max((OD - 6.0) / 2.0, 1.0)
        wall = max(2.0, 0.08 * F)

        def hexagon(across, length, z0, y0=0.0, axis="z"):
            r = (across / 2.0) / math.cos(math.radians(30))
            if axis == "z":
                pts = [V(r * math.cos(math.radians(i * 60)),
                         y0 + r * math.sin(math.radians(i * 60)), z0)
                       for i in range(6)]
                d = V(0, 0, length)
            else:                         # axis along +Y, flats along Z
                pts = [V(r * math.cos(math.radians(i * 60 + 30)), y0,
                         z0 + r * math.sin(math.radians(i * 60 + 30)))
                       for i in range(6)]
                d = V(0, length, 0)
            return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(d)

        # -- body ------------------------------------------------------------
        l0, l1 = E + 0.15 * F, E2 + 0.15 * F
        valve = hexagon(F, l0, H / 2.0 - l0)
        valve = valve.fuse(hexagon(F, l1, -H / 2.0))
        valve = valve.fuse(Part.makeCylinder(0.42 * F, H, V(0, 0, -H / 2.0),
                                             V(0, 0, 1)))
        Rs = 0.55 * F
        valve = valve.fuse(Part.makeSphere(Rs, V(0, 0, 0)))
        y_cap = Rs + 0.15 * F
        y_cap0 = 0.3 * Rs
        valve = valve.fuse(Part.makeCylinder(0.38 * F, y_cap - y_cap0,
                                             V(0, y_cap0, 0), V(0, 1, 0)))
        valve = valve.fuse(hexagon(0.45 * F, 0.12 * F, 0.0, y_cap - 0.5,
                                   axis="y"))

        # Raised flow arrows: an arrow outline extruded across, kept to a
        # shell h proud of the sphere so it follows the curved side.
        h = max(0.6, 0.03 * F)
        L = 0.9 * Rs
        yc = -0.2 * Rs
        w, wh = 0.07 * Rs, 0.2 * Rs       # shaft and head half-widths
        zt, zb = 0.5 * L, -0.5 * L        # tail and tip
        zn = zb + 0.35 * L                # start of the head
        outline = [V(0, yc - w, zt), V(0, yc + w, zt), V(0, yc + w, zn),
                   V(0, yc + wh, zn), V(0, yc, zb), V(0, yc - wh, zn),
                   V(0, yc - w, zn), V(0, yc - w, zt)]
        prism = Part.Face(Part.makePolygon(outline)).extrude(V(2.0 * Rs, 0, 0))
        prism.translate(V(-Rs, 0, 0))
        arrows = prism.common(Part.makeSphere(Rs + h, V(0, 0, 0)))
        valve = valve.fuse(arrows)

        # -- hollow, bore and end pockets -------------------------------------
        Ri = min(Rs - wall, H / 2.0 - max(E, E2) - wall)
        cut = Part.makeCylinder(bore_r, H + 2.0, V(0, 0, -H / 2.0 - 1.0),
                                V(0, 0, 1))
        if Ri > bore_r:
            cut = cut.fuse(Part.makeSphere(Ri, V(0, 0, 0)))
        cut = cut.fuse(Part.makeCylinder(OD / 2.0, E + 1.0,
                                         V(0, 0, H / 2.0 + 1.0), V(0, 0, -1)))
        cut = cut.fuse(Part.makeCylinder(OD / 2.0, E2 + 1.0,
                                         V(0, 0, -H / 2.0 - 1.0), V(0, 0, 1)))
        valve = valve.cut(cut)
        merged = valve.removeSplitter()
        fp.Shape = merged if merged.isValid() or not valve.isValid() else valve

        fp.Ports = [
            FreeCAD.Vector(0, 0,  H / 2.0 - E),
            FreeCAD.Vector(0, 0, -H / 2.0 + E2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0,  1),
            FreeCAD.Vector(0, 0, -1),
        ]

    def _execute_sw_th(self, fp, H):
        import math

        OD     = float(fp.OD)
        ODBody = float(fp.ODBody)
        E      = float(fp.E)
        E2     = float(getattr(fp, "E2", 0)) or E

        # ── hexagonal body ─────────────────────────────────────────────────────
        hex_r = (ODBody / 2.0) / math.cos(math.radians(30))
        pts = []
        for i in range(6):
            angle = math.radians(i * 60)
            pts.append(FreeCAD.Vector(hex_r * math.cos(angle),
                                    hex_r * math.sin(angle), 0))
        pts.append(pts[0])
        poly = Part.makePolygon(pts)
        face = Part.Face(poly)
        body = face.extrude(FreeCAD.Vector(0, 0, H))
        body.translate(FreeCAD.Vector(0, 0, -H / 2))

        # ── through bore  (ID = OD - 6 mm) ────────────────────────────────────
        bore_r = (OD - 6.0) / 2.0
        bore   = Part.makeCylinder(bore_r, H,
                                FreeCAD.Vector(0, 0, -H / 2),
                                FreeCAD.Vector(0, 0, 1))
        body = body.cut(bore)

        # ── socket / thread pockets ────────────────────────────────────────────
        sock_r   = OD / 2.0
        sock_pos = Part.makeCylinder(sock_r, E,
                                    FreeCAD.Vector(0, 0,  H / 2),
                                    FreeCAD.Vector(0, 0, -1))
        sock_neg = Part.makeCylinder(sock_r, E2,
                                    FreeCAD.Vector(0, 0, -H / 2),
                                    FreeCAD.Vector(0, 0,  1))
        body = body.cut(sock_pos)
        body = body.cut(sock_neg)

        # ── handle stem ────────────────────────────────────────────────────────
        stem_y0     = ODBody / 2.0
        stem_height = min(25.0, OD)
        stem = Part.makeCylinder(5.0, stem_height,
                                FreeCAD.Vector(0, stem_y0, 0),
                                FreeCAD.Vector(0, 1, 0))

        # ── handle paddle — per-segment extrusions ─────────────────────────────
        # Spine waypoints in the YZ plane:
        #   P0 = (0, py0, -15)
        #   P1 = (0, py0, +15)   segment 0: straight up in Z, length 30
        #   P2 = (0, py1, +30)   segment 1: diagonal (+Y, +Z), length sqrt(2)*15
        #   P3 = (0, py1, pz_end) segment 2: straight up in Z
        #
        # Each segment is extruded as a rectangular prism with cross-section
        # (2*hw) x (2*ht) perpendicular to the segment direction, then fused.
        # It ain't perfect, as it has gaps at the bends in the handle, so maybe fix that when you get a chance
        hw            = min(25.0, OD) / 2.0
        ht            = 1.5                        # half-thickness = 1.5 mm (3 mm total)
        paddle_base_y = stem_y0 + stem_height - 5.0
        py0           = paddle_base_y
        py1           = paddle_base_y + 15.0
        pz_end        = max(50.0, H)

        P0 = FreeCAD.Vector(0, py0, -15.0)
        P1 = FreeCAD.Vector(0, py0,  15.0)
        P2 = FreeCAD.Vector(0, py1,  30.0)
        P3 = FreeCAD.Vector(0, py1,  pz_end)

        def _seg_prism(start, end):
            """Solid rectangular prism from start to end with cross-section 2*hw x 2*ht.
            The cross-section is centered on start, in the plane perpendicular to
            (end - start).  Width (2*hw) lies along the global X axis; thickness
            (2*ht) lies in the perpendicular-to-X direction within that plane.
            """
            seg = end - start
            length = seg.Length
            if length < 1e-6:
                return None
            d = FreeCAD.Vector(seg).normalize()

            # Choose a reference 'up' not parallel to d
            up = FreeCAD.Vector(0, 0, 1)
            if abs(d.dot(up)) > 0.99:
                up = FreeCAD.Vector(0, 1, 0)

            # Two orthogonal in-plane axes
            ax1 = d.cross(up).normalize()   # lies in plane perp to d
            ax2 = d.cross(ax1).normalize()  # lies in plane perp to d, perp to ax1

            # Rectangle corners at start
            c0 = start + ax1 * hw + ax2 * ht
            c1 = start - ax1 * hw + ax2 * ht
            c2 = start - ax1 * hw - ax2 * ht
            c3 = start + ax1 * hw - ax2 * ht
            wire = Part.Wire([
                Part.makeLine(c0, c1),
                Part.makeLine(c1, c2),
                Part.makeLine(c2, c3),
                Part.makeLine(c3, c0),
            ])
            face = Part.Face(wire)
            return face.extrude(d * length)


        prism0 = _seg_prism(P0, P1)
        prism1  = _seg_prism(P1, P2)
        prism2 = _seg_prism(P2, P3)

        handle = prism0
        if prism1:
            handle = handle.fuse(prism1)
        if prism2:
            handle = handle.fuse(prism2)

        handle = self._orientHandle(stem.fuse(handle),
                                    getattr(fp, "Actuator", "Handle"))
        valve = body.fuse(handle)
        valve = valve.removeSplitter()
        fp.Shape = valve

        # ── ports ──────────────────────────────────────────────────────────────
        fp.Ports = [
            FreeCAD.Vector(0, 0,  H / 2 - E),
            FreeCAD.Vector(0, 0, -H / 2 + E2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0,  1),
            FreeCAD.Vector(0, 0, -1),
        ]

    def _execute_legacy(self, fp, H):
        if fp.PRating.lower().find("knife") + 1:
            self._execute_knife_gate(fp, H)
            return
        if fp.PRating.lower().find("pinch") + 1:
            self._execute_pinch(fp, H)
            return

        rating = fp.PRating.lower()

        c = Part.makeCone(fp.ODBody / 2, fp.ODBody / 5, H / 2,
                          FreeCAD.Vector(0, 0, -H / 2))
        v = c.fuse(c.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1)))
        if rating.find("ball") + 1 or rating.find("globe") + 1:
            r = min(H * 0.45, float(fp.ODBody) / 2)
            v = v.fuse(Part.makeSphere(r, FreeCAD.Vector(0, 0, 0)))
        fp.Shape = v
        fp.Ports = [
            FreeCAD.Vector(0, 0, -H / 2),
            FreeCAD.Vector(0, 0,  H / 2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
        ]

    def _execute_knife_gate(self, fp, H):
        """Build a simple wafer-style knife gate valve for legacy CSV rows."""
        import math

        pipe_od = pipe_OD.get(fp.PSize, float(fp.ID))
        bore_d = max(float(fp.ID), pipe_od * 0.9)
        body_d = max(float(fp.ODBody), pipe_od * 1.25)
        gate_t = max(3.0, min(12.0, pipe_od * 0.035))

        body = Part.makeCylinder(
            body_d / 2.0, H,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        bore = Part.makeCylinder(
            bore_d / 2.0, H + 2.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - 1.0),
            FreeCAD.Vector(0, 0, 1),
        )
        body = body.cut(bore)

        # Flat bonnet/packing box across the top of the wafer body.
        bonnet_w = body_d * 0.72
        bonnet_h = max(pipe_od * 0.18, 18.0)
        bonnet = Part.makeBox(
            bonnet_w, bonnet_h, H * 1.12,
            FreeCAD.Vector(-bonnet_w / 2.0, body_d / 2.0 - bonnet_h * 0.25, -H * 0.56),
        )

        # Visible knife gate blade rising through the yoke.
        blade_h = body_d * 0.95
        blade_w = max(bore_d * 0.72, pipe_od * 0.55)
        blade = Part.makeBox(
            blade_w, gate_t, H * 0.45,
            FreeCAD.Vector(-blade_w / 2.0, body_d / 2.0 - gate_t / 2.0, -H * 0.225),
        )
        blade.translate(FreeCAD.Vector(0, blade_h * 0.36, 0))

        stem_r = max(3.0, min(10.0, pipe_od * 0.035))
        stem_base_y = body_d / 2.0 + bonnet_h * 0.35
        stem_h = body_d * 1.2
        stem = Part.makeCylinder(
            stem_r, stem_h,
            FreeCAD.Vector(0, stem_base_y, 0),
            FreeCAD.Vector(0, 1, 0),
        )

        # Two yoke posts and a crosshead frame around the rising stem.
        post_r = max(3.0, stem_r * 0.8)
        post_offset = body_d * 0.24
        post_h = stem_h * 0.72
        post_y0 = body_d / 2.0 + bonnet_h * 0.1
        post1 = Part.makeCylinder(
            post_r, post_h,
            FreeCAD.Vector(-post_offset, post_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        post2 = Part.makeCylinder(
            post_r, post_h,
            FreeCAD.Vector(post_offset, post_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        cross = Part.makeBox(
            post_offset * 2.0 + post_r * 2.0,
            post_r * 2.0,
            max(H * 0.35, gate_t * 2.0),
            FreeCAD.Vector(
                -post_offset - post_r,
                post_y0 + post_h - post_r,
                -max(H * 0.35, gate_t * 2.0) / 2.0,
            ),
        )

        wheel_r = max(pipe_od * 0.32, 32.0)
        wheel_tube_r = max(2.5, wheel_r * 0.06)
        wheel_center = FreeCAD.Vector(0, stem_base_y + stem_h, 0)
        wheel = Part.makeTorus(wheel_r, wheel_tube_r, wheel_center, FreeCAD.Vector(0, 1, 0))
        hub = Part.makeCylinder(
            wheel_tube_r * 1.6, wheel_tube_r * 4.0,
            wheel_center - FreeCAD.Vector(0, wheel_tube_r * 2.0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        spoke_r = max(1.5, wheel_tube_r * 0.45)
        spokes = None
        for angle in (0, 90, 180, 270):
            rad = math.radians(angle)
            direction = FreeCAD.Vector(math.cos(rad), 0, math.sin(rad))
            spoke = Part.makeCylinder(
                spoke_r, wheel_r,
                wheel_center,
                direction,
            )
            spokes = spoke if spokes is None else spokes.fuse(spoke)

        valve = body.fuse(bonnet)
        valve = valve.fuse(blade)
        valve = valve.fuse(stem)
        valve = valve.fuse(post1)
        valve = valve.fuse(post2)
        valve = valve.fuse(cross)
        valve = valve.fuse(wheel)
        valve = valve.fuse(hub)
        if spokes is not None:
            valve = valve.fuse(spokes)
        fp.Shape = valve.removeSplitter()
        fp.Ports = [
            FreeCAD.Vector(0, 0, -H / 2),
            FreeCAD.Vector(0, 0,  H / 2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
        ]

    def _execute_pinch(self, fp, H):
        """Build a simple manual pinch valve for legacy CSV rows."""
        pipe_od = pipe_OD.get(fp.PSize, float(fp.ID))
        bore_d = max(float(fp.ID), pipe_od * 0.9)
        body_d = max(float(fp.ODBody), pipe_od * 1.15)
        flange_t = max(8.0, min(32.0, H * 0.09))

        body = Part.makeCylinder(
            body_d * 0.42, H,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )

        flange_neg = Part.makeCylinder(
            body_d / 2.0, flange_t,
            FreeCAD.Vector(0, 0, -H / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        flange_pos = Part.makeCylinder(
            body_d / 2.0, flange_t,
            FreeCAD.Vector(0, 0, H / 2.0 - flange_t),
            FreeCAD.Vector(0, 0, 1),
        )

        # Flexible sleeve body with a pinched waist under the handwheel.
        sleeve_len = max(1.0, H - 2.0 * flange_t)
        sleeve = Part.makeCylinder(
            body_d * 0.36, sleeve_len,
            FreeCAD.Vector(0, 0, -sleeve_len / 2.0),
            FreeCAD.Vector(0, 0, 1),
        )
        pinch_h = max(pipe_od * 0.16, 8.0)
        pinch_w = body_d * 0.78
        pinch_len = sleeve_len * 0.34
        pinch_cut_top = Part.makeBox(
            pinch_w, pinch_h, pinch_len,
            FreeCAD.Vector(-pinch_w / 2.0, body_d * 0.18, -pinch_len / 2.0),
        )
        pinch_cut_bot = Part.makeBox(
            pinch_w, pinch_h, pinch_len,
            FreeCAD.Vector(-pinch_w / 2.0, -body_d * 0.18 - pinch_h, -pinch_len / 2.0),
        )
        sleeve = sleeve.cut(pinch_cut_top)
        sleeve = sleeve.cut(pinch_cut_bot)

        bore = Part.makeCylinder(
            bore_d / 2.0, H + 2.0,
            FreeCAD.Vector(0, 0, -H / 2.0 - 1.0),
            FreeCAD.Vector(0, 0, 1),
        )

        bonnet_w = body_d * 0.58
        bonnet_h = max(pipe_od * 0.16, 18.0)
        bonnet_l = H * 0.42
        bonnet = Part.makeBox(
            bonnet_w, bonnet_h, bonnet_l,
            FreeCAD.Vector(-bonnet_w / 2.0, body_d * 0.34, -bonnet_l / 2.0),
        )

        stem_r = max(3.0, min(10.0, pipe_od * 0.035))
        stem_y0 = body_d * 0.34 + bonnet_h
        stem_h = body_d * 0.72
        stem = Part.makeCylinder(
            stem_r, stem_h,
            FreeCAD.Vector(0, stem_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )

        yoke_r = max(3.0, stem_r * 0.85)
        yoke_offset = body_d * 0.22
        yoke_h = stem_h * 0.78
        yoke_y0 = body_d * 0.35
        yoke1 = Part.makeCylinder(
            yoke_r, yoke_h,
            FreeCAD.Vector(-yoke_offset, yoke_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        yoke2 = Part.makeCylinder(
            yoke_r, yoke_h,
            FreeCAD.Vector(yoke_offset, yoke_y0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        cross_l = max(H * 0.22, yoke_r * 3.0)
        cross = Part.makeBox(
            yoke_offset * 2.0 + yoke_r * 2.0,
            yoke_r * 2.0,
            cross_l,
            FreeCAD.Vector(-yoke_offset - yoke_r, yoke_y0 + yoke_h - yoke_r, -cross_l / 2.0),
        )

        wheel_r = max(pipe_od * 0.3, 32.0)
        wheel_tube = max(2.5, wheel_r * 0.06)
        wheel_center = FreeCAD.Vector(0, stem_y0 + stem_h, 0)
        wheel = Part.makeTorus(wheel_r, wheel_tube, wheel_center, FreeCAD.Vector(0, 1, 0))
        hub = Part.makeCylinder(
            wheel_tube * 1.6, wheel_tube * 4.0,
            wheel_center - FreeCAD.Vector(0, wheel_tube * 2.0, 0),
            FreeCAD.Vector(0, 1, 0),
        )
        spoke_x = Part.makeCylinder(
            wheel_tube * 0.45, wheel_r * 2.0,
            wheel_center - FreeCAD.Vector(wheel_r, 0, 0),
            FreeCAD.Vector(1, 0, 0),
        )
        spoke_z = Part.makeCylinder(
            wheel_tube * 0.45, wheel_r * 2.0,
            wheel_center - FreeCAD.Vector(0, 0, wheel_r),
            FreeCAD.Vector(0, 0, 1),
        )

        valve = body.fuse(flange_neg)
        valve = valve.fuse(flange_pos)
        valve = valve.fuse(sleeve)
        valve = valve.fuse(bonnet)
        valve = valve.fuse(stem)
        valve = valve.fuse(yoke1)
        valve = valve.fuse(yoke2)
        valve = valve.fuse(cross)
        valve = valve.fuse(wheel)
        valve = valve.fuse(hub)
        valve = valve.fuse(spoke_x)
        valve = valve.fuse(spoke_z)
        valve = valve.cut(bore)
        fp.Shape = valve.removeSplitter()
        fp.Ports = [
            FreeCAD.Vector(0, 0, -H / 2),
            FreeCAD.Vector(0, 0,  H / 2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
        ]

class PypeBranch2(pypeType):  # use AttachExtensionPython
    """Class for object PType="PypeBranch2"
    Single-line pipe branch linked to its center-line using AttachExtensionPython
    ex: a=PypeBranch2(obj,base,DN="DN50",PRating="SCH-STD",OD=60.3,thk=3,BR=None)
      type(obj)=FeaturePython
      type(base)=DWire or SketchObject
    """

    def __init__(self, obj,rating, base, DN="DN50", OD=60.3, thk=3, BR=None):
        # initialize the parent class
        super(PypeBranch2, self).__init__(obj)
        # define common properties
        obj.Proxy = self
        obj.PType = "PypeBranch"
        obj.PSize = DN
        obj.PRating = rating
        # define specific properties
        if FREECADVERSION > 0.19:
            obj.addExtension("App::GroupExtensionPython")
        else:
            obj.addExtension("App::GroupExtensionPython", obj)  # 20220704
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "PypeBranch",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "thk",
            "PypeBranch",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness"),
        ).thk = thk
        if not BR:
            BR = 0.75 * OD
        obj.addProperty(
            "App::PropertyLength",
            "BendRadius",
            "PypeBranch",
            QT_TRANSLATE_NOOP("App::Property", "Bend Radius"),
        ).BendRadius = BR
        obj.addProperty(
            "App::PropertyStringList",
            "Tubes",
            "PypeBranch",
            QT_TRANSLATE_NOOP("App::Property", "The tubes of the branch."),
        )
        obj.addProperty(
            "App::PropertyStringList",
            "Curves",
            "PypeBranch",
            QT_TRANSLATE_NOOP("App::Property", "The curves of the branch."),
        )
        obj.addProperty(
            "App::PropertyLink",
            "Base",
            "PypeBranch",
            QT_TRANSLATE_NOOP("App::Property", "The path."),
        )
        if hasattr(base, "Shape") and base.Shape.Edges:
            obj.Base = base
        else:
            FreeCAD.Console.PrintError("Base not valid\n")

    def onChanged(self, fp, prop):
        if (
            prop == "Base"
            and hasattr(fp, "OD")
            and hasattr(fp, "thk")
            and hasattr(fp, "BendRadius")
        ):
            self.purge(fp)
            self.redraw(fp)
        if prop == "BendRadius" and hasattr(fp, "Curves"):
            BR = fp.BendRadius
            for curve in [FreeCAD.ActiveDocument.getObject(name) for name in fp.Curves]:
                curve.BendRadius = BR
        if prop == "OD" and hasattr(fp, "Tubes") and hasattr(fp, "Curves"):
            OD = fp.OD
            for obj in [FreeCAD.ActiveDocument.getObject(name) for name in fp.Tubes + fp.Curves]:
                if obj.PType == "Elbow":
                    obj.BendRadius = OD * 0.75
                obj.OD = OD
            fp.BendRadius = OD * 0.75
        if prop == "thk" and hasattr(fp, "Tubes") and hasattr(fp, "Curves"):
            thk = fp.thk
            for obj in [FreeCAD.ActiveDocument.getObject(name) for name in fp.Tubes + fp.Curves]:
                if hasattr(obj, "thk"):
                    obj.thk = thk

    def execute(self, fp):
        if len(fp.Tubes) != len(fp.Base.Shape.Edges):
            self.purge(fp)
            self.redraw(fp)
            return

    def redraw(self, fp):
        from math import tan, degrees

        tubes = list()
        curves = list()
        if fp.Base:
            for i in range(len(fp.Base.Shape.Edges)):
                e = fp.Base.Shape.Edges[i]
                L = e.Length
                R = float(fp.BendRadius)
                offset = 0
                # ---Create the tube---
                if i > 0:
                    alfa = e.tangentAt(0).getAngle(fp.Base.Shape.Edges[i - 1].tangentAt(0)) / 2
                    L -= R * tan(alfa)
                    offset = R * tan(alfa)
                if i < (len(fp.Base.Shape.Edges) - 1):
                    alfa = e.tangentAt(0).getAngle(fp.Base.Shape.Edges[i + 1].tangentAt(0)) / 2
                    L -= R * tan(alfa)
                eSupport = "Edge" + str(i + 1)
                t = pCmd.makePipe(fp.PRating,[fp.PSize, float(fp.OD), float(fp.thk), L])
                t.PRating = fp.PRating
                t.PSize = fp.PSize
                t.AttachmentSupport = [(fp.Base, eSupport)]
                t.MapMode = "NormalToEdge"
                t.MapReversed = True
                t.AttachmentOffset = FreeCAD.Placement(
                    FreeCAD.Vector(0, 0, offset), FreeCAD.Rotation()
                )
                tubes.append(t.Name)
                # ---Create the curve---
                if i > 0:
                    e0 = fp.Base.Shape.Edges[i - 1]
                    alfa = degrees(e0.tangentAt(0).getAngle(e.tangentAt(0)))
                    c = pCmd.makeElbow([fp.PSize, float(fp.OD), float(fp.thk), alfa, R])
                    c.PRating = fp.PRating
                    c.PSize = fp.PSize
                    O = "Vertex" + str(i + 1)
                    c.MapReversed = False
                    c.AttachmentSupport = [(fp.Base, O)]
                    c.MapMode = "Translate"
                    pCmd.placeTheElbow(c, e0.tangentAt(0), e.tangentAt(0))
                    curves.append(c.Name)
            fp.Tubes = tubes
            fp.Curves = curves
            objs = [FreeCAD.ActiveDocument.getObject(name) for name in fp.Tubes + fp.Curves]
            # FreeCAD.Console.PrintMessage(objs)
            # fp.addObjects(objs)
            # for obj in objs:
            #     obj.Proxy.execute(obj)

    def purge(self, fp):
        if hasattr(fp, "Tubes"):
            fp.removeObjects([FreeCAD.ActiveDocument.getObject(name) for name in fp.Tubes])
            for name in fp.Tubes:
                FreeCAD.ActiveDocument.removeObject(name)
            fp.Tubes = []
        if hasattr(fp, "Curves"):
            fp.removeObjects([FreeCAD.ActiveDocument.getObject(name) for name in fp.Curves])
            for name in fp.Curves:
                FreeCAD.ActiveDocument.removeObject(name)
            fp.Curves = []

class Gasket(pypeType):
    """Class for object PType="Gasket"
    Pipe(obj, rating, [PSize="DN50", FClass = "150lb", IRID = 55.6, SEID = 69.9, SEOD = 85.9,CROD = 104.9 ,SEthk=4.5, Rthk = 3.2])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      FClass (string): Flange class
      IRID (float): Inner Ring inner diameter
      SEID (float): Sealing element inner diameter
      SEOD (float): Sealing element outer diameter
      CROD (float): Centering ring outer diameter
      SEthk (float): Sealing element thickness
      Rthk (float): Inner and centering ring thickness
      """

    def __init__(self, obj, rating, DN="DN50", FClass = "150lb", IRID = 55.6, SEID = 69.9, SEOD = 85.9,CROD = 104.9 ,SEthk=4.5, Rthk = 3.2):
        # initialize the parent class
        super(Gasket, self).__init__(obj)
        # define common properties
        obj.PType = "Gasket"
        obj.Proxy = self
        obj.PRating = rating #note that gaskets do not have a typical pipe schedule, but we will use this to match the other pipe objects. rating will equal flange class
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyString",
            "FClass",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Flange class / pressure rating"),
        ).FClass = FClass
        obj.addProperty(
            "App::PropertyLength",
            "IRID",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Inner ring inner diameter"),
        ).IRID = IRID
        obj.addProperty(
            "App::PropertyLength",
            "SEID",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Sealing element inner diameter"),
        ).SEID = SEID
        obj.addProperty(
            "App::PropertyLength",
            "SEOD",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Sealing element outer diameter"),
        ).SEOD = SEOD
        obj.addProperty(
            "App::PropertyLength",
            "CROD",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Centering ring outer diameter"),
        ).CROD = CROD
        obj.addProperty(
            "App::PropertyLength",
            "SEthk",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Sealing element thickness"),
        ).SEthk = SEthk
        obj.addProperty(
            "App::PropertyLength",
            "Rthk",
            "Gasket",
            QT_TRANSLATE_NOOP("App::Property", "Inner and centering ring thickness"),
        ).Rthk = Rthk

        self.execute(obj)

    def onChanged(self, fp, prop):
        # Sealing element must be thicker than or equal to the rings
        if prop == "Rthk" and hasattr(fp, "SEthk") and fp.Rthk > fp.SEthk:
            FreeCAD.Console.PrintError(
                "Gasket: Ring thickness (Rthk) must not exceed sealing element "
                "thickness (SEthk)\n"
            )
        return None

    def execute(self, fp):
        # Validate dimensions before attempting geometry construction
        if not (fp.IRID > 0 and fp.SEID > fp.IRID and fp.SEOD > fp.SEID
                and fp.CROD > fp.SEOD and fp.SEthk > 0 and fp.Rthk > 0):
            FreeCAD.Console.PrintError(
                "Gasket: invalid dimensions -- shape not updated\n"
            )
            return

        # Ring vertical offset so all three rings are centered on the mid-plane
        # The sealing element spans 0 -> SEthk.
        # The thinner rings are centered at SEthk/2.
        ring_offset = (float(fp.SEthk) - float(fp.Rthk)) / 2.0

        # Inner ring: IRID/2 -> SEID/2, height Rthk, centered vertically
        inner_ring = Part.makeCylinder(
            fp.SEID / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), vZ
        ).cut(
            Part.makeCylinder(
                fp.IRID / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), vZ
            )
        )

        # Sealing element: SEID/2 -> SEOD/2, height SEthk
        sealing_element = Part.makeCylinder(
            fp.SEOD / 2, fp.SEthk, vO, vZ
        ).cut(
            Part.makeCylinder(fp.SEID / 2, fp.SEthk, vO, vZ)
        )

        # Centering ring: SEOD/2 -> CROD/2, height Rthk, centered vertically
        centering_ring = Part.makeCylinder(
            fp.CROD / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), vZ
        ).cut(
            Part.makeCylinder(
                fp.SEOD / 2, fp.Rthk, FreeCAD.Vector(0, 0, ring_offset), vZ
            )
        )

        gasket = inner_ring.fuse(sealing_element).fuse(centering_ring)
        gasket = gasket.removeSplitter()
        fp.Shape = gasket

        # Ports at each face of the sealing element, pointing outward
        fp.Ports = [
            FreeCAD.Vector(0, 0, 0),
            FreeCAD.Vector(0, 0, float(fp.SEthk)),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0, 1),
        ]

        super(Gasket, self).execute(fp)  # perform common operations


class Bolts_Nuts(pypeType):
    """Class for object PType="Bolts_Nuts"
    Bolts_Nuts(obj, rating, [PSize="DN50", FClass="150lb",
               dBolt=15.875, dNut=31.1658, tNut=16.0274,
               df=120.65, n=4, lBolt=76.9548, SEthk=4.5])
      obj    : the "App::FeaturePython" object
      rating : flange class string (e.g. "150lb" or "300lb")
      PSize  : nominal diameter string (e.g. "DN50")
      FClass : flange class / pressure rating
      dBolt  : stud bolt cylinder outer diameter (mm)
      dNut   : hex nut circumscribed circle outer diameter (mm)
      tNut   : hex nut extruded length (mm)
      df     : bolt center distance from flange centerline (mm)
      n      : number of bolts per flange
      lBolt  : bolt length (mm)
      SEthk  : sealing element thickness from the matching gasket (mm)
    """

    def __init__(self, obj, rating, DN="DN50", FClass="150lb",
                 dBolt=15.875, dNut=31.1658, tNut=16.0274,
                 df=120.65, n=4, lBolt=76.9548, SEthk=4.5):
        # initialize the parent class
        super(Bolts_Nuts, self).__init__(obj)
        # define common properties
        obj.PType = "Bolts_Nuts"
        obj.Proxy = self
        # PRating stores the flange class so port-alignment helpers work
        obj.PRating = rating
        obj.PSize = DN
        # define specific properties
        obj.addProperty(
            "App::PropertyString",
            "FClass",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property", "Flange class / pressure rating"),
        ).FClass = FClass
        obj.addProperty(
            "App::PropertyLength",
            "dBolt",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property", "Stud bolt outer diameter"),
        ).dBolt = dBolt
        obj.addProperty(
            "App::PropertyLength",
            "dNut",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property",
                              "Hex nut circumscribed circle outer diameter"),
        ).dNut = dNut
        obj.addProperty(
            "App::PropertyLength",
            "tNut",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property", "Hex nut extruded length"),
        ).tNut = tNut
        obj.addProperty(
            "App::PropertyLength",
            "df",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property",
                              "Bolt center distance from flange centerline"),
        ).df = df
        obj.addProperty(
            "App::PropertyInteger",
            "n",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property", "Number of bolts per flange"),
        ).n = n
        obj.addProperty(
            "App::PropertyLength",
            "lBolt",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property", "Bolt length"),
        ).lBolt = lBolt
        obj.addProperty(
            "App::PropertyLength",
            "SEthk",
            "Bolts_Nuts",
            QT_TRANSLATE_NOOP("App::Property",
                              "Sealing element thickness of the matching gasket"),
        ).SEthk = SEthk

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        from math import cos, sin, pi

        # Retrieve scalar values from FreeCAD property quantities
        dBolt  = float(fp.dBolt)
        dNut   = float(fp.dNut)
        tNut   = float(fp.tNut)
        df     = float(fp.df)
        n      = int(fp.n)
        lBolt  = float(fp.lBolt)
        SEthk  = float(fp.SEthk)

        # Validate dimensions
        if not (dBolt > 0 and dNut > 0 and tNut > 0 and df > 0
                and n > 0 and lBolt > 0 and SEthk > 0):
            FreeCAD.Console.PrintError(
                "Bolts_Nuts: invalid dimensions -- shape not updated\n"
            )
            return

        # Bolts are centered axially on the gasket mid-plane (0, 0, SEthk/2).
        # The bolt cylinder spans from z = SEthk/2 - lBolt/2
        #                           to z = SEthk/2 + lBolt/2.
        bolt_z_center = 0.0 #SEthk / 2.0
        bolt_z_base   = bolt_z_center - lBolt / 2.0  # bottom of bolt cylinder

        # Bolt angular pitch: first bolt is aligned with flange hole convention.
        # The flange execute() starts the first hole at angle (360/n/2) degrees
        # and then steps by (360/n) degrees.  We replicate that pattern so bolts
        # sit at the same angular positions as the flange holes.
        start_angle = (2.0 * pi / n) / 2.0        # half-step offset, radians
        step_angle  = 2.0 * pi / n                 # radians between bolts

        # Nut geometry: a regular hexagon with circumscribed circle radius dNut/2.
        # Build one hexagon wire centered at origin in the XY plane.
        def make_hex_wire(center, r):
            """Return a closed hexagonal Part.Wire centered at 'center'
               with circumscribed radius r in the XY plane."""
            pts = [
                FreeCAD.Vector(
                    center.x + r * cos(2.0 * pi * k / 6),
                    center.y + r * sin(2.0 * pi * k / 6),
                    center.z,
                )
                for k in range(6)
            ]
            pts.append(pts[0])  # close the polygon
            return Part.makePolygon(pts)

        bolt_solids = []

        for i in range(n):
            angle = start_angle + i * step_angle

            # Center of this bolt in the XY plane
            cx = (df / 2.0) * cos(angle)
            cy = (df / 2.0) * sin(angle)

            # --- Bolt cylinder ---
            bolt_base_pt = FreeCAD.Vector(cx, cy, bolt_z_base)
            bolt_cyl = Part.makeCylinder(
                dBolt / 2.0,
                lBolt,
                bolt_base_pt,
                vZ,
            )

            # --- Bottom nut ---
            # Outer face sits 1 mm inward from the bolt bottom (at bolt_z_base + 1.0).
            # The nut body extends inward (toward +Z) by tNut, overlapping the bolt.
            # Extrusion base is at the outer face; extrude in +Z direction.
            nut_bot_outer = bolt_z_base + 1.0
            hex_wire_bot = make_hex_wire(
                FreeCAD.Vector(cx, cy, nut_bot_outer), dNut / 2.0
            )
            hex_face_bot = Part.Face(Part.Wire(hex_wire_bot))
            nut_bot = hex_face_bot.extrude(FreeCAD.Vector(0, 0, tNut))

            # --- Top nut ---
            # Outer face sits 1 mm inward from the bolt top (at bolt_z_base + lBolt - 1.0).
            # The nut body extends inward (toward -Z) by tNut, overlapping the bolt.
            # Extrusion base is tNut below the outer face; extrude in +Z direction.
            nut_top_outer = bolt_z_base + lBolt - 1.0
            nut_top_base  = nut_top_outer - tNut
            hex_wire_top = make_hex_wire(
                FreeCAD.Vector(cx, cy, nut_top_base), dNut / 2.0
            )
            hex_face_top = Part.Face(Part.Wire(hex_wire_top))
            nut_top = hex_face_top.extrude(FreeCAD.Vector(0, 0, tNut))

            # Fuse this bolt's three solids together
            bolt_assembly = bolt_cyl.fuse(nut_bot).fuse(nut_top)
            bolt_solids.append(bolt_assembly)

        # Fuse all bolts into one compound shape
        if len(bolt_solids) == 1:
            shape = bolt_solids[0]
        else:
            shape = bolt_solids[0]
            for s in bolt_solids[1:]:
                shape = shape.fuse(s)
        #shape = shape.removeSplitter()
        fp.Shape = shape

        # Ports at the gasket faces (same convention as Gasket class)
        fp.Ports = [
            FreeCAD.Vector(0, 0, -float(fp.SEthk) / 2),
            FreeCAD.Vector(0, 0,  float(fp.SEthk) / 2),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
        ]

        super(Bolts_Nuts, self).execute(fp)  # perform common operations


class Outlet(pypeType):
    """
    Class for object PType="Outlet"

    Models integrally-reinforced branch connections that attach to the face of a run pipe, tee orelbow.

    Outlet(obj, rating, DN, OD, thk, A, B,
           endType="ButtWeld", angle=0, E=0)

    Parameters
    ----------
    obj       : App::FeaturePython object
    rating    : string  schedule (ButtWeld) or class (SocketWeld / Threaded)
    DN        : string  nominal size  e.g. "DN50"
    OD        : float   outside diameter at the pipe-connection end
    thk       : float   wall thickness at the pipe-connection end
    A         : float   height of the fitting above the run-pipe surface
                         (measured along the fitting axis)
    B         : float   outer diameter at the base (run-pipe attachment)
    endType   : "ButtWeld" | "SocketWeld" | "Threaded" (CSV Conn BW / SW / TH)
    angle     : 0 (straight)  |  45 (lateral/elbow)
    E         : float   height of the socket / thread bottom (SocketWeld and
                         Threaded); the port sits here

    Coordinate convention (local, before placement)
    ------------------------------------------------
    Origin  = the point where the fitting axis pierces the run-pipe surface.
    +Z      = outward along the fitting axis.
    Port[0] is at (0, 0, A) for straight, (0, A/√2, A/√2) for 45-degree.
    Port direction faces outward from the fitting end.

    For a 45-degree (lateral) variant the entire body is built straight then
    rotated 45° around the local X-axis, and the portion below z=0 is removed
    by a boolean cut with a half-space solid, leaving the elliptical base that
    sits on the run-pipe surface.
    """

    def __init__(
        self,
        obj,
        rating    = "Sch-STD",
        DN        = "DN50",
        OD        = 60.32,
        thk       = 3.91,
        A         = 45.0,
        B         = 70.0,
        endType   = "ButtWeld",
        angle     = 0,
        E         = 0.0,
        carrierOD = 0.0,
    ):
        super(Outlet, self).__init__(obj)

        obj.PType   = "Outlet"
        obj.Proxy   = self
        obj.PRating = rating
        obj.PSize   = DN

        # ── Geometry properties ───────────────────────────────────────────
        obj.addProperty(
            "App::PropertyLength", "OD", "Outlet",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter at pipe end"),
        ).OD = OD

        obj.addProperty(
            "App::PropertyLength", "thk", "Outlet",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness at pipe end"),
        ).thk = thk

        obj.addProperty(
            "App::PropertyLength", "A", "Outlet",
            QT_TRANSLATE_NOOP("App::Property",
                "Height above run-pipe surface (along fitting axis)"),
        ).A = A

        obj.addProperty(
            "App::PropertyLength", "B", "Outlet",
            QT_TRANSLATE_NOOP("App::Property", "Outer diameter at base attachment"),
        ).B = B

        obj.addProperty(
            "App::PropertyLength", "E", "Outlet",
            QT_TRANSLATE_NOOP("App::Property",
                "Socket depth  bore steps from ID to OD at this height "
                "(SocketWeld and Threaded only)"),
        ).E = E if E else 0.0

        obj.addProperty(
            "App::PropertyLength", "CarrierOD", "Outlet",
            QT_TRANSLATE_NOOP("App::Property",
                "Outer diameter of the carrier (run) pipe.  When non-zero the "
                "base of the fitting is shaped to lie flush against the carrier "
                "pipe surface rather than being cut flat."),
        ).CarrierOD = carrierOD if carrierOD else 0.0

        # ── Type / style ──────────────────────────────────────────────────
        obj.addProperty(
            "App::PropertyString", "EndType", "Outlet",
            QT_TRANSLATE_NOOP("App::Property",
                "ButtWeld (tapered body), SocketWeld or Threaded (cylindrical body)"),
        ).EndType = endType

        obj.addProperty(
            "App::PropertyInteger", "Angle", "Outlet",
            QT_TRANSLATE_NOOP("App::Property",
                "Branch angle: 0 = straight, "
                "45 = lateral "),
        ).Angle = int(angle)

        obj.addProperty(
            "App::PropertyString", "Profile", "Outlet",
            QT_TRANSLATE_NOOP("App::Property", "Section dimensions"),
        ).Profile = str(OD) + "x" + str(thk)

        self.execute(obj)

    # ------------------------------------------------------------------
    def onChanged(self, fp, prop):
        return None

    # ------------------------------------------------------------------
    def onChanged(self, fp, prop):
        return None

    # ------------------------------------------------------------------
    def execute(self, fp):
        import math

        OD        = float(fp.OD)
        thk       = float(fp.thk)
        A         = float(fp.A)
        B         = float(fp.B)
        E         = float(fp.E)
        endType   = str(fp.EndType)
        angle     = int(fp.Angle)
        carrierOD = float(fp.CarrierOD) if hasattr(fp, "CarrierOD") else 0.0

        ID   = OD - 2.0 * thk          # inner diameter at the pipe end
        r_id = ID / 2.0
        r_od = OD / 2.0
        r_B  = B  / 2.0                # base radius

        fp.Profile = str(OD) + "x" + str(thk)

        # ── 1. Build the body in the "straight" (upright) orientation ──────
        #
        # When carrierOD is provided we always extend the body below z=0 so
        # that we have material to subtract the carrier-pipe cylinder from.
        # The cylinder cutter has radius = carrierOD/2, its axis runs along
        # local X, and its centre is placed at z = -(carrierOD/2).  Any
        # material below the deepest point of that cylinder is trimmed away
        # by keeping only the half-space z >= -(carrierOD/2) after the cut.
        #
        # For a 45-degree lateral the body must also extend downward so that
        # rotating 45° around X and clipping at z=0 yields a full ellipse.

        use_carrier_cut = (carrierOD > 0.0)

        if angle == 45:
            if use_carrier_cut:
                # After rotating 45° around X the pre-rotation base cap at
                # z = -h_ext maps to z_world = -h_ext * cos45.  We need that
                # to lie at or below -(r_carrier) so the carrier-pipe cutter
                # removes the entire protrusion:
                #   h_ext * cos45  >=  r_carrier
                #   h_ext          >=  r_carrier / cos45  =  r_carrier * sqrt2
                # Add the original tan45 term (= r_B) on top so the elliptical
                # base is also fully formed before the cut.
                r_carrier_pre = (carrierOD / 2.0)
                h_ext = r_B * math.tan(math.radians(45)) + r_carrier_pre * math.sqrt(2.0)
            else:
                h_ext = r_B * math.tan(math.radians(angle))
        elif use_carrier_cut:
            # Extend by the carrier radius so the cutter can reach through
            h_ext = carrierOD / 2.0
        else:
            h_ext = 0.0

        if endType in ("ButtWeld", "BW"):
            if angle == 45 or use_carrier_cut:
                # Constant-radius extension below z=0, then cone upward
                ext_cyl = Part.makeCylinder(r_B, h_ext + 0.5,
                                            FreeCAD.Vector(0, 0, -(h_ext + 0.5)),
                                            FreeCAD.Vector(0, 0, 1))
                cone    = Part.makeCone(r_B, r_od, A,
                                        FreeCAD.Vector(0, 0, 0),
                                        FreeCAD.Vector(0, 0, 1), 360)
                outer   = ext_cyl.fuse(cone)
            else:
                outer = Part.makeCone(r_B, r_od, A,
                                      FreeCAD.Vector(0, 0, 0),
                                      FreeCAD.Vector(0, 0, 1), 360)

            # Inner bore: constant ID through the full height
            inner = Part.makeCylinder(r_id, A + h_ext + 1.0,
                                      FreeCAD.Vector(0, 0, -(h_ext + 0.5)),
                                      FreeCAD.Vector(0, 0, 1))
            body = outer.cut(inner)

        else:  # SocketWeld / SW, Threaded / TH
            # Outer shell: cylinder from -(h_ext) to A
            outer = Part.makeCylinder(r_B, A + h_ext,
                                      FreeCAD.Vector(0, 0, -h_ext),
                                      FreeCAD.Vector(0, 0, 1))

            # Inner bore: narrow (ID) from -h_ext to E, then wide (r_od) from E to A
            E_clamped = min(E, A - 0.5) if E > 0 else A * 0.3
            bore_narrow = Part.makeCylinder(r_id, E_clamped + h_ext + 0.5,
                                            FreeCAD.Vector(0, 0, -(h_ext + 0.5)),
                                            FreeCAD.Vector(0, 0, 1))
            bore_wide   = Part.makeCylinder(r_od, A - E_clamped + 0.5,
                                            FreeCAD.Vector(0, 0, E_clamped),
                                            FreeCAD.Vector(0, 0, 1))
            body = outer.cut(bore_narrow).cut(bore_wide)

        # ── 2. Handle the 45-degree lateral variant ─────────────────────────
        #
        # Rotate 45° around X, then clip at z >= 0 (flat base).
        # If carrierOD is also set the flat clip is replaced by the carrier
        # cylinder cut in step 3 below; we still rotate first.

        if angle == 45:
            body.rotate(FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(1, 0, 0), 45)
            if not use_carrier_cut:
                # Standard flat clip at z=0
                big  = max(B, A) * 4.0
                clip = Part.makeBox(2 * big, 2 * big, big + 1.0,
                                    FreeCAD.Vector(-big, -big, 0))
                body = body.common(clip)

        # ── 3. Carrier-pipe cylindrical base cut ─────────────────────────────
        #
        # When carrierOD is supplied we carve the fitting base so that it sits
        # flush on the outside of the carrier pipe.
        #
        # The carrier pipe surface, in the outlet's local coordinate system, is
        # a cylinder of radius r_carrier whose axis runs along local X and whose
        # centre is at (x=0, y=0, z=-(r_carrier)).  We cut this cylinder through
        # the body, then trim away anything below z = -(r_carrier) with a
        # half-space keeper so the solid remains bounded.

        if use_carrier_cut:
            r_carrier = carrierOD / 2.0
            big       = max(B, A, carrierOD) * 4.0

            # Carrier-pipe cutter: a cylinder running along Y (the carrier pipe
            # run axis in the outlet's local frame).
            #
            # For a straight fitting the body spans ±r_B in Y, so r_B*2 + 2
            # is sufficient.  For the 45° lateral, after rotation the body
            # extends in Y by up to (h_ext + A) * sin45 on each side, so the
            # cutter must be long enough to span that full extent.
            if angle == 45:
                s2 = math.sqrt(2.0) / 2.0
                y_span = (h_ext + A) * s2
                cutter_len = y_span * 2.0 + 2.0
            else:
                cutter_len = r_B * 2.0 + 2.0

            carrier_cyl = Part.makeCylinder(
                r_carrier,
                cutter_len,
                FreeCAD.Vector(0, -cutter_len / 2.0, -r_carrier),
                FreeCAD.Vector(0, 1, 0),   # axis along Y
            )
            body = body.cut(carrier_cyl)

            # Trim the dangling material below the deepest cut point
            keeper = Part.makeBox(2 * big, 2 * big, big,
                                  FreeCAD.Vector(-big, -big, -r_carrier))
            body = body.common(keeper)

        fp.Shape = body

        # ── 4. Set port ──────────────────────────────────────────────────────
        #
        # The single port is at the open pipe-connection end (top).
        # Direction faces outward (away from the body).
        if angle == 45:
            s2 = math.sqrt(2.0) / 2.0
            if endType in ("SocketWeld", "SW", "Threaded", "ThreadedEnd", "TH"):
                E_clamped = min(E, A - 0.5) if E > 0 else A * 0.3
                port_pos = FreeCAD.Vector(0, -E_clamped * s2, E_clamped * s2)
            else:
                port_pos = FreeCAD.Vector(0, -A * s2, A * s2)
            port_dir = FreeCAD.Vector(0, -s2, s2)
        else:
            if endType in ("SocketWeld", "SW", "Threaded", "ThreadedEnd", "TH"):
                E_clamped = min(E, A - 0.5) if E > 0 else A * 0.3
                port_pos = FreeCAD.Vector(0, 0, E_clamped)
            else:
                port_pos = FreeCAD.Vector(0, 0, A)
            port_dir = FreeCAD.Vector(0, 0, 1)

        fp.Ports          = [port_pos]
        fp.PortDirections = [port_dir]

        super(Outlet, self).execute(fp)   # positionBySupport()

class SocketCap(pypeType):
    """  
    SocketCap(obj, [PSize="DN25", OD=33.4, A=26.0,C=5.0,E=13.0,Conn="SW"])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      OD (float): Connecting pipe outside diameter
      BendAngle (float): Bend angle
      A (float): Cap height
      C (float): Wall thickness in socket
      E (float): Socket depth
      Conn (string): Connection type (SW=Socket Weld, TH=Threaded)

    """
    def __init__(self, obj, PSize="DN25", OD=33.4, A=26.0,C=5.0,E=13.0,Conn="SW"):
        super(SocketCap, self).__init__(obj)
        obj.Proxy = self
        obj.PType = "SocketCap"
        obj.PRating = "3000lb"
        obj.PSize = PSize
        # define specific properties
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "SocketCap",
            QT_TRANSLATE_NOOP("App::Property", "Pipe OD"),
        ).OD = OD       
        obj.addProperty(
            "App::PropertyLength",
            "A",
            "SocketCap",
            QT_TRANSLATE_NOOP("App::Property", "Cap height"),
        ).A = A
        obj.addProperty(
            "App::PropertyLength",
            "C",
            "SocketCap",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness in socket"),
        ).C = C

        obj.addProperty(
            "App::PropertyLength",
            "E",
            "SocketCap",
            QT_TRANSLATE_NOOP("App::Property", "Socket depth"),
        ).E = E
        obj.addProperty(
            "App::PropertyString",
            "Conn",
            "SocketCap",
            QT_TRANSLATE_NOOP("App::Property", "Connection type (SW=Socket Weld, TH=Threaded)"),
        ).Conn = Conn
        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):

        base = Part.makeCylinder(float(fp.C)+float(fp.OD)/2, fp.A, FreeCAD.Vector(0, 0, -float(fp.E)), FreeCAD.Vector(0, 0,1)) 
 
        socket = Part.makeCylinder(float(fp.OD)/2, float(fp.E), FreeCAD.Vector(0, 0, -float(fp.E)), FreeCAD.Vector(0, 0,1))

        base = base.cut(socket)

        fp.Shape = base   

        fp.Ports = [ FreeCAD.Vector(0,0, 0)]
        fp.PortDirections = [FreeCAD.Vector(0,0,-1)]
        super(SocketCap, self).execute(fp)  # perform common operations

class SocketCoupling(pypeType):
    """
    SocketCoupling(obj, [PSize="DN25", PSize2="DN25", OD=33.4, OD2=33.4,
                         A=35.0, C=5.0, D=25.9, E=22.0, Conn="SW"])
      obj     : the "App::FeaturePython" object
      PSize   (string): nominal diameter of port 0 (run end, -Z)
      PSize2  (string): nominal diameter of port 1 (opposite end, +Z)
      OD      (float):  port 0 pipe outside diameter
      OD2     (float):  port 1 pipe outside diameter
      A       (float):  half-length of coupling (center to outer edge)
      C       (float):  socket boss wall thickness (port 0 end)
      D       (float):  bore diameter at centre of fitting
      E       (float):  socket depth (pipe insertion depth)
      Conn    (string): connection type (SW=Socket Weld, TH=Threaded)

    Local coordinate system
    ───────────────────────
      Axis  : Z
      Port 0: at z = -(A-E), outward direction -Z  (port 0 pipe end)
      Port 1: at z = +(A-E), outward direction +Z  (port 1 pipe end)
      Origin: centre of the coupling body
    """

    def __init__(self, obj,
                 PSize="DN25", PSize2="DN25",
                 OD=33.4, OD2=33.4,
                 A=35.0, C=5.0, D=25.9, E=22.0,
                 Conn="SW"):
        # ── parent class ─────────────────────────────────────────────────────
        super(SocketCoupling, self).__init__(obj)

        # ── common pype properties ────────────────────────────────────────────
        obj.Proxy   = self
        obj.PType   = "SocketCoupling"
        obj.PRating = "3000lb"
        obj.PSize   = PSize

        # ── specific properties ───────────────────────────────────────────────
        obj.addProperty(
            "App::PropertyString",
            "PSize2",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Nominal diameter of port 1"),
        ).PSize2 = PSize2

        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Port 0 pipe OD"),
        ).OD = OD

        obj.addProperty(
            "App::PropertyLength",
            "OD2",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Port 1 pipe OD"),
        ).OD2 = OD2

        obj.addProperty(
            "App::PropertyLength",
            "A",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Half-length (center to outer edge)"),
        ).A = A

        obj.addProperty(
            "App::PropertyLength",
            "C",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Socket boss wall thickness"),
        ).C = C

        obj.addProperty(
            "App::PropertyLength",
            "D",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Bore diameter at centre"),
        ).D = D

        obj.addProperty(
            "App::PropertyLength",
            "E",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property", "Socket depth"),
        ).E = E

        obj.addProperty(
            "App::PropertyString",
            "Conn",
            "SocketCoupling",
            QT_TRANSLATE_NOOP("App::Property",
                              "Connection type (SW=Socket Weld, TH=Threaded)"),
        ).Conn = Conn

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        OD  = float(fp.OD)
        OD2 = float(fp.OD2)
        A   = float(fp.A)
        C   = float(fp.C)
        D   = float(fp.D)
        E   = float(fp.E)

        # ── outer body ────────────────────────────────────────────────────────
        # Main cylinder: full length, outer radius = OD/2 + C
        base = Part.makeCylinder(
            OD / 2 + C, A * 2,
            FreeCAD.Vector(0, 0, -A), FreeCAD.Vector(0, 0, 1))

        # ── internal cutouts ──────────────────────────────────────────────────
        # Central bore (D is bore diameter, so radius = D/2. 
        # If a reducing coupling is used, the center bore may need to be narrower than the default (maximum 6 mm narrower than OD2))
        D = min(D, OD2 - 6.0)
        bore = Part.makeCylinder(
            D / 2, A * 2,
            FreeCAD.Vector(0, 0, -A), FreeCAD.Vector(0, 0, 1))

        # Socket 0: pipe OD/2 socket pocket opening from the -Z face, depth E
        socket1 = Part.makeCylinder(
            OD / 2, E,
            FreeCAD.Vector(0, 0, -A), FreeCAD.Vector(0, 0, 1))

        # Socket 1: pipe OD2/2 socket pocket opening from the +Z face, depth E
        socket2 = Part.makeCylinder(
            OD2 / 2, E,
            FreeCAD.Vector(0, 0, A), FreeCAD.Vector(0, 0, -1))

        base = base.cut(bore)
        base = base.cut(socket1)
        base = base.cut(socket2)

        fp.Shape = base

        # ── ports ─────────────────────────────────────────────────────────────
        # Ports sit at the bottom of each socket pocket (where the pipe end rests)
        fp.Ports = [
            FreeCAD.Vector(0, 0, -A + E),   # port 0: inside socket 0
            FreeCAD.Vector(0, 0,  A - E),   # port 1: inside socket 1
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),        # port 0 outward: -Z
            FreeCAD.Vector(0, 0,  1),        # port 1 outward: +Z
        ]
        super(SocketCoupling, self).execute(fp)  # perform common operations


class SocketUnion(pypeType):
    """
    SocketUnion(obj, [PSize="DN25", OD=33.4, A=35.0, C=5.0, D=25.9, E=22.0, Conn="SW"])
      obj   : the "App::FeaturePython" object
      PSize (string): nominal diameter (both ports identical)
      OD    (float):  pipe outside diameter
      A     (float):  half-length (center to outer edge of assembled union)
      C     (float):  socket boss wall thickness
      D     (float):  bore diameter
      E     (float):  socket depth
      Conn  (string): connection type (SW=Socket Weld, TH=Threaded)

    Local coordinate system
    ───────────────────────
      Axis  : Z
      Port 0: at z = -(A-E), outward direction -Z
      Port 1: at z = +(A-E), outward direction +Z
      Origin: center of the union body
    """

    def __init__(self, obj,
                 PSize="DN25", OD=33.4, A=35.0, C=5.0, D=25.9, E=22.0,
                 Conn="SW"):
        # ── parent class ─────────────────────────────────────────────────────
        super(SocketUnion, self).__init__(obj)

        # ── common pype properties ────────────────────────────────────────────
        obj.Proxy   = self
        obj.PType   = "SocketUnion"
        obj.PRating = "3000lb"
        obj.PSize   = PSize

        # ── specific properties ───────────────────────────────────────────────
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "SocketUnion",
            QT_TRANSLATE_NOOP("App::Property", "Pipe OD"),
        ).OD = OD

        obj.addProperty(
            "App::PropertyLength",
            "A",
            "SocketUnion",
            QT_TRANSLATE_NOOP("App::Property", "Half-length (centre to outer edge)"),
        ).A = A

        obj.addProperty(
            "App::PropertyLength",
            "C",
            "SocketUnion",
            QT_TRANSLATE_NOOP("App::Property", "Socket boss wall thickness"),
        ).C = C

        obj.addProperty(
            "App::PropertyLength",
            "D",
            "SocketUnion",
            QT_TRANSLATE_NOOP("App::Property", "Bore diameter"),
        ).D = D

        obj.addProperty(
            "App::PropertyLength",
            "E",
            "SocketUnion",
            QT_TRANSLATE_NOOP("App::Property", "Socket depth"),
        ).E = E

        obj.addProperty(
            "App::PropertyString",
            "Conn",
            "SocketUnion",
            QT_TRANSLATE_NOOP("App::Property",
                              "Connection type (SW=Socket Weld, TH=Threaded)"),
        ).Conn = Conn

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        OD  = float(fp.OD)
        A   = float(fp.A)
        C   = float(fp.C)
        D   = float(fp.D)
        E   = float(fp.E)

        bossR = OD / 2 + C   # outer radius of body / socket boss

        # ── outer body ────────────────────────────────────────────────────────
        # Plain cylinder base (same shape as coupling)
        base = Part.makeCylinder(
            bossR, A * 2,
            FreeCAD.Vector(0, 0, -A), FreeCAD.Vector(0, 0, 1))

        # Octagonal center collar — a regular 8-sided prism in the XY plane,
        # circumradius = bossR * 1.5, height = A*2/3, centred at z=0.
        octR   = bossR * 1.5
        octH   = A * 2 / 3
        import math
        n = 8
        pts = []
        for i in range(n):
            angle = math.radians(i * 360.0 / n)
            pts.append(FreeCAD.Vector(octR * math.cos(angle),
                                      octR * math.sin(angle), 0))
        # Close the polygon
        pts.append(pts[0])
        poly  = Part.makePolygon(pts)
        face  = Part.Face(poly)
        # Extrude symmetrically ±octH/2 about z=0
        octSolid = face.extrude(FreeCAD.Vector(0, 0, octH))
        octSolid.translate(FreeCAD.Vector(0, 0, -octH / 2))

        base = base.fuse(octSolid)

        # ── internal cutouts ──────────────────────────────────────────────────
        # Central bore (D is bore diameter, radius = D/2)
        bore = Part.makeCylinder(
            D / 2, A * 2,
            FreeCAD.Vector(0, 0, -A), FreeCAD.Vector(0, 0, 1))

        # Socket 0: opens from -Z face, depth E
        socket1 = Part.makeCylinder(
            OD / 2, E,
            FreeCAD.Vector(0, 0, -A), FreeCAD.Vector(0, 0, 1))

        # Socket 1: opens from +Z face, depth E
        socket2 = Part.makeCylinder(
            OD / 2, E,
            FreeCAD.Vector(0, 0, A), FreeCAD.Vector(0, 0, -1))

        base = base.cut(bore)
        base = base.cut(socket1)
        base = base.cut(socket2)

        fp.Shape = base

        # ── ports ─────────────────────────────────────────────────────────────
        fp.Ports = [
            FreeCAD.Vector(0, 0, -A + E),
            FreeCAD.Vector(0, 0,  A - E),
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
        ]
        super(SocketUnion, self).execute(fp)  # perform common operations


def _hexPrism(across_flats, height, z0):
    """Regular hexagonal prism on the Z axis, flats `across_flats` apart,
    from z0 to z0 + height."""
    import math
    r = (across_flats / 2.0) / math.cos(math.radians(30))
    pts = [FreeCAD.Vector(r * math.cos(math.radians(i * 60)),
                          r * math.sin(math.radians(i * 60)), z0)
           for i in range(6)]
    pts.append(pts[0])
    return Part.Face(Part.makePolygon(pts)).extrude(FreeCAD.Vector(0, 0, height))


class HexBushing(pypeType):
    """
    HexBushing(obj, [PSize="DN25", PSize2="DN15", OD=33.4, OD2=21.34,
                     F=35.0, C=6.0, L=19.0, L2=10.84, D=15.34, Conn="TH"])
      obj     : the "App::FeaturePython" object
      PSize   (string): nominal diameter of the male (large) end, port 0
      PSize2  (string): nominal diameter of the female (small) end, port 1
      OD      (float):  large pipe OD (male thread OD)
      OD2     (float):  small pipe OD (female socket ID)
      F       (float):  hex width across flats
      C       (float):  hex height
      L       (float):  male end length (hex to tip)
      L2      (float):  female thread engagement (small size)
      D       (float):  through-bore diameter
      Conn    (string): connection type (TH=Threaded)

    Hex-head threaded bushing (ASME B16.11) drawn without threads.  The male
    end is the B16.11 minimum length E; port 0 at its tip goes one NPT
    engagement into the mating socket, so a gap of L minus the engagement
    shows between the hex and the fitting face.  The female socket is as deep
    as the small size's NPT engagement, the mean of L1 and L2 (ASME B1.20.1).

    Local coordinate system
    ───────────────────────
      Axis  : Z
      Port 0: at z = 0 (tip of the male thread), outward direction -Z
      Port 1: at z = L + C - L2 (bottom of the socket), outward direction +Z
    """

    def __init__(self, obj,
                 PSize="DN25", PSize2="DN15",
                 OD=33.4, OD2=21.34,
                 F=35.0, C=6.0, L=19.0, L2=10.84, D=15.34,
                 Conn="TH"):
        super(HexBushing, self).__init__(obj)

        obj.Proxy   = self
        obj.PType   = "HexBushing"
        obj.PRating = "B16.11"
        obj.PSize   = PSize

        obj.addProperty(
            "App::PropertyString", "PSize2", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Nominal diameter of port 1 (small end)"),
        ).PSize2 = PSize2
        obj.addProperty(
            "App::PropertyLength", "OD", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Large pipe OD (male thread)"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength", "OD2", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Small pipe OD (female socket)"),
        ).OD2 = OD2
        obj.addProperty(
            "App::PropertyLength", "F", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Hex width across flats"),
        ).F = F
        obj.addProperty(
            "App::PropertyLength", "C", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Hex height"),
        ).C = C
        obj.addProperty(
            "App::PropertyLength", "L", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Male end length (hex to tip)"),
        ).L = L
        obj.addProperty(
            "App::PropertyLength", "L2", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Female thread engagement (socket depth)"),
        ).L2 = L2
        obj.addProperty(
            "App::PropertyLength", "D", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Through-bore diameter"),
        ).D = D
        obj.addProperty(
            "App::PropertyString", "Conn", "HexBushing",
            QT_TRANSLATE_NOOP("App::Property", "Connection type (TH=Threaded)"),
        ).Conn = Conn

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        OD  = float(fp.OD)
        OD2 = float(fp.OD2)
        F   = float(fp.F)
        C   = float(fp.C)
        L   = float(fp.L)
        L2  = float(fp.L2)
        D   = float(fp.D)
        top = L + C

        # male stub + hex head
        base = Part.makeCylinder(OD / 2, L, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
        base = base.fuse(_hexPrism(F, C, L))

        # female socket from the top face, then the bore down to the male tip
        socket = Part.makeCylinder(OD2 / 2, L2, FreeCAD.Vector(0, 0, top), FreeCAD.Vector(0, 0, -1))
        bore = Part.makeCylinder(D / 2, top, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
        base = base.cut(socket).cut(bore).removeSplitter()

        fp.Shape = base
        fp.Ports = [
            FreeCAD.Vector(0, 0, 0),         # port 0: male thread tip
            FreeCAD.Vector(0, 0, top - L2),  # port 1: bottom of socket
        ]
        fp.PortDirections = [
            FreeCAD.Vector(0, 0, -1),
            FreeCAD.Vector(0, 0,  1),
        ]
        super(HexBushing, self).execute(fp)  # perform common operations


class HexPlug(pypeType):
    """
    HexPlug(obj, [PSize="DN25", OD=33.4, F=35.0, C=10.0, L=19.0, Conn="TH"])
      obj   : the "App::FeaturePython" object
      PSize (string): nominal diameter
      OD    (float):  pipe OD (male thread OD)
      F     (float):  hex width across flats
      C     (float):  hex height
      L     (float):  male end length (hex to tip)
      Conn  (string): connection type (TH=Threaded)

    Hex-head threaded plug (ASME B16.11): a HexBushing without the hole.

    Local coordinate system
    ───────────────────────
      Axis  : Z
      Port 0: at z = 0 (tip of the male thread), outward direction -Z
    """

    def __init__(self, obj, PSize="DN25", OD=33.4, F=35.0, C=10.0, L=19.0, Conn="TH"):
        super(HexPlug, self).__init__(obj)

        obj.Proxy   = self
        obj.PType   = "HexPlug"
        obj.PRating = "B16.11"
        obj.PSize   = PSize

        obj.addProperty(
            "App::PropertyLength", "OD", "HexPlug",
            QT_TRANSLATE_NOOP("App::Property", "Pipe OD (male thread)"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength", "F", "HexPlug",
            QT_TRANSLATE_NOOP("App::Property", "Hex width across flats"),
        ).F = F
        obj.addProperty(
            "App::PropertyLength", "C", "HexPlug",
            QT_TRANSLATE_NOOP("App::Property", "Hex height"),
        ).C = C
        obj.addProperty(
            "App::PropertyLength", "L", "HexPlug",
            QT_TRANSLATE_NOOP("App::Property", "Male end length (hex to tip)"),
        ).L = L
        obj.addProperty(
            "App::PropertyString", "Conn", "HexPlug",
            QT_TRANSLATE_NOOP("App::Property", "Connection type (TH=Threaded)"),
        ).Conn = Conn

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        OD = float(fp.OD)
        L  = float(fp.L)
        base = Part.makeCylinder(OD / 2, L, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
        base = base.fuse(_hexPrism(float(fp.F), float(fp.C), L)).removeSplitter()
        fp.Shape = base
        fp.Ports = [FreeCAD.Vector(0, 0, 0)]
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1)]
        super(HexPlug, self).execute(fp)  # perform common operations
