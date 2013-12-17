Introduction
The purpose of this package is to allow Zemax to be controlled from within the 
Python programming environment. There are two major components to the package: 
an easy-to-use, object orientated programming interface, and a low-level wrapper of 
the Zemax Extensions interface.

Components
1)	zemaxclient.py : Provides a connection to the Zemax application, and a wraps 
the Zemax extensions interface. Methods on the class “Connection” map 
closely the commands provided to Zemax extensions, which are listed in 
Chapter 23 of the Zemax manual.
2)	 pyzmx.py : Provides an easy-to-use object orientated interface to Zemax. Not 
all operations available to Zemax extensions have been implemented yet. 
Facilities include a SurfaceSequence class that provides access to the surfaces 
defined in the Zemax Sequential Lens Data Editor. Parameters on surfaces can 
be accessed and modified.

Other requirements:
This package depends on the following Python packages which are not present in the 
standard distribution.
1)	Numpy : http://www.scipy.org/Download
2)	Python for Windows Extensions: http://starship.python.net/crew/mhammond/win32/ 

Note: Python for Windows Extensions, versions 214-216, contain a bug and do not work. Use version 213 until the problem is fixed. Or, if a later version is already installed, replace dde.pyd with the file of the same name from version 213 (the file can be extracted from the distribution exe with Winzip or 7-Zip).
The bug is described here: http://sourceforge.net/tracker/index.php?func=detail&aid=3314345&group_id=78018&atid=551954
 

Getting started
Zemax extensions perform operations on the optical model in the Zemax server 
memory. This is separate from the optical model displayed to the user in the main 
Zemax window on the desktop. The extension can, however, copy the model back and 
forth between the Zemax server and the main Zemax window. In order to copy the 
model to the main window, the extension needs permission to “push” the lens to the 
window. This permission must be given in the Zemax preferences (“allow extensions 
to push lenses).

The script “cooke_triplet.py” contains an example of how to use the Python interface to 
Zemax. Some operations are performed with the object-orientated interface. Other 
operations, that are not available with the object-orientated interface, can be 
performed with the basic wrapper of the Zemax extensions interface. 
The script can be executed from the command line as follows:
$ python cooke_triplet.py

Use for analysis
Ray tracing: Ray tracing can be performed on surfaces. Type the following for help:
>>> help("pyzmx.UnknownSurface.get_ray_intersect")

Optimisation operands: The value of any optimisation operand can be calculated (regardless of whether the operand appears in the current merit function). This facility is available through the method zemaxclient.Connection.OperandValue. See Chapter 23 (Zemax Extensions) of the Zemax manual for information on OperandValue.

Future work
Not all Zemax extensions commands are implemented in the zemaxclient.Connection 
wrapper class. New commands can be added relatively easily and quickly where 
needed. 

The object orientated interface will gradually be extended to provide access to: non-
sequential components and analysis, (multi) configurations, and merit functions.

Author: Darius Sullivan <darius.sullivan@thermo.com> Thermo Fisher Scientific (Cambridge, UK).
$Rev: 346 $
$Date: 2013-12-17 16:52:04 +0000 (Tue, 17 Dec 2013) $




