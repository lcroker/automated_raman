import numpy as np
from abc import ABC, abstractmethod

class ICamera(ABC):
    def __init__(self, core, camera):
        self.core = core
        self.camera = camera
        self.snapped_image = None
        self.core.set_camera_device(self.camera)

    def set_option(self, option:str = None, value:str = None):
        self.core.set_property(self.camera, option, value)

    def set_exposure(self, val:int = 15):
        self.core.set_exposure(val)

    @abstractmethod
    def capture(self) -> np.array:
        pass

class Camera(ICamera):
    def __init__(self, core, camera:str='AmScope', exposure:int=15):
        super().__init__(core, camera)
        # self.set_exposure(exposure)

    def capture(self) -> np.array:

        # self.core.set_property(self.camera, "Binning", "1x1")
        # self.core.set_property(self.camera, "PixelType", "GREY8")
        # self.core.set_property(self.camera, "ExposureAuto", "0")
        # self.core.set_exposure(15)

        self.core.snap_image()
        img = self.core.get_image()
        
        # Get the current image width and height
        self.width = self.core.get_image_width()
        self.height = self.core.get_image_height()
        
        byte_depth = self.core.get_bytes_per_pixel()
        total_pixels = self.width * self.height

        # if len(img) == total_pixels * byte_depth:
        #     if byte_depth == 1:
        #         img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width))
        #     elif byte_depth == 2:
        #         img = np.frombuffer(img, dtype=np.uint16).reshape((self.height, self.width))
        #     else:
        #         raise ValueError(f'Invalid byte depth: {byte_depth}')
        # elif len(img) == total_pixels * 3:  # RGB image
        #     img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width, 3))
        # else:
        #     raise ValueError(f'Unexpected image size: {len(img)} bytes')
        print(byte_depth)
        if byte_depth == 1:
            img = np.reshape(img, (self.height, self.width, 1)).astype(np.uint8)
        elif byte_depth == 2:
            img = np.reshape(img, (self.height, self.width, 2)).astype(np.uint16)
        elif byte_depth == 3:
            img = np.reshape(img, (self.height, self.width, 3)).astype(np.uint32)
        else:
            raise ValueError(f'Invalid byte depth: {byte_depth}')
        
        self.snapped_image = img
        return self.snapped_image

class SpectralCamera(ICamera):
    def __init__(self, core, camera:str='Andor'):
        super().__init__(core, camera)
    
    def capture(self) -> np.array:
        # Placeholder implementation
        return np.array([])