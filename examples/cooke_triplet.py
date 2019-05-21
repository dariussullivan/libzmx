# Author: Darius Sullivan <darius.sullivan@thermo.com>
# Thermo Fisher Scientific (Cambridge, UK).
# $Rev: 351 $
# $Date: 2013-12-17 18:29:25 +0000 (Tue, 17 Dec 2013) $

# Loads one of the Zemax sample files "Cooke Triplet".
# Performs an exercise from the Short Course, optimising the lens.

from __future__ import print_function
from zemaxclient import Connection
from libzmx import *
import surface

# Establish a connection to the running Zemax application
z = Connection()
# Load a lens file into the Zemax server memory.
# It won't yet appear in the zemax window. For that we need to do z.PushLens()
z.LoadFile("C:\\Program Files\\ZEMAX\\Samples\\Short course\\sc_cooke1.zmx")

# Get a SurfaceSequence instance. This behaves like a list of surfaces
# (the same sequence as viewed in the Zemax lens data editor).
model = SurfaceSequence(z)
# Get a SystemConfig object. This allows us to get/set certain system
# parameters (eg. the stop surface, ray aiming, etc.)
systemconfig = SystemConfig(z)

# Show the number of surfaces in the lens
print("Number of surfaces in model : %d " % len(model))

# Display some information about each surface
print("Surface number, radius, thickness....")
for surf in model:
    curvature = surf.curvature.value
    if curvature:
        radius = str(1.0/curvature)
    else:
        radius = "Infinity"
    print((surf.get_surf_num(), radius, surf.thickness))

# Add some comments. These will appear in the editor.
model[1].comment = "Front surface"
model[-2].comment = "Back surface"

print("Setting variables...")
surfaces_to_optimise = range(1, 7)
for i in surfaces_to_optimise:
    surf = model[i]
    surf.curvature.vary()
    surf.thickness.vary()

# Insert an f/# solve on the curvature of surface #6
z.SetSolve(
    6,   # surface number
    0,   # solve code for curvature
    11,  # solve type code for f/#
    3.5  # desired f/#
)

# Let's add an extra constraint. We'll make the curvatures on the
# faces of the central element equal.  We can insert a pickup solve
# like this:
central_front_face = model[3]
central_rear_face = model[4]
central_rear_face.curvature = -central_front_face.curvature.linked()

# Load a merit function from another zemax file
z.LoadMerit("C:\\Program Files\\ZEMAX\\Samples\\Short course\\sc_cooke2.zmx")

# Insert a flat, glass window in front of the lens
model.insert_new(1, surface.Standard, "Window", thickness=1.0, glass="BK7")
model.insert_new(2, surface.Standard, thickness=10.0)

print("Optimising ....")
print("Initial merit func = %g" % z.Optimize(-1))
print("Final merit func = %g" % z.Optimize())

# Push the lens from the Zemax server into the display.
# The option "allow extensions to push lenses" should be enabled in
# Zemax preferences.
z.GetUpdate()
z.PushLens()
