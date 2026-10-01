Las tablas se encuentran ubicadas en la carpeta `Tablez`

Existen tablas ordenadas por tipo de estandar, Tipo de ensamble, clase, etc.
`_` es un separador necesario para quetzal este clasifica la tabla para ser utilizada por las ventanas emergentes.

AAA_BBB.cvs

| [Elemento] AAA |
| ------------- |
| Elbow |
| Beam |
| Section |
| Coupling |
| Clamp |
| Flange |
| Gasket |
| Pipe |
| Reduct |
| Tee |
| Valve |
| Union |
| TerminalAdapter |
| Outlet |

| [Clase] BBB|
| ------------- |
| 150lb |
| 300lb |
| 400lb |
| 600lb |
| 900lb |
| 1500lb |
| 2500lb |
| 3000lb |
| 6000lb |
| 9000lb |
| SCH-5 |
| SCH-10 |
| SCH-20 |
| SCH-30 |
| SCH-40 |
| SCH-50 |
| SCH-50 |
| SCH-80 |
| SCH-100 |
| SCH-120 |
| SCH-140 |
| SCH-160 |
| SCH-STD |
| SCH-XS |
| SCH-XXS |
| ASME-BL-RF-150lb |
| ASME-BL-RF-300lb |
| ASME-BL-RF-600lb |
| ASME-BL-RF-900lb |
| ASME-BL-RF-1500lb |
| ASME-BL-RF-2500lb |
| ASME-SO-RF-150lb |
| ASME-SO-RF-300lb |
| ASME-SO-RF-600lb |
| ASME-SO-RF-900lb |
| ASME-SW-RF-150lb |
| ASME-WN-RF-150lb |
| ASME-WN-RF-300lb |

Variables Implemented in each CSV table:

| Variable | Description | Implemented in table |
| --------------- | --------------- | --------------- |
| Psize | Section designation | All |
| Psize2 | nominal diameter of port 1 (opposite end, +Z) | SocketCoupling, Bushing |
| OD | Outer diameter | Pipe, Reduct, Elbow, Coupling, TerminalAdapter, Outlet|
| OD2 | Minor outer diameter | Reduct, TerminalAdapter, Bushing |
| BendAngle | Bend angle | Elbow, SocketCap |
| BendRadio | Bend radio | Elbow |
| thk | Wall thickness | Pipe, Reduct, Outlet, Cap |
| thk2 | Minor wall thickness | Reduct |
| ID | Inner diameter | Pipe, Cap |
| H | Beam height | Beam, Reduct |
| W | Beam width | Beam |
| Stype | Beam section profile type | Beam |
| ta | Web / wall thickness | Beam |
| tf | Web / Flange thickness | Beam |
| Height | Overall beam length | Beam, Pipe, Reduct |
| IRID | Inner ring inner diameter | Gasket |
| SEID | Sealing element inner diameter | Gasket |
| SEOD | Sealing element outer diameter | Gasket |
| CROD | Centering ring outer diameter | Gasket |
| SEthk | Sealing element thickness | Gasket |
| Rthk | Inner and centering ring thickness | Gasket |
| L | Overall length; male end length, hex to tip (Bushing, Plug) | TerminalAdapter, Bushing, Plug |
| L2 | Female thread engagement (socket depth) | Bushing |
| F | Hex width across flats | Bushing, Plug |
| SW | Support width | Outlet, TerminalAdapter |
| A | Height above run-pipe surface (along fitting axis) | Outlet, Cap |
| B | Outer diameter at base attachment | Outlet |
| C |  | Outlet |
| E | Socket depth bore steps from ID to OD at this height | Outlet, SocketCap |
| Conn | ConnectionType | SocketCap, Cap, Bushing, Plug |
| Conc | Concentric or excentric connection | Reduct |
| E2 | Socket / thread engagement at port 1 when it differs from E | Valve (socket x threaded) |
| Conn2 | Connection type at port 1 when it differs from Conn | Valve (socket x threaded) |
| TopH | Upper envelope from centerline; gate valves: to the stem top, gate open | Valve (flanged) |
| WheelD | Handwheel diameter (0 = 0.9 x face-to-face length) | Valve (flanged gate) |

Section profile type [Stype] summary table:

| Variable | Description | Implemented in table |
| --------------- | --------------- | --------------- |
| H | H section | Beam |
| RH | Rectangular hollow section | Beam|
| R | Rectangular solid section | Beam|
| C | Circular solid section | Beam|
| U | C section | Beam|
| L | Angle section | Beam|
| T | T section | Beam|


<figure>
    <img src="./doc/Elbow-reference.svg"
         alt="GDL,Mexico">
    <figcaption>Elbow variables.</figcaption>
</figure>

<figure>
    <img src="./doc/Reduct-reference.svg"
         alt="GDL,Mexico">
    <figcaption>Reduct variables.</figcaption>
</figure>

<figure>
    <img src="./doc/Cap-reference.svg"
         alt="GDL,Mexico">
    <figcaption>Cap variables.</figcaption>
</figure>
<figure>
    <img src="./doc/Tee-reference.svg"
         alt="GDL,Mexico">
    <figcaption>Tee variables.</figcaption>
</figure>
<figure>
    <img src="./doc/Gasket-reference.svg"
         alt="GDL,Mexico">
    <figcaption>Gasket variables.</figcaption>
</figure>
<figure>
    <img src="./doc/TerminalAdapter-reference.svg"
         alt="GDL,Mexico">
    <figcaption>TerminalAdapter variables.</figcaption>
</figure>

<figure>
    <img src="./doc/Coupling-reference.svg"
         alt="GDL,Mexico">
    <figcaption>Coupling variables.</figcaption>
</figure>
