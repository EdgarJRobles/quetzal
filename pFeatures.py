# SPDX-License-Identifier: LGPL-3.0-or-later

__title__ = "pypeTools objects"
__author__ = "oddtopus"
__url__ = "github.com/oddtopus/dodo"
__license__ = "LGPL 3"
objs = ["Pipe", "Elbow","DuctReduction", "DuctElbow", "Reduct", "Cap", "Flange", "Tee", "Ubolt", "Valve"]
metaObjs = ["PypeLine", "PypeBranch"]

import FreeCAD
import Part

from quetzal_config import FREECADVERSION, get_icon_path
from quetzal.domain.pipe_sizes import PIPE_OUTSIDE_DIAMETERS_MM as pipe_OD
from quetzal.features.flange import (
    DEFAULT_FLANGE_BUILDER,
    FLANGE_BUILDERS,
    configure_view,
    spec_from_object,
)
from quetzal.features.flange.properties import define_flange_properties
from quetzal.application.valve import ValveContext
from quetzal.application.pype_line import line_group as resolve_line_group
from quetzal.application.pype_children import (
    branch_children,
    clear_branch_children,
    ensure_branch_schema,
    migrate_branch_children,
    set_branch_children,
)
from quetzal.domain.valve_modes import (
    FLANGE_CONNS as VALVE_FLANGE_CONNS,
    geometry_mode,
    property_mode,
)
from quetzal.features.valve import strategy_for
from quetzal.features import (  # noqa: F401 (re-exported)
    Cap,
    Gasket,
    Pipe,
    PypeFeature as pypeType,
    TerminalAdapter,
)

QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate

vO = FreeCAD.Vector(0, 0, 0)
vX = FreeCAD.Vector(1, 0, 0)
vY = FreeCAD.Vector(0, 1, 0)
vZ = FreeCAD.Vector(0, 0, 1)
# Nominal OD table lives in quetzal.domain.pipe_sizes (imported above).

################ CLASSES ###########################


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
        import pCmd
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
        # FreeCAD's normalize()/multiply() mutate in place.  Copy the input
        # vectors first: callers pass the module-level vX/vY/vZ constants, and
        # mutating those corrupted every feature created afterwards.
        x = FreeCAD.Vector(xdir).normalize().multiply(width / 2)
        y = FreeCAD.Vector(ydir).normalize().multiply(height / 2)
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

    shape_builders = FLANGE_BUILDERS
    default_shape_builder = DEFAULT_FLANGE_BUILDER

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
        obj.PSize = DN
        define_flange_properties(
            obj,
            {
                "FClass": FClass,
                "FlangeType": FlangeType,
                "D": D,
                "d": d,
                "df": df,
                "f": f,
                "t": t,
                "n": int(n),
                "trf": trf,
                "drf": drf,
                "twn": twn,
                "dwn": dwn,
                "ODp": ODp,
                "R": R,
                "T1": T1,
                "B2": B2,
                "Y": Y,
            },
        )


    def onChanged(self, fp, prop):
        # FreeCAD.Console.PrintMessage(prop)
        if prop == "ODp":
            if fp.ODp > fp.D:
                FreeCAD.Console.PrintError(
                    "Raised edge diameter must be smaller than flange diameter"
                )
        return None

    def execute(self, fp):
        configure_view(fp)
        spec = spec_from_object(fp)
        builder = self.shape_builders.get(fp.FlangeType, self.default_shape_builder)
        geometry = builder.build(spec)
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super(Flange, self).execute(fp)

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

        #cut out inner bore
        base = base.cut(cutout)

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

        base = base.cut(cutout)
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
        # FreeCAD's normalize()/multiply() mutate in place.  Copy the input
        # vectors first: callers pass the module-level vX/vY/vZ constants, and
        # mutating those corrupted every feature created afterwards.
        x = FreeCAD.Vector(xdir).normalize().multiply(width / 2)
        y = FreeCAD.Vector(ydir).normalize().multiply(height / 2)
        pts = [
            center - x - y,
            center + x - y,
            center + x + y,
            center - x + y,
            center - x - y,
        ]
        return Part.Wire(Part.makePolygon(pts))


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
        if prop == "Label":
            group = fp.getParentGroup()
            if group is not None:
                group.Label = fp.Label + "_pieces"
                fp.Group = group.Label
        if hasattr(fp, "Base") and prop == "Base" and fp.Base:
            FreeCAD.Console.PrintWarning(fp.Label + " Base has changed to " + fp.Base.Label + "\n")
        if prop == "OD":
            fp.BendRadius = 0.75 * fp.OD

    def purge(self, fp):
        group = resolve_line_group(fp)
        for obj in list(group.OutList):
            if hasattr(obj, "PType") and obj.PType in ["Pipe", "Elbow"]:
                fp.Document.removeObject(obj.Name)

    def update(self, fp, edges=None):
        import fCmd
        import pCmd
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
        tubes, curves = branch_children(self.Object)
        return tubes + curves

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
    FLANGE_CONNS = VALVE_FLANGE_CONNS

    def __init__(self, obj, DN="DN50", VType="ball", ODBody=72, ID=50, H=40, Kv=150,
                 OD=None, E=None, Conn=None,
                 flgD=0, flgt=0, flgdrf=0, flgtrf=0,
                 flgdf=0, flgf=0, flgn=0,
                 actuator="Handle", bottomH=0, topH=0):
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

        mode = property_mode(Conn)
        if mode == "flanged":
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
                QT_TRANSLATE_NOOP("App::Property",
                                  "Actuator type: Handle or Gearbox"),
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

        elif mode == "sw_th":
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
        else:
            # -- Generic (legacy) valve properties --------------------------
            obj.addProperty(
                "App::PropertyLength", "ID", "Valve",
                QT_TRANSLATE_NOOP("App::Property", "Inside diameter"),
            ).ID = ID

        self.execute(obj)

    def onChanged(self, fp, prop):
        return None

    def execute(self, fp):
        context = ValveContext.from_feature(fp)
        strategy = strategy_for(geometry_mode(context.conn, context.rating))
        geometry = strategy.build(context)
        fp.Shape = geometry.shape
        fp.Ports = list(geometry.ports)
        fp.PortDirections = list(geometry.directions)
        super(Valve, self).execute(fp)

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
        ensure_branch_schema(obj)
        obj.ChildrenSchema = 1
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

    def onDocumentRestored(self, fp):
        migrate_branch_children(fp)

    def onChanged(self, fp, prop):
        if (
            prop == "Base"
            and hasattr(fp, "OD")
            and hasattr(fp, "thk")
            and hasattr(fp, "BendRadius")
        ):
            self.purge(fp)
            self.redraw(fp)
        elif prop == "BendRadius" and hasattr(fp, "CurvesLink"):
            for curve in branch_children(fp)[1]:
                if curve is not None:
                    curve.BendRadius = fp.BendRadius
        elif prop == "OD" and hasattr(fp, "BendRadius") and hasattr(fp, "TubesLink"):
            for obj in sum(branch_children(fp), []):
                if obj is None:
                    continue
                if getattr(obj, "PType", "") == "Elbow":
                    obj.BendRadius = fp.BendRadius
                obj.OD = fp.OD
            fp.BendRadius = fp.OD * 0.75
        elif prop == "thk" and hasattr(fp, "TubesLink"):
            for obj in sum(branch_children(fp), []):
                if obj is not None and hasattr(obj, "thk"):
                    obj.thk = fp.thk

    def execute(self, fp):
        ensure_branch_schema(fp)
        migrate_branch_children(fp)
        base = getattr(fp, "Base", None)
        if base is None or not hasattr(base, "Shape"):
            return
        tubes, _ = branch_children(fp)
        if len(tubes) != len(base.Shape.Edges):
            self.purge(fp)
            self.redraw(fp)

    def redraw(self, fp):
        import pCmd
        from math import degrees, tan

        tubes = []
        curves = []
        if not getattr(fp, "Base", None):
            return
        for i in range(len(fp.Base.Shape.Edges)):
            edge = fp.Base.Shape.Edges[i]
            length = edge.Length
            radius = float(fp.BendRadius)
            offset = 0
            if i > 0:
                alfa = edge.tangentAt(0).getAngle(
                    fp.Base.Shape.Edges[i - 1].tangentAt(0)
                ) / 2
                length -= radius * tan(alfa)
                offset = radius * tan(alfa)
            if i < (len(fp.Base.Shape.Edges) - 1):
                alfa = edge.tangentAt(0).getAngle(
                    fp.Base.Shape.Edges[i + 1].tangentAt(0)
                ) / 2
                length -= radius * tan(alfa)
            support = "Edge" + str(i + 1)
            tube = pCmd.makePipe(
                fp.PRating, [fp.PSize, float(fp.OD), float(fp.thk), length]
            )
            tube.PRating = fp.PRating
            tube.PSize = fp.PSize
            tube.AttachmentSupport = [(fp.Base, support)]
            tube.MapMode = "NormalToEdge"
            tube.MapReversed = True
            tube.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0, 0, offset), FreeCAD.Rotation()
            )
            tubes.append(tube)
            if i > 0:
                previous = fp.Base.Shape.Edges[i - 1]
                alfa = degrees(previous.tangentAt(0).getAngle(edge.tangentAt(0)))
                elbow = pCmd.makeElbow(
                    [fp.PSize, float(fp.OD), float(fp.thk), alfa, radius]
                )
                elbow.PRating = fp.PRating
                elbow.PSize = fp.PSize
                elbow.MapReversed = False
                elbow.AttachmentSupport = [(fp.Base, "Vertex" + str(i + 1))]
                elbow.MapMode = "Translate"
                pCmd.placeTheElbow(elbow, previous.tangentAt(0), edge.tangentAt(0))
                curves.append(elbow)
        set_branch_children(fp, tubes, curves)

    def purge(self, fp):
        tubes, curves = branch_children(fp)
        for obj in tubes + curves:
            if obj is None:
                continue
            try:
                fp.removeObjects([obj])
            except Exception:
                pass
            document = getattr(obj, "Document", None)
            if document is not None and document.getObject(obj.Name) is not None:
                document.removeObject(obj.Name)
        clear_branch_children(fp)


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
    rating    : string  schedule (ButtWeld) or class (SocketWeld)
    DN        : string  nominal size  e.g. "DN50"
    OD        : float   outside diameter at the pipe-connection end
    thk       : float   wall thickness at the pipe-connection end
    A         : float   height of the fitting above the run-pipe surface
                         (measured along the fitting axis)
    B         : float   outer diameter at the base (run-pipe attachment)
    endType   : "ButtWeld" | "SocketWeld"
    angle     : 0 (straight)  |  45 (lateral/elbow)
    E         : float   socket depth (SocketWeld only); the port sits here

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
                "(SocketWeld only)"),
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
                "ButtWeld (tapered body) or SocketWeld (cylindrical body)"),
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

        else:  # SocketWeld / SW
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
            if endType in ("SocketWeld", "SW"):
                E_clamped = min(E, A - 0.5) if E > 0 else A * 0.3
                port_pos = FreeCAD.Vector(0, -E_clamped * s2, E_clamped * s2)
            else:
                port_pos = FreeCAD.Vector(0, -A * s2, A * s2)
            port_dir = FreeCAD.Vector(0, -s2, s2)
        else:
            if endType in ("SocketWeld", "SW"):
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

