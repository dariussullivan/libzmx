# Author: Darius Sullivan <darius.sullivan@thermo.com> Thermo Fisher Scientific (Cambridge, UK).
# $Rev: 346 $
# $Date: 2013-12-17 16:52:04 +0000 (Tue, 17 Dec 2013) $
import os
import tempfile
import codecs
from numpy import array, matrix
from contextlib import contextmanager
from functools import wraps
import dde

# A Connection can manipulate a "Lens" in the Zemax server memory.
# This is not the same as the Lens shown in the Zemax program window (Lens Data Editor).
# The Lens can be copied in and out of the Lens Data Editor by the commands PushLens and
# GetRefresh, respectively.

class Untraceable(Exception) :
    pass

class SurfaceLabelError(LookupError) :
    pass

class ZemaxServerError(Exception) :
    pass

class InvalidSurface(Exception) :
    pass

class AmbiguousString(Exception) :
    pass

def returns_error_status(func) :
    @wraps(func)
    def wrapper(*args, **kwargs) :
        error = func(*args, **kwargs)
        if error :
            raise ZemaxServerError("%s signalled an error: %s" % (func.__name__,str(error)))
    return wrapper

@contextmanager
def tmpfile_callback(callback, extension=".txt", mode="rb") :
    # Zemax will not open a file created with tempfile.NamedTemporaryFile().
    # We have to use lower level functions.
    (fd, path) = tempfile.mkstemp(extension)
    
    try :    
        result = callback(path)
    except :
        os.close(fd)
        raise
    else :
        f = os.fdopen(fd, mode)
        try :
            yield (result, f, path)
        finally :
            f.close()
    finally :
        os.remove(path)

class Connection :
    """Encapsulates a connection to the Zemax server.

    Methods on this class closely resemble the commands (or "data items") available to Zemax extensions.
    Chapter 23 of the Zemax manual "Zemax Extensions" explains how the commands work.
    """
    def __init__(self, verbose=False) :
        self.verbose = verbose
        self.connect()

    def connect(self) :
        self.conversation = dde.DDEClient("ZEMAX", "ZEMAX")

    def disconnect(self) :
        if self.conversation is not None:
            self.conversation.__del__()
            self.conversation = None

    default_timeout = 2**28
    def req(self, rs, timeout=0) :
        timeout = max(self.default_timeout, timeout)
        if self.verbose :
            print "Send : " + rs
        response = self.conversation.request(rs, timeout)
        if self.verbose :
            print "Recv : " + response.rstrip()
        if response.startswith("BAD COMMAND")  :
            raise ZemaxServerError("Bad command sent to server : %s" % str(rs))
        return response.rstrip("\r\n")

    def _str(self, val) :
        if isinstance(val, float) :
            s = "%.20E" % val
        else :
            s = str(val)
        return s
        
    #@returns_error_status
    def DeleteConfig(self, config) :
        response = self.req("DeleteConfig,%d" % config)
        return int(response)

    def DeleteMCO(self, operand) :
        # returns the new number of operands
        return int(self.req("DeleteMCO,%d" % operand))

    def DeleteMFO(self, operand) :
        # returns the new number of operands
        return int(self.req("DeleteMFO,%d" % operand))

    @returns_error_status
    def DeleteSurface(self, surf) :
        """deletes the surface"""
        response = self.req("DeleteSurface,%d" % surf)
        return int(response)

    def ExportCAD(self, filename, filetype, numspline=0, first=0, last=-1, rayslayer=0, lenslayer=1,
                  exportdummy=False, usesolids=True, raypattern=0, numrays=10, wave=0, field=0,
                  deletevignetted = True, dummythick=1.0, split=False, scatter=False, usepol=False, config=0) :
        """
        Arguments:
            filetype: {0:IGES, 1:STEP, 2:SAT, 3:STL)
            numspline: {0:16, 1:32, 2:64, 4:256, 5:512}
            first: first surface to export
            last: last surface to export
            rayslayer: layer to contain rays
            lenslayer: layer to contain lens objects
            exportdummy: export dummy surfaces
            usesolids: export solids as surfaces
            raypattern: {0:XY, 1:X, 2:Y, 3:ring, 4:list, 5:none, 6:grid, 7:solid beam}
            numrays: number of rays
            wave: wavelength number (0 for all)
            field: field number (0 for all)
            deletevignetted: delete vignetted rays
            dummythick: dummy surface thickness (lens units)
            split: split rays from NSC sources
            scatter: scatter rays from NSC sources
            usepol: use polarisation
            config: configuration to export
              {
               0: current,
               1..n: specific config,
               -1: all by file,
               -2: all by layer,
               -3: all at once
              }
         """ 
        if config < 0 :
            n = self.GetMulticon(1,1)[1]
            config = n - config
        if last < 0 :
            last = self.GetSystem()[0] - last + 1
        cmd = "ExportCAD,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%.20E,%d,%d,%d,%d" % (
             filename, filetype, numspline, first, last, rayslayer, lenslayer, int(exportdummy),
             int(usesolids), raypattern, numrays, wave, field, int(deletevignetted),
             dummythick, int(split), int(scatter), int(usepol), config)
        return self.req(cmd)

    def ExportCheck(self) :
        response = self.req("ExportCheck")
        return int(response)
        
    def FindLabel(self, label) :
        response = self.req("FindLabel,%d" % label)
        surf = int(response)
        if surf<0 :
            raise SurfaceLabelError(label)
        return surf

    def GetAperture(self, surf) :
        response = self.req("GetAperture,%d" % surf)
        _type, _min, _max, _xdecenter, _ydecenter, _aperturefilename = response.split(",")
        return int(_type), float(_min), float(_max), float(_xdecenter), float(_ydecenter), _aperturefilename

    def GetConfig(self) :
        response = self.req("GetConfig")
        _currentconfig, _numberconfig, _numbermcoper = response.split(",")
        return int(_currentconfig), int(_numberconfig), int(_numbermcoper)

    def GetExtra(self, surf, column) :
        return self.req("GetExtra,%d,%d" % (surf, column))

    def GetFieldsConfig(self) :
        response = self.req("GetField,0")
        _type, _number, _max_x_field, _max_y_field, _normalization_method = response.split(",")
        return int(_type), int(_number), float(_max_x_field), float(_max_y_field), int(_normalization_method)

    def GetField(self, n) :
        assert(n > 0) # 0 gets configuration - see GetFieldsConfig
        response = self.req("GetField,%d" % n)
        xfield, yfield, weight, vdx, vdy, vcx, vcy, van = (float(n) for n in response.split(","))
        return xfield, yfield, weight, vdx, vdy, vcx, vcy, van

    def GetFile(self) :
        response = self.req("GetFile")
        return response

    def GetGlobalMatrix(self, surf) :
        response = self.req("GetGlobalMatrix,%d" % surf)
        elements = [float(x) for x in response.split(",")]
        rotation = matrix(array(elements[:9]).reshape((3,3)))
        offset = array(elements[9:])
        return rotation, offset

    def GetIndex(self, surf) :
        response = self.req("GetIndex,%d" % surf)
        if not response :
            raise InvalidSurface()
        return [float(x) for x in response.split(",")]

    def GetLabel(self, surf) :
        response = self.req("GetLabel,%d" % surf)
        label = int(response)
        return label

    def GetMulticonOperand(self, row) :
        values = self.req("GetMulticon,0,%d" % row).split(",")
        #operand_type = int(values[0])
        operand_type = values.pop(0)
##        ivalues = [int(x) for x in values]
##        # need to check for loss of precision
##        assert(all( i-float(v)==0 for i, v in zip(ivalues,values)))
##        return operand_type, ivalues
        v0, v1, v2 = values
        return operand_type, int(v0), int(v1), int(v2)

    def GetMulticon(self, config, row) :
        assert(config > 0) # 0 gets operand info - see GetMulticonOperand
        response = self.req("GetMulticon,%d,%d" % (config, row))
        vals = response.split(",")
        if len(vals) > 6 :
            _value, _num_config, _num_row, _status, _pickuprow, _pickupconfig, _scale, _offset = vals
            _scale = float(_scale)
            _offset = float(_offset)
        else :
            _value, _num_config, _num_row, _status, _pickuprow, _pickupconfig = vals
            _scale = _offset = None
        # Status :
        #  0 : fixed
        #  1 : variable
        #  2 : pickup
        #  3 : thermal pickup
        # 2,3 => _pickuprow, _pickupconfig indicate source
        return (
            _value, int(_num_config), int(_num_row),
            int(_status), int(_pickuprow), int(_pickupconfig), _scale, _offset           
            )

    def GetNSCData(self, surf, code=0) :
        # currently only code=0 is defined (returns number of objects)
        response = self.req("GetNSCData,%d,%d" % (surf, code))
        return int(response)

    def GetNSCMatrix(self, surf, obj) :
        response = self.req("GetNSCMatrix,%d,%d" % (surf, obj))
        # same behaviour as GetGlobalMatrix
        elements = [float(x) for x in response.split(",")]
        rotation = array(elements[:9]).reshape((3,3))
        offset = array(elements[9:])
        return rotation, offset

    def GetNSCParameter(self, surf, obj, code) :
        cmd = "GetNSCParameter,%d,%d,%d" % (surf,obj,code)
        return self.req(cmd)

    def GetNSCProperty(self, surf, obj, code, face=None) :
        cmd = "GetNSCProperty,%d,%d,%d" % (surf,obj,code)
        if face is not None :
            cmd = "%s,%d" % (cmd, face)
        return self.req(cmd)

    def GetOperand(self, row, column) :
        # Column values :
        #  1 : type (string eg. "EFFL")
        #  2 : integer #1
        #  3 : integer #2
        #  4-7 : data #1-4
        #  8 : target
        #  9 : weight
        # 10 : value
        cmd = "GetOperand,%d,%d" % (row, column)
        response = self.req(cmd)
        return response

    def GetPath(self) :
        response = self.req("GetPath")
        paths = response.split(",")
        if len(paths) != 2 :
            raise AmbiguousString(response)
        data_path, lenses_path = paths
        return data_path, lenses_path
    
    @returns_error_status
    def GetRefresh(self, untraceable_allowed=False) :
        # Copies lens back from Lens Data Editor, then performs equivalent of GetUpdate
        error = int(self.req("GetRefresh"))
        if not untraceable_allowed and error :
            raise Untraceable()
        return error

    def GetSolve(self, surf, code) :
        cmd = "GetSolve,%d,%d" % (surf,code)
        response = self.req(cmd)
        return response

    def GetSurfaceData(self, surf, code) :
        cmd = "GetSurfaceData,%d,%d" % (surf,code)
        response = self.req(cmd)
        # manual lists all codes and the data type returned.
        # for now just return the response without conversion.
        return response

    def GetSurfaceParameter(self, surf, code) :
        cmd = "GetSurfaceParameter,%d,%d" % (surf,code)
        response = self.req(cmd)
        return response

    def GetSystem(self) :
        response = self.req("GetSystem")
        (numsurfs, unitcode, stopsurf, nonaxialflag, rayaimingtype, adjust_index,
         temp, pressure, globalrefsurf
         ) = response.split(",")
        # Zemax manual specifies 9 parameters but we only observe 8 (need_save missing)
        # unitcode : {0:mm, 1:cm, 2:in, 3:M}
        return (int(numsurfs), int(unitcode), int(stopsurf), int(nonaxialflag), int(rayaimingtype),
                int(adjust_index), float(temp), float(pressure), int(globalrefsurf))

    def GetSystemRaw(self) :
        response = self.req("GetSystem")
        return response.split(",")

    def GetSystemAper(self) :
        """Return information about the system aperture.

        Returns :
            (type, stopsurf, aperture_value)

        Where type takes values:
              0 : entrance pupil diameter   
              1 : image space f/#
              2 : object space NA
              3 : float by stop size
              4 : paraxial working f/#
              5 : object cone angle
        """        
        response = self.req("GetSystemAper")
        _type, _stopsurf, _aperture_value = response.split(",")
        return int(_type), int(_stopsurf), float(_aperture_value)

    def GetSystemProperty(self, code) :
        response = self.req("GetSystemProperty,%d" % code)
        return response
        
    def GetTextFile(self, path, type, settingspath, flag, **kwargs) :
        if flag == 2 :
            # Zemax creates a dialog box for the user to close. We need to wait for that.
            kwargs["timeout"] = 2**28
        response = self.req("GetTextFile,\"%s\",%s,\"%s\",%d" % (path, type, settingspath, flag), **kwargs)
        return response

    def GetTextFileString(self, type, settingspath=None, flag=0, timeout=120000) :
        """Returns the output of GetTextFile as a string."""
        with self.GetTextFileObject(type, settingspath, flag, timeout) as f :
            return f.read()

    @contextmanager
    def GetTextFileObject(self, type, settingspath=None, flag=0, timeout=120000) :
        """Returns the output of GetTextFile as a file-like context manager.

        This is useful when we want temporary file handling, but we want to handle the file one
        line at a time."""
        if settingspath is None :
            settingspath = ""
        elif not flag :
            # settingspath has been set.
            # For it to take effect, ensure flag is 1, otherwise Zemax default will be used
            flag = 1

        # Define custom stream object to decode the text file
        def decoded(f) :
            bom = f.read(2)
            f.seek(0)
            ## Older versions of Zemax wrote plain ascii files.
            ## The output txt file format can be selected in the preferences dialog box.
            if bom == codecs.BOM_UTF16 :
                reader = codecs.getreader("utf-16")
            else :
                reader = codecs.getreader("utf-8")
            return reader(f)

        def acquire(resultsf) :
            return self.GetTextFile(resultsf, type, settingspath, flag, timeout=timeout)

        # If the timeout expires here, Zemax will not have released the file for writing.
        # This means the tmpfile context manager will fail.
        # The work-around is to specify a longer timeout value on the request.
        # TODO: provide an option to prevent DDE request timeouts triggering before a resource (eg. temporary file) is released.
        with tmpfile_callback(acquire) as (response, f, path) :
            assert(response=="OK")
            yield decoded(f)

    def GetTrace(self, wave, mode, surf, h, p) :
        # mode: 0=real, 1=paraxial
        response = self.req("GetTrace,%d,%d,%d,%.20E,%.20E,%.20E,%.20E" %
                            (wave, mode, surf, h[0], h[1], p[0], p[1]))
        status, vigcode, x, y, z, l, m, n, l2, m2, n2, intensity = response.split(",")
        status = int(status)
        if status>0 :
            raise Untraceable(status)
        float_array = lambda a : array([float(e) for e in a])
        intersect = float_array((x, y, z))
        cosines = float_array((l, m, n))
        normal = float_array((l2, m2, n2))
        return status, int(vigcode), intersect, cosines, normal, float(intensity)

    def GetTraceDirect(self, wave, mode, startsurf, stopsurf, origin, cosines) :
        # mode: 0=real, 1=paraxial
        # startsurf : specifies the coordinate frame for origin and cosines
        #   (the ray does not interact with surface startsurf)
        cmd = "GetTraceDirect,%d,%d,%d,%d,%.20E,%.20E,%.20E,%.20E,%.20E,%.20E" % (
            wave, mode, startsurf, stopsurf,
            origin[0], origin[1], origin[2],
            cosines[0], cosines[1], cosines[2]
            )
        response = self.req(cmd)
        status, vigcode, x, y, z, l, m, n, l2, m2, n2, intensity = response.split(",")
        status = int(status)
        if status>0 :
            raise Untraceable(status)
        float_array = lambda a : array([float(e) for e in a])
        intersect = float_array((x, y, z))
        cosines = float_array((l, m, n))
        normal = float_array((l2, m2, n2))
        return status, int(vigcode), intersect, cosines, normal, float(intensity)        

    @returns_error_status      
    def GetUpdate(self, untraceable_allowed=False) :
        error = int(self.req("GetUpdate"))
        if not untraceable_allowed and error :
            raise Untraceable()
        return error

    def GetVersion(self) :
        return int(self.req("GetVersion"))

    def GetWavelengthsCount(self) :
        response = self.req("GetWave,0")
        primary, number = response.split(",")
        return int(primary), int(number)

    def GetWave(self, n) :
        response = self.req("GetWave,%d" % n)
        wavelength, weight = response.split(",")
        return float(wavelength), float(weight)        

    #@returns_error_status
    def InsertConfig(self, config) :
        return int(self.req("InsertConfig,%d" % config))

    def InsertMCO(self, operand) :
        # returns the new number of operands
        return int(self.req("InsertMCO,%d" % operand))

    def InsertMFO(self, operand) :
        # returns the new number of operands
        return int(self.req("InsertMFO,%d" % operand))

    def InsertObject(self, surf, obj) :
        return int(self.req("InsertObject,%d,%d" % (surf,obj)))

    def InsertSurface(self, surf) :
        #assert(surf>0) # Insertion fails silently for surf==0
        return int(self.req("InsertSurface,%d" % surf))

    @returns_error_status
    def LoadFile(self, filename, append=0, untraceable_allowed=False) :
        error = int(self.req("LoadFile,%s,%d" % (filename,append)))
        if error==-999 :
            raise IOError((error, "File cannot be loaded", filename))
        if not untraceable_allowed and error==-1 :
            raise Untraceable()
        return error

    def LoadMerit(self, filename) :
        response = self.req("LoadMerit,%s" % filename)
        numoperands, merit = response.split(",")
        # Manual states: If the merit function value is 9.00e+009, the merit function cannot be evaluated
        return (int(numoperands), float(merit))
    
    @returns_error_status
    def NewLens(self) :
        return int(self.req("NewLens"))

    def NSCDetectorData(self, surf, obj, pixel=0, data=0) :
        # if obj==0 : all detectors cleared
        # if obj==-x : detector x is cleared
        cmd = "NSCDetectorData,%d,%d,%d,%d" % (surf, obj, pixel, data)
        response = self.req(cmd)
        return float(response)
        
    def NSCTrace(self, surf=1, source=0, split=0, scatter=0, usepolar=1, ignore_errors=0,
                 no_random_seed=0, save=0, savefilename="", filter="", zrd_format=2,
                 timeout=600000) :
        args = (surf, source, split, scatter, usepolar, ignore_errors, no_random_seed, save, savefilename, filter, zrd_format)
        cmd = 'NSCTrace,%d,%d,%d,%d,%d,%d,%d,%d,%s,"%s",%d' % args
        response = self.req(cmd, timeout=timeout)
        return response
        
    def OperandValue(self, _type, *args) :
        cmd = "OperandValue,%s," % _type + ",".join(self._str(a) for a in args)
        response = self.req(cmd)
        return float(response)

    def Optimize(self, n=0, algorithm=0, timeout=600000) :
        # n - Defines number of optimisation cycles
        #  0 : Automatic
        #  >0 : Specified number of cycles
        #  <0 : Calculate current merit function value and return
        # Algorithm :
        #  0 : Damped least squares
        #  1 : Orthogonal descent
        response = self.req("Optimize,%d,%d" % (n,algorithm), timeout)
        if response == "9.0E+009" :
            raise Untraceable
        return float(response)

    @returns_error_status
    def PushLens(self, flag=0) :
        error = int(self.req("PushLens,%d" % flag))
        if error==-999 :
            raise Exception("Lens cannot be pushed into Lens Data Editor. This operation must be enabled in the Zemax preferences.")
        # error value has same semantics as GetUpdate        
        if error :
            raise Untraceable()
        return error

    def QuickFocus(self, mode=0, centroid=True) :
        """Perform a quick best focus of the system.

        mode :
            0 : RMS spot radius
            1 : spot x
            2 : spot y
            3 : wavefront OPD
        centroid :
            True : reference to image centroid
            False : reference to chief ray
        """
        response = self.req("QuickFocus,%d,%d" % (mode,int(centroid)))
        return response

    def RemoveVariables(self) :
        return self.req("RemoveVariables")

    @returns_error_status
    def SaveDetector(self, surf, obj, filename, timeout=60000) :
        error = self.req("SaveDetector,%d,%d,%s" % (surf, obj, filename), timeout=timeout)
        return int(error)

    @returns_error_status
    def SaveFile(self, filename, untraceable_allowed=False) :
        error = int(self.req("SaveFile,%s" % os.path.abspath(filename)))
        if error==-999 :
            raise IOError((error, "File cannot be loaded", filename))
        if not untraceable_allowed and not error==0 :
            raise Untraceable()
        return error
          
    def SetAperture(self, surf, _type, _min=0.0, _max=0.0, xdecenter=0.0, ydecenter=0.0, aperturefile="") :
        """Sets the surface aperture data.
        SetAperture(surf, _type, _min, _max, xdecenter, ydecenter, aperturefile)
        
        type : 
         0 : None
         1 : Circular
         2 : Circular obscuration
         3 : Spider
         4 : Rectangular
         5 : Rectangular obscuration
         6 : Elliptical
         7 : Elliptical obscuration
         8 : User defined
         9 : User defined obscuration
         10: Floating
        """
        response = self.req("SetAperture,%d,%d,%.20E,%.20E,%.20E,%.20E,%s" % (surf, _type, _min, _max, xdecenter, ydecenter, aperturefile))
        # we may not receive aperturefile
        items = response.split(",")
        _type, _min, _max, xdecenter, ydecenter = items[:5]
        try :
            aperturefile = items[5]
        except IndexError :
            aperturefile = None
        return int(_type), float(_min), float(_max), float(xdecenter), float(ydecenter), aperturefile

    def SetConfig(self, config, untraceable_allowed=False) :
        response = self.req("SetConfig,%d" % config)
        currentconfig, numberconfig, error = response.split(",")
        error = int(error)
        if not untraceable_allowed and error :
            raise Untraceable()
        return int(currentconfig), int(numberconfig), error

    def SetExtra(self, surf, column, value) :
        newvalue = self.req("SetExtra,%d,%d,%s" % (surf, column, self._str(value)))
        return newvalue

    def SetFieldsConfig(self, _type, _number, _normalization) :
        # _type :
        #  0 : angles in degrees
        #  1 : object height
        #  2 : paraxial image height
        #  3 : real image height
        # _number : number of fields defined
        # _normalization :
        #  0 : radial
        #  1 : rectangular
        response = self.req("SetField,0,%d,%d,%d" % (_type, _number, _normalization))
        return response

    def SetField(self, n, xf, yf, wgt=1.0, vdx=0.0, vdy=0.0, vcx=0.0, vcy=0.0, van=0.0) :
        assert(n > 0) # 0 gets configuration
        response = self.req("SetField,%d,%.20E,%.20E,%.20E,%.20E,%.20E,%.20E,%.20E,%.20E" % (n, xf, yf, wgt, vdx, vdy, vcx, vcy, van))
        xfield, yfield, weight, vdx, vdy, vcx, vcy, van = (float(n) for n in response.split(","))
        return xfield, yfield, weight, vdx, vdy, vcx, vcy, van

    def SetLabel(self, surf, label) :
        response = self.req("SetLabel,%d,%d" % (surf, label))
        newlabel = int(response)
        if not label==newlabel :
            raise ValueError("Label value (%d) not stored" % label)

    def SetMulticonOperand(self, row, operand_type, *args) :
        cmd = "SetMulticon,0,%d,%s" % (row, operand_type)
        cmd = ",".join([cmd]+ [self._str(a) for a in args])
        response = self.req(cmd)
        values = response.split(",")
        operand_type = values.pop(0)
##        ivalues = [int(x) for x in values]
##        # need to check for loss of precision
##        assert(all( i-float(v)==0 for i,v in zip(ivalues,values)))
##        return operand_type, ivalues
        v0, v1, v2 = values
        return operand_type, int(v0), int(v1), int(v2)

        
    def SetMulticon(self, config, row, value, status=0, pickuprow=1, pickupconfig=1, scale=1.0, offset=0.0) :
        assert(config) # use GetMulticonConfig to handle this
        cmd = "SetMulticon,%d,%d,%s,%d,%d,%d,%.20E,%.20E" % (config, row, self._str(value), status, pickuprow, pickupconfig, scale, offset)
        response = self.req(cmd)
        items = response.split(",")
        # _value, _num_config, _num_row, _status = items[:4]
        _value, _num_config, _num_row, _status, _pickuprow, _pickupconfig = items[:6]
        # Status :
        #  0 : fixed
        #  1 : variable
        #  2 : pickup
        #  3 : thermal pickup
        # 2,3 => _pickuprow, _pickupconfig indicate source
        try :
            _scale = float(items[6])
        except IndexError :
            _scale = None
            
        try :
            _offset = float(items[7])
        except IndexError :
            _offset = None
            
        return (
            _value, int(_num_config), int(_num_row),
            int(_status), int(_pickuprow), int(_pickupconfig), _scale, _offset            
            )

    def SetNSCObjectData(self, surf, obj, code, value) :
        cmd = "SetNSCObjectData,%d,%d,%d,%s" % (surf, obj, code, self._str(value))
        return self.req(cmd)

    def SetNSCParameter(self, surf, obj, param, value) :
        cmd = "SetNSCParameter,%d,%d,%d,%s" % (surf, obj, param, self._str(value))
        return self.req(cmd)

    def SetNSCPosition(self, surf, obj, code, value) :
        cmd = "SetNSCPosition,%d,%d,%d,%s" % (surf, obj, code, self._str(value))
        return self.req(cmd)
    
    def SetNSCProperty(self, surf, obj, code, face, value) :
        cmd = "SetNSCProperty,%d,%d,%d,%d,%s" % (surf, obj, code, face, self._str(value))
        return self.req(cmd)

    def SetOperand(self, row, column, value) :
        # Column values :
        #  1 : type (string eg. "EFFL")
        #  2 : integer #1
        #  3 : integer #2
        #  4-7 : data #1-4
        #  8 : target
        #  9 : weight
        cmd = "SetOperand,%d,%d,%s" % (row, column, self._str(value))
        response = self.req(cmd)
        return response

    def SetSolve(self, surf, code, *args) :
        # Sending undefined solvetype codes does not result in an error from Zemax
        cmd = "SetSolve,%d,%d," % (surf,code) + ",".join(self._str(a) for a in args)
        response = self.req(cmd)
        return response

    def SetSurfaceData(self, surf, code, data) :
        cmd = "SetSurfaceData,%d,%d,%s" % (surf,code,self._str(data))
        response = self.req(cmd)
        # response is usually the data value echoed back
        return response

    def SetSurfaceParameter(self, surf, code, data) :
        cmd = "SetSurfaceParameter,%d,%d,%s" % (surf,code,self._str(data))
        response = self.req(cmd)
        # response is usually the data value echoed back
        return response
    
    def SetSystem(self, unitcode, stopsurf, rayaimingtype, temp, pressure, globalrefsurf) :
        # argument #4 "useenvdata" is ignored, according to manual
        response = self.req("SetSystem,%d,%d,%d,0,%.20E,%.20E,%d" % (unitcode, stopsurf, rayaimingtype, temp, pressure, globalrefsurf))
        (numsurfs, unitcode, stopsurf, nonaxialflag, rayaimingtype, adjust_index,
         temp, pressure, globalrefsurf
        ) = response.split(",")
        # unitcode : {0:mm, 1:cm, 2:in, 3:m}
        return (int(numsurfs), int(unitcode), int(stopsurf), int(nonaxialflag), int(rayaimingtype),
                int(adjust_index), float(temp), float(pressure), int(globalrefsurf))

    def SetSystemRaw(self, *args) :
        cmd = ",".join(["SetSystem"] + list(args))
        response = self.req(cmd)
        return response.split(",")
        
    def SetSystemAper(self, _type, _stopsurf, _aperture_value) :
        response = self.req("SetSystemAper,%d,%d,%.20E" % (_type, _stopsurf, _aperture_value))
        _type, _stopsurf, _aperture_value = response.split(",")
        # type :
        #  0 : entrance pupil diameter
        #  1 : image space f/#
        #  2 : object space NA
        #  3 : float by stop size
        #  4 : paraxial working f/#
        #  5 : object cone angle
        return int(_type), int(_stopsurf), float(_aperture_value)

    def SetSystemProperty(self, code, *args) :
        values_str = ",".join(self._str(a) for a in args)
        cmd = "SetSystemProperty,%d,%s" % (code, values_str)
        response = self.req(cmd)
        return response

    def SetVig(self) :
        response = self.req("SetVig")
        return response

    def SetWavelengthsCount(self, primary, count) :
        response = self.req("SetWave,0,%d,%d" % (primary, count))
        _primary, _count = response.split(",")
        return _primary, _count

    def SetWave(self, n, wavelength, weight=1.0) :
        response = self.req("SetWave,%d,%.20E,%.20E" % (n, wavelength, weight))
        _wavelength, _weight = response.split(",")
        return _wavelength, _weight


if __name__=="__main__" :   
    z = Connection()
    print "Zemax Version : " + str(z.GetVersion())

