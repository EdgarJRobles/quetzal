# SPDX-License-Identifier: LGPL-3.0-or-later

__title__ = "pypeTools objects"
__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"
objs = ["Pipe", "Elbow", "Reduct", "Cap", "Flange", "Tee", "Ubolt", "Valve"]
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

    def __init__(self, obj, DN="DN50", OD=60.3, thk=3, BA=90, BR=45.225):
        # initialize the parent class
        super(Elbow, self).__init__(obj)
        # define common properties
        obj.PType = "Elbow"
        obj.PRating = "SCH-STD"
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
    ):
        # initialize the parent class
        super(Flange, self).__init__(obj)
        # define common properties
        self.Type = "Flange"
        obj.Proxy = self
        obj.PType = "Flange"
        obj.PRating = "DIN-PN16"
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
        """ """
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
        flange = base.extrude(FreeCAD.Vector(0, 0, fp.t - fp.trf))
        fp.ViewObject.Deviation = 0.10
        if (
            fp.FlangeType == "SW"
            or fp.FlangeType == "WN"
            or fp.FlangeType == "LJ"
            or fp.FlangeType == "SO"
        ):
            # creates flange neck
            nn = Part.makeCylinder(fp.ODp / 2, fp.T1 - fp.trf, vO, vZ).cut(
                Part.makeCylinder(fp.d / 2, fp.T1 - fp.trf, vO, vZ)
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
                        fp.dwn / 2, fp.ODp / 2, fp.twn, vZ * float(fp.t - fp.trf)
                    ).cut(Part.makeCylinder(fp.d / 2, fp.twn, vZ * float(fp.t - fp.trf)))
                    flange = flange.fuse(wn)
                    flange = flange.removeSplitter()
                    flange = flange.makeFillet(fp.R, [flange.Edges[2]])
                    flange = flange.makeChamfer((fp.ODp - fp.d) / 2 * 0.90, [flange.Edges[6]])
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
        fp.Shape = flange
        if fp.FlangeType == "WN":
            fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.trf)), FreeCAD.Vector(0, 0, float(fp.T1)-float(fp.trf))] #weld neck flanges mate with pipe at T1 - RF thickness, raised face is at 0,0,-RF thickness
        elif fp.FlangeType == "SW":
            fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.trf)), FreeCAD.Vector(0, 0, float(fp.T1)-float(fp.Y)-float(fp.trf))] #Socket weld flanges mate with pipe at Y - RF thickness, raised face is at 0,0,-RF thickness
        else: #slip on and lap joint
            fp.Ports = [FreeCAD.Vector(), FreeCAD.Vector(0, 0, float(fp.trf))] #Slip on and lap joint flanges should be mated with pipe at 0,0,0. Raised face will be at 0,0,-RF thickness
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

class Tee(pypeType):
    """  
    Tee(obj, [PSize="DN150", OD=168.27, OD2=114.3,thk=7.11,thk2=6.02,C=178,M=156])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter (run)
      OD (float): Run outside diameter
      OD2 (float): Branch outside diameter. If None, assumes same diameter as run
      thk (float): Run shell thickness
      thk2 (float): Branch shell thickness. If None, assumes same thickness as run
      C (float): Length from branch centerline to run edge
      M (float): Length from run centerline to branch edge. If None, assumes same length as run
    """
    def __init__(self, obj, DN="DN150", OD=168.27, OD2=168.27,thk=7.11,thk2=7.11,C=178.0,M=178.0):
         # initialize the parent class
        super(Tee, self).__init__(obj)
         # define common properties
        obj.Proxy = self
        obj.PType = "Tee"
        obj.PRating = "SCH-STD"
        obj.PSize = DN
        # define specific properties
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
        
        obj.addProperty(
            "App::PropertyString",
            "Profile",
            "Tee",
            QT_TRANSLATE_NOOP("App::Property", "Run and Branch Size"),
        ).Profile = str(obj.OD) + "x" + str(obj.OD2)
        
    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        
        fp.Profile = str(fp.OD) + "x" + str(fp.OD2)        
            
        Base = Part.makeCylinder(fp.OD/2, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), ) #run tube
        BranchTube = Part.makeCylinder(fp.OD2/2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
        RunHole = Part.makeCylinder(fp.OD/2 - fp.thk, fp.C*2, FreeCAD.Vector(0, 0, -fp.C), FreeCAD.Vector(0, 0, 1), )
        BranchHole = Part.makeCylinder(fp.OD2/2 - fp.thk2, fp.M, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0),  )
        
        CommonOD = Base.common(BranchTube)
        CommonID = RunHole.common(BranchHole)

        Base = Base.fuse(BranchTube)

        Base = Base.cut(RunHole)
        Base = Base.cut(BranchHole)
        
        #Filleting to make the shape look more like an actual tee does not work. Need to figure out why. 
        ##Fillet edges are Edge 4 and 10 for reducing tees and 5, 6, 7, 14, 15, 16 for straight tees

        #ODFillet = CommonOD.makeFillet(fp.M/2-fp.OD/4, CommonOD.Edges)
        #IDFillet = CommonID.makeFillet(fp.M/2-fp.OD/4, CommonID.Edges)
        
        #Base = Base.fuse(ODFillet)
        #Base = Base.fuse(IDFillet)

        """ Alternate way of filleting directly doesn't work. Also can't figure out why.
        if fp.M==fp.C :
            commonEdges = [Base.Edges[5], Base.Edges[6], Base.Edges[7], Base.Edges[14], Base.Edges[15], Base.Edges[16]]
            
        else:
            commonEdges = [Base.Edges[4], Base.Edges[10]]

        Base = Base.makeFillet(fp.M/2-fp.OD/4, commonEdges)
        #Base = Base.fuse(ODFillet)
        """
        fp.Shape = Base
        fp.Ports = [FreeCAD.Vector(0, 0, -float(fp.C)), FreeCAD.Vector(0, 0, float(fp.C)), FreeCAD.Vector(0, float(fp.M), 0)]
        fp.PortDirections = [FreeCAD.Vector(0, 0, -1), 
                      FreeCAD.Vector(0, 0, 1), 
                      FreeCAD.Vector(0, 1, 0)]
        super(Tee, self).execute(fp)  # perform common operations


class Reduct(pypeType):
    """Class for object PType="Reduct"
    Reduct(obj,[PSize="DN50",OD=60.3, OD2= 48.3, thk=3, thk2=None, H=None, conc=True])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter (major)
      OD (float): major outside diameter
      OD2 (float): minor outside diameter
      thk (float): major shell thickness
      thk2 (float): minor shell thickness
      H (float): length of reduction
      conc (bool): True for a concentric reduction, False for eccentric
    If thk2 is None or 0, the same thickness is used at both ends.
    If H is None or 0, the length of the reduction is calculated as 3x(OD-OD2).
    """

    def __init__(self, obj, DN="DN50", OD=60.3, OD2=48.3, thk=3, thk2=None, H=None, conc=True):
        # initialize the parent class
        super(Reduct, self).__init__(obj)
        # define common properties
        obj.Proxy = self
        obj.PType = "Reduct"
        obj.PRating = "SCH-STD"
        obj.PSize = DN
        # define specific properties
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


class Cap(pypeType):
    """Class for object PType="Cap"
    Cap(obj,[PSize="DN50",OD=60.3,thk=3])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      OD (float): outside diameter
      thk (float): shell thickness"""

    def __init__(self, obj, DN="DN50", OD=60.3, thk=3):
        # initialize the parent class
        super(Cap, self).__init__(obj)
        # define common properties
        obj.PType = "Cap"
        obj.Proxy = self
        obj.PRating = "SCH-STD"
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
        obj.addProperty(
            "App::PropertyLength",
            "BendRadius",
            "PypeLine2",
            QT_TRANSLATE_NOOP("App::Property", "the radius of bending"),
        ).BendRadius = BR
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "PypeLine2",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
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
    Pipe(obj,[PSize="DN50",VType="ball", OD=60.3, H=100])
      obj: the "App::FeaturePython object"
      PSize (string): nominal diameter
      PRating (string): ! the valve's type !
      OD (float): outside diameter
      H (float): length of valve"""

    def __init__(self, obj, DN="DN50", VType="ball", OD=72, ID=50, H=40, Kv=150):
        # initialize the parent class
        super(Valve, self).__init__(obj)
        # define common properties
        obj.Proxy = self
        obj.PType = "Valve"
        obj.PRating = VType
        obj.PSize = DN
        obj.Kv = Kv
        # define specific properties
        obj.addProperty(
            "App::PropertyLength",
            "OD",
            "Valve",
            QT_TRANSLATE_NOOP("App::Property", "Outside diameter"),
        ).OD = OD
        obj.addProperty(
            "App::PropertyLength",
            "ID",
            "Valve",
            QT_TRANSLATE_NOOP("App::Property", "Inside diameter"),
        ).ID = ID
        obj.addProperty(
            "App::PropertyLength",
            "Height",
            "Valve",
            QT_TRANSLATE_NOOP("App::Property", "Length of tube"),
        ).Height = H

    def execute(self, fp):
        c = Part.makeCone(fp.OD / 2, fp.OD / 5, fp.Height / 2)
        v = c.fuse(c.mirror(FreeCAD.Vector(0, 0, fp.Height / 2), FreeCAD.Vector(0, 0, 1)))
        if fp.PRating.find("ball") + 1 or fp.PRating.find("globe") + 1:
            r = min(fp.Height * 0.45, fp.OD / 2)
            v = v.fuse(Part.makeSphere(r, FreeCAD.Vector(0, 0, fp.Height / 2)))
        fp.Shape = v
        fp.Ports = [FreeCAD.Vector(), FreeCAD.Vector(0, 0, float(fp.Height))]
        super(Valve, self).execute(fp)  # perform common operations


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
