
# Author: Darius Sullivan <darius.sullivan@thermo.com> Thermo Fisher Scientific (Cambridge, UK).
# $Rev: 151 $
# $Date: 2013-12-17 18:29:25 +0000 (Tue, 17 Dec 2013) $

import random
import re
import numpy as np
from zemaxclient import Connection, Untraceable
from itertools import count
from collections import namedtuple

surface_types = dict()
surface_params = dict()
class surface_type(type) :
    """Metaclass for creating a mapping between Zemax surface type strings and Surface classes"""
    def __init__(cls, name, bases, dict):
        super(surface_type, cls).__init__(name, bases, dict)
        _type = getattr(cls, "surface_type")
        if _type :
            surface_types[_type] = cls

        # register the parameters.
        # TODO: create an attribute on the surface class containing a mapping between column and parameter
        params = {}
        surface_params[cls] = params
        for key, val in dict.items() :
            if isinstance(val, Property) :
                params[key] = val.param


class SurfaceSequence :
    max_surf_id = 2**31-1
    def __init__(self, conn, empty=False, copy_from_editor=False) :
        self.conn = conn
        if empty :
            #self.conn.NewLens()
            for i in range(1, self.__len__()-1) :
                del self[i]
        if copy_from_editor :
            self.conn.GetRefresh()
        self._enforce_id_uniqueness()

    def __len__(self) :
        response = self.conn.GetSystem()
        return response[0]+1

    def _translate_id(self, id) :
        """Translate python-style sequence index into a Zemax surface number"""
        if id < 0 :
            id += self.__len__()
        if id < 0 :
            id = 0
        return id
        
    def __getitem__(self, surfno) :
        surfno = self._translate_id(surfno)
        id  = self.conn.GetLabel(surfno)
        if not id :
            id = random.randint(1, self.max_surf_id)
            self.conn.SetLabel(surfno, id)

        _type = self.conn.GetSurfaceData(surfno, 0)
        surface_factory = surface_types.get(_type, UnknownSurface)
        surf = surface_factory(self.conn, id)
        return surf

    def __delitem__(self, surfno) :
        surfno = self._translate_id(surfno)
        if surfno < 1 :
            raise IndexError("Cannot delete this surface")
        self.conn.DeleteSurface(surfno)
        
    def __iter__(self) :
        for i in range(len(self)) :
            yield self[i]

    def insert_new(self, surfno, factory, *args, **kwargs) :
        """Create and insert a new surface before the specified numbered surface.

        surfno = 0 : Not allowed
        surfno = 1 : Insert after the first surface(OBJ)
        surfno = -1 : Insert before the last surface (IMA)
        """
        surfno = self._translate_id(surfno)
        if surfno < 1 :
            raise IndexError("Cannot insert before first surface")
        
        self.conn.InsertSurface(surfno)
        id = random.randint(1, self.max_surf_id)
        self.conn.SetLabel(surfno, id)
        return factory.create(self.conn, id, *args, **kwargs)

    def append_new(self, factory, *args, **kwargs) :
        return self.insert_new(-1, factory, *args, **kwargs)

    def _enforce_id_uniqueness(self) :
        # File "C:\\Program Files\\ZEMAX\\Samples\\Short course\\sc_cooke1.zmx" has duplicate ids
        ids = set()
        for i in range(len(self)) :
            id  = self.conn.GetLabel(i)
            if id in ids :
                id = random.randint(1, self.max_surf_id)
                self.conn.SetLabel(i, id)
            ids.add(id)
    
class NamedElements(object) :
    """Allows elements of the model to be referenced by named attributes"""
    
    def __init__(self, seq) :
        """Stores all tagged surfaces as attributes on initialisation

        The argument is a SurfaceSequence instance.
        """
        for surf in seq :
            tag = surf.comment.tag
            if tag is not None:
                setattr(self, tag, surf)

    def __setattr__(self, tag, surf) :
        object.__setattr__(self, tag, surf)
        surf.comment.tag = tag


class SystemConfig(object) :
    ### This can now use SetSystemParameter.
    ### That would be less awkward and could access more attributes.
    unit_types = {
        0 : "mm",
        1 : "cm",
        2 : "in",
        3 : "m"
    }
    rayaiming_types = {
        0 : None,
        1 : "paraxial",
        2 : "real"
    }
    ###  get <- (int(numsurfs), int(unitcode), int(stopsurf), int(nonaxialflag), int(rayaimingtype),
    ###                int(adjust_index), float(temp), float(pressure), int(globalrefsurf))  
    ### set -> (unitcode, stopsurf, rayaimingtype, adjust_index, temp, pressure, globalrefsurf)

    class SystemParameter(object) :
        # define the positions of the input parameters in the output format
        setget_map = [1, 2, 4, 5, 6, 7, 8]

        def __init__(self, get_id, _type=bool) :
            self.get_id = get_id
            self._type = _type

        def __get__(self, system, owner) :
            vals = system.conn.GetSystemRaw()
            val = vals[self.get_id]
            if self._type is bool :
                val = int(val)
            return self._type(val)

        def __set__(self, system, value) :
            # We have to set all parameters at once 
            try :
                set_id = self.setget_map.index(self.get_id)
            except :
                raise NotImplementedError("This parameter cannot be set")
            if self._type is bool :
                value = int(value)
            # retrieve current values
            orig = system.conn.GetSystemRaw()
            new = [orig[i] for i in self.setget_map]
            # update with new value
            new[set_id] = str(value)
            system.conn.SetSystemRaw(*new)

    numsurfs = SystemParameter(0, int)
    unitcode = SystemParameter(1, int)
    stopsurf = SystemParameter(2, int)
    nonaxialflag = SystemParameter(3, bool)
    rayaimingtype = SystemParameter(4, int)
    adjustindex = SystemParameter(5, bool)
    temperature = SystemParameter(6, float)
    pressure = SystemParameter(7, float)
    globalrefsurf = SystemParameter(8, int)

    def __init__(self, conn) :
        self.conn = conn


class ModelConfigs(object) :
    def __init__(self, conn) :
        self.conn = conn

    def length(self) :
        currentconfig, numberconfig, numbermcoper = self.conn.GetConfig()
        return numberconfig

    def get_current(self) :
        currentconfig, numberconfig, numbermcoper = self.conn.GetConfig()
        return currentconfig

    def set_current(self, config) :
        return self.conn.SetConfig(config)

    def get_num_operands(self) :
        currentconfig, numberconfig, numbermcoper = self.conn.GetConfig()
        return numbermcoper

    def delete_operand(self, n) :
        return self.conn.DeleteMCO(n)

    def delete_config(self, n) :
        return self.conn.DeleteConfig(n)

    def clear(self) :
        for i in range(self.length()) :
            self.delete_config(i+1)
        for i in range(self.get_num_operands()) :
            self.delete_operand(i+1)

class PickupFormat(object) :
    def __init__(self, solve_code, has_scale, has_offset, has_col_ref=False) :
        """
            Defines how to set pickup solves on a parameter.

            solve_code :
                Integer code used to specify a pickup solve on the parameter with Set/GetSolve.
                Zemax manual (section: Solves >> Introduction) contains table of values (see codes "P").
            has_scale :
                Flag indicating whether referenced value can be scaled
            has_offset :
                Flag indicating whether referenced value can be offset
            has_col_ref :
                Flag indicating whether the pickup solve can reference other columns
        """

        self.solve_code = solve_code
        self.has_scale = has_scale
        self.has_offset = has_offset
        self.has_col_ref = has_col_ref
        
    def set_pickup(self, surfp, pickup_expr) :
        modifiers = []
        if self.has_scale :
            modifiers.append(pickup_expr.scale)
        elif not pickup_expr.scale==1 :
            raise TypeError("Multiplication not applicable for this pickup solve type")
        
        if self.has_offset :
            modifiers.append(pickup_expr.offset)
        elif not pickup_expr.offset==0 :
            raise TypeError("Addition not applicable for this pickup solve type")

        # Solves on "parameters" seem to require the scale and offset reversed,
        # contrary to the Zemax manual (see Solves>>Introduction).
        if surfp.reverse_pickup_terms :
            modifiers.reverse()

        col = pickup_expr.src_param.column
        if self.has_col_ref :
            modifiers.append(pickup_expr.src_param.solve_code + 1)
        elif not surfp.column == col:
            raise TypeError("Pickup solves on this parameter cannot dereference other columns")
        
        surfp.surface.conn.SetSolve(
            surfp.surface.get_surf_num(), surfp.solve_code, self.solve_code,
             pickup_expr.surface.get_surf_num(), *modifiers
            )


class Parameter(object) :
    reverse_pickup_terms = False
    def __init__(self, surface, column, _type=float, solve_code=None, pickup_conf=None, fix_code=None, can_optimise=False) :
        """Define the behaviour of a parameter on a surface.

        column:
            Integer code for parameter when defining/querying a value with Set/GetSurfaceData.
            Zemax manual (section: Zemax Extensions >> GetSurfaceData) contains table of values. 
        type :
            type for data element
        solve_code :
            Integer code for parameter when defining/querying a Solve with Set/GetSolve.
            Zemax manual (section: Zemax Extensions >> GetSolve) contains table of values.
        pickup_conf :
            PickupFormat instance defining how to set pickup solves
        fix_code :
            Integer code used to specify a fixed solve on the parameter with Set/GetSolve.
            Zemax manual (section: Solves >> Introduction) contains table of values.                
        """
        self.surface = surface
            
        self.column = column
        self._type = _type
        self.solve_code = solve_code
        self.pickup_conf = pickup_conf
        self.fix_code = fix_code
        self.can_optimise = can_optimise

    def _client_get_value(self) :
        s = self.surface
        return s.conn.GetSurfaceData(s.get_surf_num(), self.column)

    def _client_set_value(self, value) :
        s = self.surface
        s.conn.SetSurfaceData(s.get_surf_num(), self.column, value)

    def set_value(self, value) :
        if isinstance(value, PickupExpression) :
            self.link_value_to(value)
            return

        n = self.surface.get_surf_num()
        # set parameter solve to fixed (spreadsheet-like behaviour)
        if self.fix_code is not None :
            self.fix()
            
        if self._type is bool :
            value = int(value)
        self._client_set_value(value)

    def get_value(self) :
        n = self.surface.get_surf_num()
        value = self._client_get_value()
        if self._type in (bool,int) :
            # value can be (eg.) "0.0000E+000"
            value = float(value)
        
        return self._type(value)

    def __repr__(self) :
        return repr(self.get_value())

    def __str__(self) :
        return str(self.get_value())

    def linked(self) :
        return PickupExpression(self.surface, self)    

    def link_value_to(self, pickup_expr) :
        self.pickup_conf.set_pickup(self, pickup_expr)

    def fix(self) :
        n = self.surface.get_surf_num()
        self.surface.conn.SetSolve(n, self.solve_code, self.fix_code)

    def vary(self) :
        if self.can_optimise :
            n = self.surface.get_surf_num()
            self.surface.conn.SetSolve(n, self.solve_code, 1)
        else :
            raise NotImplementedError("Cannot optimise this parameter")
        
    value = property(get_value, set_value)

class Property(property) :
    # Marks surface parameters in the class dictionary
    def __init__(self, param, *args, **kwargs) :
        def get(surface) :
            return param(surface, *args, **kwargs)
        
        def set(surface, value) :
            p = get(surface)
            p.value = value
        
        property.__init__(self, get, set)
        self.param = param


class AuxParameter(Parameter) :
    reverse_pickup_terms = True
    def __init__(self, surface, column, _type=float) :
        Parameter.__init__(self, surface, column, _type, column+4, PickupFormat(2, True, True, True), 0, True)

    def _client_get_value(self) :
        s = self.surface
        return s.conn.GetSurfaceParameter(s.get_surf_num(), self.column)

    def _client_set_value(self, value) :
        s = self.surface
        s.conn.SetSurfaceParameter(s.get_surf_num(), self.column, value)

    def align_to_chief_ray(self, field_id=1, wavelength_id=0) :
        n = self.surface.get_surf_num()
        self.surface.conn.SetSolve(n, self.solve_code, 3, field_id, wavelength_id)


class ExtraParameter(Parameter) :
    def __init__(self, surface, column, _type=float) :
        Parameter.__init__(self, surface, column, _type, column+1000, PickupFormat(2, True, False, False), 0, True)

    def _client_get_value(self) :
        s = self.surface
        return s.conn.GetExtra(s.get_surf_num(), self.column)

    def _client_set_value(self, value) :
        s = self.surface
        s.conn.SetExtra(s.get_surf_num(), self.column, value)


class CurvatureParameter(Parameter) :
    def __init__(self, surface) :
        Parameter.__init__(self, surface, 2, float, 0, PickupFormat(4, True, False), 0, True)

    def set_fnumber(self, fnumber) :
        """Constrain the f/# using a solve."""
        n = self.surface.get_surf_num()
        self.surface.conn.SetSolve(n, self.solve_code, 11, fnumber)


class ThicknessParameter(Parameter) :
    def __init__(self, surface) :
        Parameter.__init__(self, surface, 3, float, 1, PickupFormat(5, True, True), 0, True)

    def focus_on_next(self, pupil_zone=0.2, target_height=0.0) :
        """Constrains thickness so that next surface lies on the focal plane.

        Uses a solve for marginal ray height on the following surface.        

        pupil_zone :
            0 : set to paraxial focus
            other : normalised entrace pupil y-coordinate for marginal ray solve
        target_height : height of marginal ray for which thickness will be constrained
            (default is zero for focus)
        """
        n = self.surface.get_surf_num()
        self.surface.conn.SetSolve(n, self.solve_code, 2, target_height, pupil_zone)


class SemiDiameterParameter(Parameter) :
    def __init__(self, surface) :
        Parameter.__init__(self, surface, 5, float, 3, PickupFormat(2, True, False), 1)

    def maximise(self, fix=False) :
        """Set to maximum of all configurations.

        fix - If true, update then fix the value."""
        n = self.surface.get_surf_num()
        self.surface.conn.SetSolve(n, self.solve_code, 3)
        if fix :
            self.surface.conn.GetUpdate()
            self.fix()
        

class CommentParameter(Parameter) :
    """Embeds an optional tag inside the comment.

    The tag is hidden when the "value" is accessed,
    but can be accessed via the property "tag".
    """
    tag_format = "%s #%s#"
    tag_patt = re.compile(r"(.*?)\s*(?:#([^#]+)#)?$")
    max_len = 32
    
    def __init__(self, surface) :
        Parameter.__init__(self, surface, 1, str)

    def get_comment_and_tag(self) :
        value = Parameter._client_get_value(self)
        comment, tag = self.tag_patt.match(value).groups()
        return comment, tag

    def set_comment_and_tag(self, comment, tag) :
        if tag :
            value = self.tag_format % (comment.rstrip(), tag)
        else :
            value = comment
        n = len(value)
        if n > self.max_len :
            # This string can probably be assigned to the model, but it won't be saved correctly in a .ZMX file
            raise ValueError(("Comment field cannot be saved", n, value))
        Parameter._client_set_value(self, value)
        
    def set_value(self, comment) :
        old_comment, tag = self.get_comment_and_tag()
        self.set_comment_and_tag(comment, tag)

    def get_value(self) :
        comment, tag = self.get_comment_and_tag()
        return comment

    def get_tag(self) :
        comment, tag = self.get_comment_and_tag()
        return tag

    def set_tag(self, tag) :
        comment, old_tag = self.get_comment_and_tag()
        self.set_comment_and_tag(comment, tag)

    value = property(get_value, set_value)
    tag = property(get_tag, set_tag)
 
    
class BaseSurface(object) :
    __metaclass__ = surface_type
    surface_type = None

    def __init__(self, conn, id) :
        self.conn = conn
        self.id = id

    def get_surf_num(self) :
        return self.conn.FindLabel(self.id)

    def remove(self) :
        """Remove the surface from the model"""
        n = self.get_surf_num()
        if n < 1 :
            raise IndexError("Cannot delete this surface")
        self.conn.DeleteSurface(n)


RayNode = namedtuple("RayNode", ["status", "vigcode", "intersect", "exit_cosines", "normal", "intensity"])

class UnknownSurface(BaseSurface) :
    type = Property(Parameter, 0, str)
    comment = Property(CommentParameter)
    thickness = Property(ThicknessParameter) # NSC doesn't have this
    ignored = Property(Parameter, 20, bool)

    def __init__(self, conn, id, comment=None, **kwargs) :
        BaseSurface.__init__(self, conn, id)
        if comment is not None :
            kwargs["comment"] = comment
        for key, value in kwargs.items() :
            try :
                p = getattr(self, key)
                assert(isinstance(p, Parameter))
            except :
                raise KeyError(key)
            p.value = value

    @classmethod
    def create(cls, *args, **kwargs) :
        # a surface type must be defined (don't call on the abstract class)
        assert(cls.surface_type is not None)
        surf = cls(*args, **kwargs)
        # creating the surface, so set the surface type
        surf.type = cls.surface_type
        return surf

    def get_ray_intersect(self, h=(0.0, 0.0), p=(0.0, 0.0), wavelength_num=0, _global = False) :
        """Get the coordinates of a ray intersecting the surface.

        h:
            Normalised field coordinate. Default: (0.0, 0.0)
        p:
            Normalised pupil coordinate. Default: (0.0, 0.0) [i.e. chief ray]
        wavelength_num:
            Wavelength number
        _global :
            Return vectors in global coordinates?
        """    
        #GetTrace(self, wave, mode, surf, h, p)
        #return status, int(vigcode), intersect, cosines, normal, float(intensity)
        n = self.get_surf_num()
        result = self.conn.GetTrace(wavelength_num, 0, n, h, p)
        #status, vigcode, intersect, exit_cosines, normal, intensity = result
        ray = RayNode(*result)
        if ray.status :
            raise Exception("GetTrace failed:", ray.status, ray)
        if _global :
            # convert vectors to global reference frame
            rotation, offset = self.conn.GetGlobalMatrix(n)
            ray = ray._replace(
                intersect = np.array(ray.intersect*rotation.T + offset).flatten(),
                exit_cosines = np.array(ray.exit_cosines*rotation.T).flatten(),
                normal = np.array(ray.normal*rotation.T).flatten()
                )
        return ray

    def trace_from_surface(self, surf, origin, cosines) :
        pass

    def fix_variables(self) :
        """Fix all variables and parameters that were adjustable under optimisation."""        
        n = self.get_surf_num()
        # Scan the surface parameters checking for adjustable variables
        fixed = []
        for i in range(17) :
            # codes are 0-16
            vals = self.conn.GetSolve(n, i)
            # check if adjustable
            if int(vals[0])==1 :
                # fix parameter
                self.conn.SetSolve(n, i, 0)
                fixed.append(i)
        return fixed

    def get_global_ref_status(self) :
        return int(float(self.conn.GetSystemProperty(21))) == self.get_surf_num()

    def make_global_reference(self) :
        return bool(self.conn.SetSystemProperty(21, self.get_surf_num()))

    is_global_reference = property(get_global_ref_status)
        

class Standard(UnknownSurface) :
    surface_type = "STANDARD"

    curvature = Property(CurvatureParameter)
    glass = Property(Parameter, 4, str, 2, PickupFormat(2, False, False), 0)
    semidia = Property(SemiDiameterParameter)
    conic = Property(Parameter, 6, float, 4, PickupFormat(2, True, False), 0, True)
    coating = Property(Parameter, 7, str)
    thermal_expansivity = Property(Parameter, 8, float, True)

    def set_rectangular_aperture(self, size, offset=(0,0)) :
        n = self.get_surf_num()
        self.conn.SetAperture(n, 4, size[0], size[1], offset[0], offset[1])        


class CoordinateBreak(UnknownSurface) :
    surface_type = "COORDBRK"

    offset_x = Property(AuxParameter, 1)
    offset_y = Property(AuxParameter, 2)
    rotate_x = Property(AuxParameter, 3)       
    rotate_y = Property(AuxParameter, 4)
    rotate_z = Property(AuxParameter, 5)
    rotate_before_offset = Property(AuxParameter, 6, bool)

    return_codes = {
        (False, False) : 1,
        (True, False) : 2,
        (True, True) : 3
        }
    def return_to(self, surf, offset_xy = True, offset_z=True) :
        """Set a coordinate return.

        Set surf to None to remove a coordinate return."""
        if surf is None :
            # do not return to a surface
            self.conn.SetSurfaceData(self.get_surf_num(), 80, 0)
        else :
            code = self.return_codes[(offset_xy, offset_z)]
            self.conn.SetSurfaceData(self.get_surf_num(), 81, surf.get_surf_num())
            self.conn.SetSurfaceData(self.get_surf_num(), 80, code)


def return_to_coordinate_frame(seq, first_return_surf, last_return_surf, insert_point=None, include_null_transforms=True, factory=None) : 
    assert (first_return_surf < last_return_surf)
    nsteps = last_return_surf - first_return_surf + 1
    surfaces_to_undo = range(last_return_surf, last_return_surf-nsteps, -1)

    if not factory :
        if insert_point is None :
            insert_point = last_return_surf
            
        insertion_point_sequence = count(insert_point+1)
        factory = lambda : seq.insert_new(insertion_point_sequence.next(), CoordinateBreak)
        
    for sn1 in surfaces_to_undo :
        to_undo = seq[sn1]        
        if isinstance(to_undo, CoordinateBreak) :
            # undo thickness first
            if not to_undo.thickness.value==0 or include_null_transforms :
                inserted = factory()
                inserted.thickness.value = -to_undo.thickness.linked()
                inserted.comment.value = "UNDO thickness "+ (to_undo.comment.value or str(to_undo.get_surf_num()))

            transformations = [
                to_undo.offset_x.value,
                to_undo.offset_y.value,
                to_undo.rotate_x.value,
                to_undo.rotate_y.value,
                to_undo.rotate_z.value
            ]
            if any(transformations) or include_null_transforms :          
                inserted = factory()              
                inserted.offset_x.value = -to_undo.offset_x.linked()
                inserted.offset_y.value = -to_undo.offset_y.linked()
                inserted.rotate_x.value = -to_undo.rotate_x.linked()
                inserted.rotate_y.value = -to_undo.rotate_y.linked()
                inserted.rotate_z.value = -to_undo.rotate_z.linked()
                inserted.rotate_before_offset.value = not to_undo.rotate_before_offset.value
                inserted.comment.value = "UNDO " + (to_undo.comment.value or str(to_undo.get_surf_num()))
                
        elif not to_undo.thickness.value==0 or include_null_transforms :
            # simple surface, only requires undo of thickness
            inserted = factory()
            inserted.rotate_before_offset.value = False
            inserted.thickness.value = -to_undo.thickness.linked()
            inserted.comment.value = "UNDO " + (to_undo.comment.value or str(to_undo.get_surf_num()))

    return inserted.get_surf_num()        
   
            
class PickupExpression:
    # Zemax extensions are restricted in setting pickup solves from different (columns).
    # Currently, we can only pick up from different columns on "parameter" solves (ie. AuxParameter instances).
    # This restriction does not exist in the GUI and ZPL scripts.
    def __init__(self, surface, parameter, offset=0, scale=1) :
        self.surface = surface
        self.src_param = parameter
        self.offset = offset 
        self.scale = scale

    def _copy(self) :
        return PickupExpression(self.surface, self.src_param, self.offset, self.scale)

    def __add__(self, other) :
        x = self._copy()
        x.offset += other
        return x

    def __radd__(self, other) :
        return self.__add__(other)

    def __sub__(self, other) :
        x = self._copy()
        x.offset -= other
        return x

    def __rsub__(self, other) :
        x = self._copy()
        x.offset = other - x.offset
        x.scale = -x.scale
        return x

    def __mul__(self, other) :
        x = self._copy()
        x.offset *= other
        x.scale *= other
        return x

    def __rmul__(self, other) :
        return self.__mul__(other)

    def __div__(self, other) :
        x = self._copy()
        x.offset /= float(other)
        x.scale /= float(other)
        return x

    def __truediv__(self, other) :
        return self.__div__(self, other)

    def __neg__(self) :
        x = self._copy()
        x.offset = -x.offset
        x.scale = -x.scale
        return x

    def __pos__(self) :
        return self


def make_singlet(z) :
    """Make a singlet lens"""
    model = SurfaceSequence(z, empty=True)

    model[0].thickness = 100     # Set object plane position
    z.SetSystemAper(0, 1, 10.0)  # Set entrance pupil diameter to 10.0

    # append front surface
    front = model.append_new(Standard)
    front.glass = "BK7"
    front.thickness = 1.0

    # append back surface
    back = model.append_new(Standard)
    back.curvature.set_fnumber(10)   # f/number solve on radius
    back.thickness.focus_on_next()   # marginal ray height solve

    z.PushLens() # transfer model to frontend

if __name__=="__main__" :
    import sys

    z = Connection()
    print "Zemax Version : " + str(z.GetVersion())
    model = SurfaceSequence(z)
    sysconfig = SystemConfig(z)

    if "singlet" in sys.argv :
        make_singlet(z)
        z.PushLens()
    

