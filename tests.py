# Author: Darius Sullivan <darius.sullivan@thermo.com> Thermo Fisher Scientific (Cambridge, UK).
# $Rev: 351 $
# $Date: 2013-12-17 18:29:25 +0000 (Tue, 17 Dec 2013) $

# These unit tests require the Zemax application to be running.
# Run the tests with the command:
# $ python -m libzmx.tests

from __future__ import print_function
import zemaxclient
from zemaxclient import Connection, SurfaceLabelError
from libzmx import SurfaceSequence, return_to_coordinate_frame, SystemConfig, make_singlet, NamedElements
import libzmx
import surface
import unittest
import numpy
import os, time, tempfile
from itertools import count

## TODO :
##        - test for chief ray solves on coordinate break parameters

class ConnectionTestCase(unittest.TestCase) :
    def runTest(self) :
        z = Connection()
        self.assertTrue(z.GetVersion(), "Can't connect")

class CopyLensTestCase(unittest.TestCase) :
    def runTest(self) :
        z = Connection()

        response = z.NewLens()
        self.assertFalse(response, "Can't create new lens")

        # find number of surfaces
        response = z.GetSystem()
        numsurfs1 = response[0]

        response = z.InsertSurface(2)
        self.assertFalse(response, "Can't insert a surface")

        # check number of surfaces increased
        response = z.GetSystem()
        numsurfs2 = response[0]
        self.assertEqual(numsurfs2, numsurfs1+1, "Number of surfaces didn't increase")

        # copy lens to editor
        response = z.PushLens()
        self.assertFalse(response, "Can't push lens to editor window")

        response = z.NewLens()
        self.assertFalse(response, "Can't create new lens")
        
        response = z.GetSystem()
        self.assertNotEqual(response[0], numsurfs2,
                            "New lens has same number of surfaces as old (modified) one")

        # copy modified lens back into server memory        
        response = z.GetRefresh()

        # check it's our modified lens
        response = z.GetSystem()
        self.assertEqual(response[0], numsurfs2, "Didn't get our lens back")


class ClientSurfaceLabels(unittest.TestCase) :        
    def setUp(self) :
        self.z = Connection()
        self.n = self.z.GetSystem()[0]+1
        
        self.z.NewLens()
        for i in range(self.n) :
            self.z.SetLabel(i, 0)

    def setlabel(self, surf, label) :
        self.assertNotEqual(self.z.GetLabel(surf), label)
        self.z.SetLabel(surf, label)
        self.assertEqual(self.z.GetLabel(surf), label)
        self.assertEqual(self.z.FindLabel(label), surf, str(label))

    def testAll(self) :
        for exp in [2,16,31] :
            i = 2**exp-1
            self.setlabel(1, i)
            self.setlabel(1, -i)

    def testSurfaceSequence(self) :
        self.setlabel(1, SurfaceSequence.max_surf_id)
        

class ClientInsertSurface(unittest.TestCase) :
    """Check that we understand the semantics of the InsertSurface method

    Insert 0 => No effect
    Insert 1 => Adds surface after object
    Insert n-1 => Adds surface before image
    Insert i (where i>=n) => As Insert n-1
    """
    def setUp(self) :
        self.z = Connection()
        self.z.NewLens()
        #self.model = SurfaceSequence(self.z)
        self.n = self.get_len()
        self.original_label = 1
        self.new_label = 2

        for i in range(self.n) :
            self.z.SetLabel(i, self.original_label)

    def get_len(self) :
        response = self.z.GetSystem()
        return response[0]+1   

    def mark_new_surfaces(self) :
        for i in range(self.n) :
            if not self.z.GetLabel(i)==self.original_label :
                self.z.SetLabel(i, self.new_label)        
        
    def testAllLabels(self) :
        z = self.z
        n = self.n

        for i in range(self.n) :
            self.assertEqual(z.GetLabel(i), self.original_label)
        self.mark_new_surfaces()
        for i in range(self.n) :
            self.assertEqual(z.GetLabel(i), self.original_label)
                
    def testInsertAtZero(self) :
        z = self.z
        n = self.n

        # Insert at zero does nothing
        z.InsertSurface(0)

        self.assertEqual(n, self.get_len())

    def testInsertAtOne(self) :
        z = self.z
        n = self.n

        # Insert at 1 adds after object surface
        z.InsertSurface(1)

        self.assertEqual(n+1, self.get_len())
        self.mark_new_surfaces()
        self.assertEqual(z.GetLabel(1), self.new_label)

    def testInsertAtNminus1(self) :      
        z = self.z
        n = self.n

        # Insert at n-1 adds before image surface
        z.InsertSurface(n-1)

        self.assertEqual(n+1, self.get_len())
        self.mark_new_surfaces()
        #self.assertEqual(model[n-1].comment.value, self.new_label)
        self.assertEqual(z.GetLabel(n-1), self.new_label)
        
    def testInsertAt100(self) :      
        z = self.z
        n = self.n

        # Insert at i>>n adds before image surface
        z.InsertSurface(100)
        
        self.assertEqual(n+1, self.get_len())
        self.mark_new_surfaces()
        self.assertEqual(z.GetLabel(n-1), self.new_label)


class ClientDeleteSurface(unittest.TestCase) :
    """Check that we understand the semantics of the DeleteSurface method.

    Delete 0 => No effect
    Delete 1 => Delete surface 1 (first surface after object)
    Delete n-1 => Delete last surface (penultimate surface becomes image)
    Delete i (where i>=n) => As Delete n-1
    """
    def setUp(self) :
        self.z = Connection()
        self.z.NewLens()

        self.z.InsertSurface(1)
        self.z.InsertSurface(1)

        self.n = self.get_len()
        for i in range(self.n) :
            self.z.SetLabel(i, i)
        
    def get_len(self) :
        response = self.z.GetSystem()
        return response[0]+1   

    def ListLabels(self) :
        for i in range(self.get_len()) :
            print((i,self.z.GetLabel(i)))

    def testFind(self) :
        for i in range(self.n) :
            j = self.z.FindLabel(i)
            self.assertEqual(i, j)
        
    def testDeleteAtZero(self) :
        z = self.z
        n = self.n

        # Delete at zero does nothing
        z.DeleteSurface(0)

        self.assertEqual(n, self.get_len())

    def testDeleteAtOne(self) :
        z = self.z
        n = self.n

        # Delete at 1 deletes after object surface
        z.DeleteSurface(1)

        self.assertEqual(n-1, self.get_len())
        ## i=1 removed
        self.assertRaises(SurfaceLabelError, lambda : z.FindLabel(1))        

    def testDeleteAtEnd(self) :      
        z = self.z
        n = self.n

        # Delete at n-1 removes image surface
        z.DeleteSurface(n-1)

        self.assertEqual(n-1, self.get_len())
        ## i=n-1 removed
        self.assertRaises(SurfaceLabelError, lambda : z.FindLabel(n-1))
        
    def testDeleteAt100(self) :      
        z = self.z
        n = self.n

        # Delete at i>>n removes image surface
        z.DeleteSurface(100)

        self.assertEqual(n-1, self.get_len())
        ## i=n-1 removed
        self.assertRaises(SurfaceLabelError, lambda : z.FindLabel(n-1))


class SurfaceSequenceManipulate(unittest.TestCase) :
    """Check that semantics of SurfaceSequence are close to Python list type."""
    def setUp(self) :
        self.z = Connection()
        self.z.NewLens()
        self.model = SurfaceSequence(self.z, empty=True)
        self.model[0].comment.value = "OBJ"
        self.model[-1].comment.value = "IMG"
        self._list = ["OBJ", "IMG"]

    def verifyIdentical(self) :
        self.z.GetUpdate()
        self.assertEqual(len(self._list), len(self.model))
        for a, s in zip(self._list, self.model) :
            self.assertEqual(a, s.comment.value)

    def testInit(self) :
        self.verifyIdentical()

    def testInsert(self) :
        self.model.insert_new(1, surface.Standard, "Inserted 1")
        self._list.insert(1, "Inserted 1")
        
        self.model.insert_new(-1, surface.Standard, "Inserted -1")
        self._list.insert(-1, "Inserted -1")

        self.verifyIdentical()

    def testDelete(self) :
        self.model.insert_new(1, surface.Standard, "Inserted 1")
        self._list.insert(1, "Inserted 1")
        
        self.model.insert_new(-1, surface.Standard, "Inserted -1")
        self._list.insert(-1, "Inserted -1")

        self.verifyIdentical()

        del self.model[1]
        del self._list[1]

        self.verifyIdentical()

        del self.model[-2]
        del self._list[-2]

        self.verifyIdentical()

    def testGetItem(self) :
        self.model.insert_new(1, surface.Standard, "Inserted 1")
        self._list.insert(1, "Inserted 1")

        for i in range(len(self.model)) :       
            self.assertEqual(self.model[i].comment.value, self._list[i])
            self.assertEqual(self.model[-i].comment.value, self._list[-i])

    def testAppendItem(self) :
        ## Here the behaviour differs. The surface is inserted before the last (image) surface
        self.model.insert_new(1, surface.Standard, "Inserted 1")
        self._list.insert(1, "Inserted 1")

        self.model.append_new(surface.Standard, "Appended")
        self._list.insert(-1, "Appended")

        self.verifyIdentical()

    def testIndexing(self) :
        new_surf = self.model.insert_new(1, surface.Grating, "Inserted 1")
        indexed_surf = self.model[1]

        self.assertEqual(new_surf.id, indexed_surf.id) 
        # check that model retrieves surface object with correct class
        self.assertEqual(new_surf.__class__, indexed_surf.__class__)
        
                   
class SetSurfaceAttributes(unittest.TestCase) :    
    def runTest(self) :    
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        #id = model.insert_surface(1)
        #m1 = surface.Standard(z,id)
        m1 = model.insert_new(1, surface.Toroidal)
    
        m1.comment.value = "M1" 
        self.assertEqual( m1.comment.value, "M1" )
        
        m1.glass.value = "MIRROR"
        self.assertEqual( m1.glass.value, "MIRROR")
        
        m1.curvature.value = 1
        self.assertAlmostEqual(m1.curvature.value, 1)
        
        m1.ignored.value = True
        self.assertEqual(m1.ignored.value, True)
        
        m1.semidia.value = 2
        self.assertAlmostEqual(m1.semidia.value, 2)
        
        m1.thermal_expansivity.value = .001
        self.assertAlmostEqual(m1.thermal_expansivity.value, .001)
        
        m1.coating.value = "METAL"
        self.assertEqual(m1.coating.value, "METAL")

        # "extra" type parameters
        m1.num_poly_terms = 11
        self.assertEqual(m1.num_poly_terms.value, 11)
    
        m1.norm_radius = 123.0
        self.assertAlmostEqual(m1.norm_radius.value, 123.0)

        def access_missing_attr() :
            item =  m1.this_will_never_ever_exist
            print("Item : " + str(item))
            return item
        self.assertRaises(AttributeError, access_missing_attr)

        def access_missing_attr_linked() :
            item = m1.this_will_never_ever_exist_linked
            return item
        self.assertRaises(AttributeError, access_missing_attr_linked)        


class SetExtraAttributes(unittest.TestCase) :    
    def runTest(self) :    
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        # setting the extra parameter on surface creation requires surface type to be set first, internally
        m1 = model.insert_new(1, surface.Toroidal, num_poly_terms=11)
    
        self.assertEqual(m1.num_poly_terms.value, 11)

        
class SetSurfaceAttributesOnInitialisation(unittest.TestCase) :    
    def runTest(self) :    
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        m1 = model.insert_new(1, surface.Standard, "M1", glass="MIRROR", curvature=1, ignored=True, semidia=2,
                             thermal_expansivity=.001, coating="METAL")
    
        self.assertEqual( m1.comment.value, "M1" )
        self.assertEqual( m1.glass.value, "MIRROR")
        self.assertAlmostEqual(m1.curvature.value, 1)
        self.assertEqual(m1.ignored.value, True)
        self.assertAlmostEqual(m1.semidia.value, 2)
        self.assertAlmostEqual(m1.thermal_expansivity.value, .001)
        self.assertEqual(m1.coating.value, "METAL")

                
class AccessSurfaceAttributes(unittest.TestCase) :    
    def runTest(self) :    
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        m1 = model.insert_new(1, surface.Standard)

        m1.coating.set_value("METAL")
        self.assertEqual(m1.coating.value, "METAL")
        self.assertEqual(m1.coating.get_value(), "METAL")

        # We allow direct access to attributes values (similar to Django Model)
        m1.coating = "METAL2"
        self.assertEqual(m1.coating.value, "METAL2")
        self.assertEqual(repr(m1.coating), repr("METAL2"))
        self.assertEqual(str(m1.coating), "METAL2")

        thickness = 3.1
        m1.thickness = thickness
        self.assertAlmostEqual(m1.thickness.value, thickness)
        self.assertAlmostEqual(float(repr(m1.thickness)), thickness)
        self.assertAlmostEqual(float(str(m1.thickness)), thickness)
        
class SetSurfacePickups(unittest.TestCase) :
    def setUp(self) :
        self.z = Connection()
        self.z.NewLens()
        model = SurfaceSequence(self.z)

        m1 = model.insert_new(1, surface.Toroidal)    
        m1.comment.value = "M1" 
        m1.glass.value = "MIRROR"
        m1.curvature.value = 1
        m1.conic.value = 0.1
        m1.ignored.value = True
        m1.semidia.value = 2
        m1.thermal_expansivity.value = .001
        m1.coating.value = "METAL"
        m1.thickness.value = 30
        m1.norm_radius = 123.0
        m1.num_poly_terms = 5

        self.m1 = m1
        self.m2 = model.insert_new(-1, surface.Toroidal)

        cb1 = model.insert_new(-1, surface.CoordinateBreak)
        cb1.rotate_x.value = 34
        cb1.rotate_y.value = 42
        cb1.rotate_z.value = 83
        cb1.offset_x.value = 2.63
        cb1.offset_y.value = 753.3
        cb1.thickness.value = 322.3
        
        self.cb1 = cb1
        self.cb2 = model.insert_new(-1, surface.CoordinateBreak)

    def testIdenticalColRefs(self) :    
        z = self.z
        m1 = self.m1
        m2 = self.m2

        m2.semidia.value = 3*m1.semidia.linked()
        z.GetUpdate()
        self.assertAlmostEqual( m2.semidia.value, 3*m1.semidia.value)

        m2.curvature.value = 2*(+m1.curvature.linked())
        z.GetUpdate()
        self.assertAlmostEqual( m2.curvature.value, 2*(+m1.curvature.value))
               
        m2.thickness.value = 10 - (-m1.thickness.linked()/2.0)
        z.GetUpdate()
        self.assertAlmostEqual( m2.thickness.value, 10 - (-m1.thickness.value/2.0))

        m2.glass.value = m1.glass.linked()
        z.GetUpdate()
        self.assertEqual(m1.glass.value, m2.glass.value)

        m2.conic.value = 4*m1.conic.linked()
        z.GetUpdate()
        self.assertAlmostEqual( m2.conic.value, 4*m1.conic.value)
        
        # "extra" type parameters
        m2.norm_radius = 0.7*m1.norm_radius.linked()
        z.GetUpdate()
        self.assertAlmostEqual( m2.norm_radius.value, 0.7*m1.norm_radius.value)

        m2.num_poly_terms = 2*m1.num_poly_terms.linked()
        z.GetUpdate()
        self.assertEqual(m2.num_poly_terms.value, 2*m1.num_poly_terms.value)
        
        # check we catch inappropriate pickup expressions
        # (offsets, where only scaling permitted).
        def offset1() :
            m2.semidia.value = 1 + m1.semidia.linked()
        self.assertRaises(TypeError, offset1)

        def offset2() :
            m2.curvature.value = 1 + m1.curvature.linked()
        self.assertRaises(TypeError, offset2)

    def testOtherColRefs(self) :
        z = self.z
        m1 = self.m1
        m2 = self.m2
        cb1 = self.cb1
        cb2 = self.cb2

        # Check we can dereference SurfaceParameter instances
        cb2.offset_x = 1 - 2*m1.thickness.linked()
        z.GetUpdate()
        self.assertAlmostEqual( cb2.offset_x.value, 1 - 2*m1.thickness.value)

        # Check we can dereference SurfaceAuxParameter instances
        cb2.rotate_x = 1 - 2*cb1.rotate_y.linked()
        z.GetUpdate()
        self.assertAlmostEqual( cb2.rotate_x.value, 1 - 2*cb1.rotate_y.value)
        
        # Check we can dereference columns from the same surface
        self.assertNotAlmostEqual( cb1.rotate_x.value, cb1.rotate_y.value)
        cb1.rotate_y = cb1.rotate_x.linked()
        z.GetUpdate()
        self.assertAlmostEqual( cb1.rotate_x.value, cb1.rotate_y.value)
        

class NamedSurfaces(unittest.TestCase) :    
    def testTagging(self) :    
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)
        els = NamedElements(model)

        surf = model.insert_new(1, surface.Standard)
        
        comment = "first comment"
        surf.comment = comment

        # if no tag set, comment matches "comment" verbatim
        self.assertEqual(comment, surf.comment._client_get_value())
        self.assertEqual(comment, surf.comment.value)

        # Setting the surface as an attribute of a NamedElements instance,
        # causes the name to be stored as a tag on the surface.
        els.m1 = surf
        # value in zemax model now has tag embedded
        self.assertNotEqual(comment, surf.comment._client_get_value())
        # the tag is invisible in the value of comment
        self.assertEqual(comment, surf.comment.value)
        # the tag can be accessed, however
        self.assertEqual("m1", surf.comment.tag)

        # Updating the comment does not alter the tag
        comment = "second comment"
        self.assertNotEqual(comment, surf.comment.value)
        surf.comment = comment
        self.assertEqual(comment, surf.comment.value)
        # the tag is unchanged
        self.assertEqual("m1", surf.comment.tag)

        # we can access the surface as a property of a newly-created NamedElements instance
        els2 = NamedElements(model)
        self.assertEqual(comment, els2.m1.comment.value)
        self.assertEqual(surf.id, els2.m1.id)

        # named surfaces can be discovered in models
        self.assertTrue("m1" in dir(els2))

    def testSaving(self) :
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        # Zemax surface comments must be 32 characters or less, to survive saving and reloading
        surf = model.insert_new(1, surface.Standard)
        id = surf.id
        comment = "c"*20
        tag = "t"*9
        surf.comment = comment
        surf.comment.tag = tag

        self.assertEqual(len(surf.comment._client_get_value()), libzmx.CommentParameter.max_len)

        # Surface can be retrieved from unsaved model
        els = NamedElements(model)
        self.assertEqual(id, getattr(els, tag).id)

        # Save model
        (fd, modelf) = tempfile.mkstemp(".ZMX")
        z.SaveFile(modelf)

        n = len(model)
        z.NewLens()
        self.assertNotEqual(n, len(model))

        # Reload model
        z.LoadFile(modelf)
        els2 = NamedElements(model)

        # Comment and tag are intact
        s2 = getattr(els2, tag)
        self.assertEqual(id, s2.id)
        self.assertEqual(s2.comment.value, comment)

        os.close(fd)
        os.remove(modelf)

    def testLimitLength(self) :
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        # Zemax surface comments must be 32 characters or less, to survive saving and reloading
        surf = model.insert_new(1, surface.Standard)
        def set_comment() :
            surf.comment = "z" * (libzmx.CommentParameter.max_len+1)
        self.assertRaises(ValueError, set_comment)

        comment = "c"*20
        tag = "t"*10
        surf.comment = comment
        def set_tag() :
            surf.comment.tag = tag
        self.assertRaises(ValueError, set_tag)


class Optimisation(unittest.TestCase) :    
    def runTest(self) :    
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z)

        #id = model.insert_surface(1)
        #m1 = surface.Standard(z,id)
        s = model.insert_new(1, surface.Standard)

        # there are no adjustable variables        
        self.assertEqual(0, len(s.fix_variables()))

        # make some parameters adjustable
        s.thickness.vary()
        s.curvature.vary()
        
        # there are some adjustable variables
        self.assertEqual(2, len(s.fix_variables()))
        # adjustable variables are now fixed
        self.assertEqual(0, len(s.fix_variables()))
    
def build_coord_break_sequence(model) :
        s = model[0]
        s.thickness.value = 1

        insertion_point = -1

        #id = model.insert_surface(insertion_point)
        #s = surface.Standard(self.z,id)
        s = model.insert_new(insertion_point, surface.Standard)
        s.thickness.value = 5
        first = s.get_surf_num()

        #id = model.insert_surface(insertion_point)
        #s = surface.CoordinateBreak(self.z,id)
        s = model.insert_new(insertion_point, surface.CoordinateBreak)
        s.rotate_x.value = 34
        s.rotate_y.value = 42
        s.rotate_z.value = 83
        s.offset_x.value = 2.63
        s.offset_y.value = 753.3
        s.thickness.value = 322.3

        #id = model.insert_surface(insertion_point)
        #s = surface.CoordinateBreak(self.z,id)
        s = model.insert_new(insertion_point, surface.CoordinateBreak)
        s.rotate_x.value = 75
        s.rotate_y.value = 85
        s.rotate_z.value = 21
        s.offset_x.value = 543.64
        s.offset_y.value = 654.32
        s.thickness.value = 543.43
        s.rotate_before_offset.value = True

        #id = model.insert_surface(insertion_point)
        #s = surface.CoordinateBreak(self.z,id)
        s = model.insert_new(insertion_point, surface.CoordinateBreak)
        s.rotate_x.value = 34
        s.rotate_y.value = 65
        s.rotate_z.value = 84
        s.offset_x.value = 543.324
        s.offset_y.value = 43.23
        s.thickness.value = 0
        s.rotate_before_offset.value = True

        #id = model.insert_surface(insertion_point)
        #s = surface.Standard(self.z,id)
        s = model.insert_new(insertion_point, surface.Standard)
        s.thickness.value = -38.21

        #id = model.insert_surface(insertion_point)
        #s = surface.CoordinateBreak(self.z,id)
        s = model.insert_new(insertion_point, surface.CoordinateBreak)
        s.rotate_x.value = 54
        s.rotate_y.value = 88
        s.rotate_z.value = 22
        s.offset_x.value = 43.85
        s.offset_y.value = 92.84
        s.thickness.value = 0
        
        #id = model.insert_surface(insertion_point)
        #s = surface.CoordinateBreak(self.z,id)
        s = model.insert_new(insertion_point, surface.CoordinateBreak)
        s.rotate_x.value = 34
        s.rotate_y.value = 43
        s.rotate_z.value = 54
        s.offset_x.value = 643.54
        s.offset_y.value = 127.3
        s.thickness.value = 23.63

        #id = model.insert_surface(insertion_point)
        #s = surface.CoordinateBreak(self.z,id)
        s = model.insert_new(insertion_point, surface.CoordinateBreak)
        s.rotate_x.value = 0
        s.rotate_y.value = 0
        s.rotate_z.value = 0
        s.offset_x.value = 0
        s.offset_y.value = 0
        s.thickness.value = 23.63

        #id = model.insert_surface(insertion_point)
        #s = surface.Standard(self.z,id)
        s = model.insert_new(insertion_point, surface.Standard)
        s.thickness.value = 3.6

        last = s.get_surf_num()
        return (first, last)

class CoordinateReturn(unittest.TestCase) :
    def setUp(self) :    
        self.z = Connection()
        self.z.NewLens()
        self.model = SurfaceSequence(self.z, empty=True)
        self.first, self.last = build_coord_break_sequence(self.model)

    def testZemaxCoordinateReturn(self) :
        cb = self.model.append_new(surface.CoordinateBreak)
        return_surf = cb.get_surf_num()
        self.z.SetSurfaceData(return_surf, 81, self.first)
        self.z.SetSurfaceData(return_surf, 80, 3) # orientation + offset
        self.z.GetUpdate()
        self.coord_return_common_tests(return_surf)

    def testLibraryCoordinateReturn(self) :
        cb = self.model.append_new(surface.CoordinateBreak)
        cb.return_to(self.model[self.first])
        self.z.GetUpdate()
        self.coord_return_common_tests(cb.get_surf_num())
        ## To unset the coordinate return, pass None (has no effect here)
        cb.return_to(None) # unset coordinate return status

    def testFull(self) :
        return_surf = return_to_coordinate_frame(self.model, self.first, self.last)
        self.z.GetUpdate()
        self.coord_return_common_tests(return_surf)

    def testOmitZeroThicknesses(self) :
        self.z.GetUpdate()
        return_surf = return_to_coordinate_frame(self.model, self.first, self.last, include_null_transforms=False)
        self.z.GetUpdate()
        self.coord_return_common_tests(return_surf)

    def testWithCursor(self) :
        insert_point = self.last
        insertion_point_sequence = count(insert_point+1)
        def factory() :
            return self.model.insert_new(next(insertion_point_sequence), surface.CoordinateBreak)

        self.z.GetUpdate()
        return_surf = return_to_coordinate_frame(self.model, self.first, self.last, include_null_transforms=False, factory=factory)
        self.z.GetUpdate()
        self.coord_return_common_tests(return_surf)

    def testWithAppend(self) :
        def factory() :
            return self.model.append_new(surface.CoordinateBreak)
        self.z.GetUpdate()
        return_surf = return_to_coordinate_frame(self.model, self.first, self.last, include_null_transforms=False, factory=factory)
        self.z.GetUpdate()
        self.coord_return_common_tests(return_surf)

    def coord_return_common_tests(self, return_surf) :
        first_rot, first_offset = self.z.GetGlobalMatrix(self.first)
        last_rot, last_offset = self.z.GetGlobalMatrix(self.last)        
        return_rot, return_offset = self.z.GetGlobalMatrix(return_surf + 1)

        # check coordinate frames are identical
        self.assertAlmostEqual( abs(first_rot - return_rot).max(), 0)
        self.assertAlmostEqual( abs(first_offset - return_offset).max(), 0)

        # check we have finite rotation matrices
        self.assertNotAlmostEqual( abs(first_rot).max(), 0)

        # check that first and last frames differ
        self.assertNotAlmostEqual( abs(first_rot - last_rot).max(), 0)
        self.assertNotAlmostEqual( abs(first_offset - last_offset).max(), 0)


class ChangeGlobalReferenceSurface(unittest.TestCase) :
    def runTest(self) :
        z = Connection()
        z.NewLens()
        model = SurfaceSequence(z, empty=True)
        build_coord_break_sequence(model)

        # set each surface to be the global reference, in turn
        last = None
        for surf in model :
            surf.make_global_reference()
            self.assertTrue(surf.is_global_reference)
            if last is not None :
                self.assertFalse(last.is_global_reference)
            rot, offset = z.GetGlobalMatrix(surf.get_surf_num())
            self.assertAlmostEqual( abs(rot - numpy.eye(3)).max(), 0)
            self.assertAlmostEqual( abs(offset).max(), 0)
            last = surf
            
        
class ConfigureSystemParameters(unittest.TestCase) :    
##    numsurfs = SystemParameter(0, int)
##    unitcode = SystemParameter(1, int)
##    stopsurf = SystemParameter(2, int)
##    nonaxialflag = SystemParameter(3, bool)
##    rayaimingtype = SystemParameter(4, int)
##    adjustindex = SystemParameter(5, bool)
##    temperature = SystemParameter(6, float)
##    pressure = SystemParameter(7, float)
##    globalrefsurf = SystemParameter(8, float)

    def setUp(self) :    
        self.z = Connection()
        self.z.NewLens()
        self.system = SystemConfig(self.z)
        self.model = SurfaceSequence(self.z)

    def testSurfaceNumbers(self) :
        n = self.system.numsurfs
        self.assertEqual(n, 2)
        self.model.append_new(surface.Standard)
        self.assertEqual(n+1, self.system.numsurfs)
            
    def testGlobalReferenceSurface(self) :
        newglref = 2
        oldglref = self.system.globalrefsurf
        self.assertNotEqual(newglref, oldglref)
        self.system.globalrefsurf = newglref
        #self.z.GetUpdate()
        self.assertEqual(self.system.globalrefsurf, newglref)

    def testStopSurface(self) :
        newstop = 2
        oldstop = self.system.stopsurf
        self.assertNotEqual(newstop, oldstop)
        self.system.stopsurf = newstop
        self.assertEqual(self.system.stopsurf, newstop)

    def testAdjustIndex(self) :
        old = self.system.adjustindex
        new = not old
        self.system.adjustindex = new
        self.assertEqual(self.system.adjustindex, new)

    def testTemperature(self) :
        new = -40.0
        old = self.system.temperature
        self.assertNotAlmostEqual(new, old)
        self.system.temperature = new
        self.assertAlmostEqual(new, self.system.temperature)

    def testPressure(self) :
        new = 1.1
        old = self.system.pressure
        self.assertNotAlmostEqual(new, old)
        self.system.pressure = new
        self.assertAlmostEqual(new, self.system.pressure)

    def testRayAiming(self) :
        new = 1
        old = self.system.rayaimingtype
        self.assertNotEqual(new, old)
        self.system.rayaimingtype = new
        self.assertEqual(self.system.rayaimingtype, new)


class RayCoordinates(unittest.TestCase) :
    marginal_ray_solve_pupil_coordinate = 0.7
    tracing_accuracy = 4 # expected accuracy in decimal places  
    def setUp(self) :    
        self.z = Connection()
        self.z.NewLens()
        self.model = SurfaceSequence(self.z)
        self.system = SystemConfig(self.z)
        self.system.rayaimingtype = 0

        self.model[0].thickness = 10.0

        # insert fold mirror
        self.model.append_new(surface.CoordinateBreak, rotate_y=40.0, rotate_z=10.0)
        self.model.append_new(surface.Standard, glass="MIRROR")
        cb = self.model.append_new(surface.CoordinateBreak, thickness=-20.0)
        cb.rotate_x.align_to_chief_ray()
        cb.rotate_y.align_to_chief_ray()

        front = self.model.append_new(surface.Standard, curvature=-0.05, glass="BK7", thickness=-1.0)
        back = self.model.append_new(surface.Standard, curvature=-front.curvature.linked())

        self.z.SetSystemAper(3, front.get_surf_num(), 2.5)
        back.thickness.focus_on_next(self.marginal_ray_solve_pupil_coordinate)

        self.z.GetUpdate()        

    def testFocus(self) :
        image = self.model[-1]
        chief = image.get_ray_intersect()
        marginal = image.get_ray_intersect(
            (0,0), (0,self.marginal_ray_solve_pupil_coordinate), 0)
        self.assertAlmostEqual(abs(marginal.intersect-chief.intersect).max(), 0.0)

    def testDirectTracing(self) :
        """Verify that we can launch rays using normalised pupil coordinates and local
        surface cartesian coordinates, with consistent results."""
        
        pc = (0.3, 0.5) # normalised pupil coordinate under test
        image = self.model[-1]
        # find ray intersection on image plane
        (status, vigcode, im_intersect, im_exit_cosines, normal, intensity) = image.get_ray_intersect((0,0), pc)
        for surf in self.model :
            # get ray intersection on surface
            (status, vigcode, surf_intersect, exit_cosines, normal, intensity) = surf.get_ray_intersect((0,0), pc)

            # launch ray directly using the obtained origin and exit cosines.
            # GetTraceDirect launches a ray from startsurf coordinate frame, but the ray does not interact with startsurf
            status, vigcode, intersect, cosines, normal, intensity = self.z.GetTraceDirect(
                0, 0, surf.get_surf_num(), image.get_surf_num(), surf_intersect, exit_cosines)
            
            # verify that the ray is the same as obtained with normalised pupil coordinates on the image plane
            self.assertAlmostEqual(abs(intersect - im_intersect).max(), 0.0, self.tracing_accuracy)
            self.assertAlmostEqual(abs(cosines - im_exit_cosines).max(), 0.0, self.tracing_accuracy)
            if surf.id != image.id :
                self.assertNotAlmostEqual(abs(surf_intersect - im_intersect).max(), 0.0, self.tracing_accuracy)

    def testMatrixCoordinateTransforms(self) :
        """Check we can acquire and use global transformation matrices.

        Make each surface the coordinate global reference in turn.
        For each iteration check we can recover the original global reference of each surface by applying the inverse of the
        new global reference."""
        def trans_mat(rotation, offset) :
            m = numpy.zeros((4,4),float)
            m[0:3,0:3] = rotation
            m[0:3,3] = offset
            m[3,3] = 1.0
            return numpy.matrix(m)

        surf_ids = range(len(self.model))
        initial_global_ref = self.system.globalrefsurf
        initial_surface_coord_frames = [trans_mat(*self.z.GetGlobalMatrix(i)) for i in surf_ids]
        
        for i in surf_ids :
            if isinstance(self.model[i], surface.CoordinateBreak) :
                # coordinate breaks as global reference surfaces give unexpected results
                continue
            
            self.system.globalrefsurf = i
            # find inverse transformation
            trans = initial_surface_coord_frames[i].I

            self.z.GetUpdate()
            for j in surf_ids :
                new_frame = trans_mat(*self.z.GetGlobalMatrix(j))
                #calc_frame = numpy.dot(trans, initial_surface_coord_frames[j])
                calc_frame = trans * initial_surface_coord_frames[j]
                self.assertAlmostEqual(abs(new_frame - calc_frame).max(), 0)

    def testCheckRayTraceResults(self) :
        pc = (0.3, 0.5) # normalised pupil coordinate under test
        for surf in self.model :
            n = surf.get_surf_num()
            # get ray intersection on surface in local coordinates
            #(status, vigcode, intersect, exit_cosines, normal, intensity) = surf.get_ray_intersect((0,0), pc)
            ray = surf.get_ray_intersect((0,0), pc)
            # compare with values obtained from operands
            for val, op in zip(ray.intersect, ("REAX", "REAY", "REAZ")) :
                opval = self.z.OperandValue(op, n, 0, 0.0, 0.0, pc[0], pc[1])
                self.assertAlmostEqual(opval, val, places=5)

            # get ray intersection on surface in global coordinates
            #(status, vigcode, intersect_gl, exit_cosines, normal, intensity) = surf.get_ray_intersect((0,0), pc, _global=True)
            glray = surf.get_ray_intersect((0,0), pc, _global=True)
            # compare with direct global coordinates from operands            
            for val, op in zip(glray.intersect, ("RAGX", "RAGY", "RAGZ")) :
                opval = self.z.OperandValue(op, n, 0, 0.0, 0.0, pc[0], pc[1])
                self.assertAlmostEqual(opval, val, self.tracing_accuracy)
             

class Temporaryfile(unittest.TestCase) :
    def testOpenWithError(self) :
        def open_tmpfile_with_error() :
            def fails(path) :
                self.path = path
                assert(False)
            with zemaxclient.tmpfile_callback(fails) as (response, f, path) :
                # never get here
                self.assertTrue(False)

        # if temporary file cannot be removed, this will raise WindowsError instead
        self.assertRaises(AssertionError, open_tmpfile_with_error)
        # check that file was removed despite the AssertionError
        self.assertFalse(os.path.exists(self.path))

    def testRemovedWhenNoError(self) :
        with zemaxclient.tmpfile_callback(len) as (response, f, path) :
            self.assertTrue(os.path.exists(path))

        self.assertFalse(os.path.exists(path))

    def testPrematureRemove(self) :
        z = Connection()

        def open_tmpfile_and_delete() :
            with zemaxclient.tmpfile_callback(os.remove) as (response, f) :
                pass

        # if temporary file cannot be removed, this will raise WindowsError
        self.assertRaises(WindowsError, open_tmpfile_and_delete)
 
    
class ZemaxTextOutput(unittest.TestCase) :
    def setUp(self) :
        self.z = Connection()
        self.z.NewLens()

    def testSpt(self) :
        text = self.z.GetTextFileString("Spt")
        nlines = len(text.splitlines())
        # simply check we received a number of lines
        self.failUnless(nlines>=23, "Received %d lines"%nlines)

    def testPre(self) :
        text = self.z.GetTextFileString("Pre")
        first = text.splitlines()[0]
        self.assertEqual(u"System/Prescription Data", unicode(first))

    def testContext(self) :
        with self.z.GetTextFileObject("Pre") as f :
            first = next(f).strip()
        self.assertEqual(u"System/Prescription Data", first)

      
class ExportModelToCAD(unittest.TestCase) :
    def setUp(self) :
        self.z = Connection()
        self.model = SurfaceSequence(self.z, empty=True)
        make_singlet(self.z)

    def testLength(self) :
        self.assertEqual(len(self.model), 4)

    def testExport(self) :
        (fd, resultsf) = tempfile.mkstemp(".IGS")
        
        response = self.z.ExportCAD(resultsf,0)
        self.assertEqual(response.split()[0], "Exporting")
        
        while self.z.ExportCheck() : time.sleep(0.2)

        # check exported file is not empty
        sz = os.stat(resultsf).st_size
        self.assertNotEqual(sz, 0)
        
        os.close(fd)
        os.remove(resultsf)

        
if __name__=="__main__" :
    print("Please ensure Zemax is in sequential mode before running the unit tests")
    unittest.main()
