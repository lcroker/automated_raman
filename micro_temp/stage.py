class Stage:
    def __init__(self, core):
        self.core = core
        self.focus_device = self.core.get_focus_device()
        self.xy_stage_device = self.core.get_xy_stage_device()
        self.x = self.core.get_x_position(self.xy_stage_device)
        self.y = self.core.get_y_position(self.xy_stage_device)
        self.z = self.core.get_position(self.focus_device)
    
    def move(self, x=None, y=None, z=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if z is not None:
            self.z = z
        
        self.core.set_xy_position(self.xy_stage_device, self.x, self.y)
        self.core.set_position(self.focus_device, self.z)