import sys
from libzmx import *

z = Connection()
print("Zemax Version : " + str(z.GetVersion()))
model = SurfaceSequence(z)
sysconfig = SystemConfig(z)

if "singlet" in sys.argv:
    make_singlet(z)
    z.PushLens()
