from libzmx import UnknownSurface, FiniteSurface, Standard, CoordinateBreak
from libzmx import Property, Parameter, AuxParameter, ExtraParameter, PickupFormat
from libzmx import SemiDiameterParameter

class Toroidal(Standard) :
    surface_type = "TOROIDAL"

    radius_of_rotation = Property(AuxParameter, 1)

    num_poly_terms = Property(ExtraParameter, 1, int)
    norm_radius = Property(ExtraParameter, 2)
    

class Grating(Standard) :
    surface_type = "DGRATING"

    groove_freq = Property(AuxParameter, 1)
    order = Property(AuxParameter, 2)


class GeneralisedFresnel(Standard) :
    surface_type = "GEN_FRES"

    num_poly_terms = Property(ExtraParameter, 1, int)
    norm_radius = Property(ExtraParameter, 2)

    x1y0 = Property(ExtraParameter, 3)
    x0y1 = Property(ExtraParameter, 4)


class RetroReflect(FiniteSurface) :
    # When glass=="mirror", exit rays coincide with incident rays
    surface_type = "RETROREF"
    
    glass = Property(Parameter, 4, str, 2, PickupFormat(2, False, False), 0)
    semidia = Property(SemiDiameterParameter)

    coating = Property(Parameter, 7, str)
    thermal_expansivity = Property(Parameter, 8, float, True)
    