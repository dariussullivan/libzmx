from libzmx import *

# It's hard to handle Nonsequential object references as gracefully as sequential surface references because there is no
# Set/Get/FindLabel method for them.
# Still, there's probably a better approach than the one taken here.

class NonSequentialComponent(UnknownSurface) :
    surface_type = "NONSEQCO"

    draw_ports = Property(AuxParameter, 0)
    offset_x = Property(AuxParameter, 1)
    offset_y = Property(AuxParameter, 2)
    offset_z = Property(AuxParameter, 3)
    rotate_x = Property(AuxParameter, 4)       
    rotate_y = Property(AuxParameter, 5)
    rotate_z = Property(AuxParameter, 6)
    rotate_before_offset = Property(AuxParameter, 7, bool)
    reverse_rays = Property(AuxParameter, 8, bool)

    def __len__(self) :
        return self.conn.GetNSCData(self.get_surf_num())

    def get_object_type(self, id) :
        return self.conn.GetNSCProperty(self.get_surf_num(), id, 0)

    def get_obj_param(self, slot, param) :
        n = self.get_surf_num()
        return self.conn.GetNSCParameter(n, slot, param)

    def set_obj_param(self, slot, param, val) :
        n = self.get_surf_num()
        self.conn.SetNSCParameter(n, slot, param, val)

    def get_obj_property(self, slot, param, face=0) :
        n = self.get_surf_num()
        return self.conn.GetNSCProperty(n, slot, param, face)

    def set_obj_property(self, slot, param, value, face=0) :
        n = self.get_surf_num()
        self.conn.SetNSCProperty(n, slot, param, face, value)

    def set_obj_comment(self, slot, comment) :
        self.conn.SetNSCObjectData(self.get_surf_num(), slot, 1, comment)

    def set_obj_material(self, slot, material) :
        self.conn.SetNSCPosition(self.get_surf_num(), slot, 7, material.upper())

    def set_obj_ref(self, slot, ref) :
        self.conn.SetNSCObjectData(self.get_surf_num(), slot, 5, ref)

    def set_obj_position(self, slot, offset_x=None, offset_y=None, offset_z=None, rotate_x=None, rotate_y=None, rotate_z=None) :
        args = [offset_x, offset_y, offset_z, rotate_x, rotate_y, rotate_z]
        for i, val in enumerate(args) :
            if val is None : continue
            self.conn.SetNSCPosition(self.get_surf_num(), slot, i+1, val)

    def set_obj_aperture_file(self, slot, path) :
        self.conn.SetNSCObjectData(self.get_surf_num(), slot, 4, path)
        self.conn.SetNSCObjectData(self.get_surf_num(), slot, 3, 1) # enable

    def set_obj_ignored(self, slot, ignore, on_launch_only=False) :
        status = 0
        if ignore :
            status = 1
            if on_launch_only :
                status = 2
        return int(float(self.conn.SetNSCProperty(self.get_surf_num(), slot, 16, 0, status)))

    def insert_obj(self, slot, _type="NSC_NULL") :
        self.conn.InsertObject(self.get_surf_num(), slot)
        self.conn.SetNSCObjectData(self.get_surf_num(), slot, 0, _type)
        #self.conn.SetNSCProperty(self.get_surf_num(), slot, 0, 0, _type)
        return slot

    def insert_std_surf(self, slot, comment=None, radius=None, conic=None, max_aper=None) :
        slot = self.insert_obj(slot, "NSC_SSUR")
        if comment :
            self.set_obj_comment(slot, comment)
        if radius :
            self.set_obj_param(slot, 1, radius)
        if conic :
            self.set_obj_param(slot, 2, conic)
        if max_aper :
            self.set_obj_param(slot, 3, max_aper)
        return slot
        
    def insert_toroidal_surf(self, slot, comment=None, radius=None, radius_of_rotation=None, hwidth_x=None, hwidth_y=None) :
        slot = self.insert_obj(slot, "NSC_TSUR")
        if comment :
            self.set_obj_comment(slot, comment)
        if radius :
            self.set_obj_param(slot, 6, radius)
        if radius_of_rotation :
            self.set_obj_param(slot, 5, radius_of_rotation)
        if hwidth_x :
            self.set_obj_param(slot, 1, hwidth_x)
        if hwidth_y :
            self.set_obj_param(slot, 1, hwidth_y)
        return slot
        
    def insert_imported(self, slot, path) :
        ret = self.insert_obj(slot, "NSC_IMPT")
        n = self.get_surf_num()
        self.set_obj_comment(slot, path)
        self.conn.SetNSCParameter(n, slot, 1, 1.0)
        return ret

    def insert_drect(self, slot, comment=None, n_pixels_x=None, n_pixels_y=None) :
        slot = self.insert_obj(slot, "NSC_DETE")
        if comment :
            self.set_obj_comment(slot, comment)
        if n_pixels_x :
            self.set_obj_param(slot, 3, n_pixels_x)
        if n_pixels_y :
            self.set_obj_param(slot, 4, n_pixels_y)
        return slot
        
    def insert_src_rect(self, slot) :
        return self.insert_obj(slot, "NSC_SRCR")

    def insert_two_angle_src(self, slot, half_widths, half_angles, src_is_rectangle=True, ang_distr_is_rect=False) :
        slot = self.insert_obj(slot, "NSC_SR2A")
        # Source size
        (hwx, hwy) = half_widths
        self.set_obj_param(slot, 6, hwx) 
        self.set_obj_param(slot, 7, hwy)
        # Size of angular distribution
        (hax, hay) = half_angles
        self.set_obj_param(slot, 8, hax)
        self.set_obj_param(slot, 9, hay)
        # Source shape
        self.set_obj_param(slot, 10, not src_is_rectangle)
        # Shape of angular distribution
        self.set_obj_param(slot, 10, not ang_distr_is_rect)
        return slot
        
    def insert_std_lens(self, slot) :
        return self.insert_obj(slot, "NSC_SLEN")

    def insert_lenslet_array(self, slot, comment=None, thickness=None, groove_freq=None, order=None, diffract_face=None) :
        slot = self.insert_obj(slot, "NSC_LET1")
        n = self.get_surf_num()
        # set thickness
        if comment :
            self.set_obj_comment(slot, comment)
        if thickness :
            self.conn.SetNSCParameter(n, slot, 3, thickness)
        if groove_freq :
            self.conn.SetNSCParameter(n, slot, 10, groove_freq)
        if order :
            self.conn.SetNSCParameter(n, slot, 11, order)
        if diffract_face :
            self.conn.SetNSCParameter(n, slot, 24, diffract_face)
        return slot

    def insert_rect_vol(self, slot, comment=None) :
        slot = self.insert_obj(slot, "NSC_RBLK")
        if comment :
            self.set_obj_comment(slot, comment)
        return slot

# matches definition of array size
_dvr_pixels_re = re.compile(r".*Pixels\s(\d+)\sW\sX\s(\d+)\s")
# matches row of column numbers (before listing of detector data)
_dvr_cols_re = re.compile(r"^\s*1\s")

def get_detector_data(conn, settingspath=None) :
    with conn.GetTextFileObject("Dvr", settingspath) as f:
        # extract size of array in pixels
        while True :
            m = _dvr_pixels_re.match(f.next())
            if m : break
        sz = tuple(int(x) for x in m.groups())
        # allocate array of floats
        ar = np.zeros(sz, np.float32)
        # skip to column numbers
        while not _dvr_cols_re.match(f.next()) : pass
        # read detector data
        for i in range(sz[1]) :
            row = f.next().split('\t')
            # skip row number in first column
            ar[i,:] = row[1:]
    return ar


