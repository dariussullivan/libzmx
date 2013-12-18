libzmx
======

[Libzmx] [1] is a Python module for controlling [Zemax] [2] optical design software. It provides a friendly interface for manipulating optical models with Python.

The module works as a Zemax client, built on the extensions API for Zemax. 

Hello, World
------------

This is how we construct a singlet lens with libzmx. You need to have the option “allow extensions to push lenses" enabled in the Zemax preferences for this to work.

```python
from libzmx import *

z = Connection()
model = SurfaceSequence(z, empty=True)

model[0].thickness = 100     # Set object plane position
z.SetSystemAper(0, 1, 10.0)  # Set entrance pupil diameter to 10.0

# append front surface
front = model.append_new(surface.Standard)
front.glass = "BK7"
front.thickness = 1.0

# append back surface
back = model.append_new(surface.Standard)
back.curvature.set_fnumber(10)   # f/number solve on radius
back.thickness.focus_on_next()   # marginal ray height solve

z.PushLens() # send model to frontend
```

Features
--------
* Access *Lens Data Editor* surfaces as elements of the list-like `libzmx.SurfaceSequence`
* Access surface parameters as attributes of surface objects
* Define "solves" on surface parameters
* Define pickup solves using expressions and surface attributes (e.g. `back.curvature = -2*front.curvature.linked()`)
* Trace rays to surfaces
* Get the text-file result of any Zemax analysis
* Read the data from non-sequential detectors as a [NumPy array] [3]
* Get the value of any Zemax merit function operand
* Access to low-level extension operations with `libzmx.Connection`

Requirements
------------
* [Zemax] [2]
* [NumPy] [3]

Getting it working
------------------
The libzmx client works with a model residing in a Zemax server, which is not the model we see in the Zemax main window. The client can transfer  models between the server and Zemax window, but only if the option “allow extensions to push lenses" is enabled in the Zemax preferences. *Tick this option to see results in the Zemax window.*

Problems
--------
If you find that python freezes when using libzmx, check the Zemax main window for error message dialogs and dismiss them. In this respect, Zemax doesn't really act like a server. 

Zemax
-----
[Zemax] [2] is an optical-design software package for Windows.

Zemax is a registered trademark of Radiant Zemax LLC.

[1]: https://github.com/dariussullivan/libzmx/ "libzmx"
[2]: http://http://www.radiantzemax.com/zemax/ "Zemax"
[3]: http://www.numpy.org/ "NumPy"


