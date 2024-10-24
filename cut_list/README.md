# Cut List Creation Command for Dodo Workbench

This Module can be used to create a cut list of beams created by the DODO-Workbench.\
The cut list can use one or more profiles (sections/sketches).\
A position number will be generated for each profile & length combination (rounded to 0.01mm).\
The script will create a new speadsheet object with each cut list.

# How to use it
[Cut_List.webm](https://github.com/FilePhil/dodo_Cutlist_Macro_Version/assets/16101101/e992a925-0a02-4560-8e7c-a22eef86234d)

# Options
## Group Parts by Size
The Option "Group Parts by Size" will count all Pieces with the same profile and Length (rounded to 0.01mm).

### Example: Group Party by Size

| Beam No. 1 | | | |
|-----------------------------|--|--|--|
| Used 2855.0 mm | | | |
| Pos. | Profil | Length | Quantity |
| 1 | 10X10 | 610,00 mm | 2 |
| 2 | 10X10 | 600,00 mm | 2 |
| 3 | 10X10 | 410,00 mm | 1 |

### Exampl: Without Group Party by Size

 | Beam No. 1 | | | |
 |-----------------------------|--|--|--|
 | Used 2410.0 mm  | | | |
 | Pos.	 | Profil	 | Label	 | Length
 | 1	 | 10X10	 | Structure006	 | 610,00 mm |
 | 1	 | 10X10	 | Structure017	 | 610,00 mm |
 | 2	 | 10X10	 | Structure012	 | 600,00 mm |
 | 2	 | 10X10	 | Structure018	 | 600,00 mm |


## Use Nesting
The Option "Use Nesting" allows to specify the maximum length of the Stock Material and allows for optimizing of the available material.\
The cut Width will be added to each piece to account for the saw thickness.\
The list will be separated into Sections and shows the Used Length and the Parts that can be cut from the Stock Material.\
The position number of a piece will be the same on every stock material beam.

### Example with Nesting & Group Party by Size

| Beam No. 1 | | | |
|-----------------------------|--|--|--|
| Used 2855.0 mm of 3000.0 mm  | | | |
| Pos. | Profil | Length | Quantity |
| 1 | 10X10 | 610,00 mm | 2 |
| 2 | 10X10 | 600,00 mm | 2 |
| 3 | 10X10 | 410,00 mm | 1 |
| | | | |
| Beam No. 2   |
| Used 3000.0 mm of 3000.0 mm   |
| Pos. | Profil | Length | Quantity|
| 3 | 10X10 | 410,00 mm | 1|
| 4 | 10X10 | 390,00 mm | 2|
| 5 | 10X10 | 210,00 mm | 2|
| 6 | 10X10 | 190,00 mm | 7|
| | | | |
| Beam No. 3   |
| Used 1365.0 mm of 3000.0 mm   |
| Pos. | Profil | Length | Quantity|
| 6 | 10X10 | 190,00 mm | 7|
