import numpy as np
from abc import ABC, abstractmethod

class ICamera(ABC):
    def __init__(self, core, camera):
        self.core = core
        self.camera = camera
        self.snapped_image = None
        self.core.set_camera_device(self.camera)
        self.available_properties = self.get_available_properties()

    def get_available_properties(self):
        properties = {}
        property_names = self.core.get_device_property_names(self.camera)
        for i in range(property_names.size()):
            prop = property_names.get(i)
            allowed_values = self.core.get_allowed_property_values(self.camera, prop)
            if allowed_values is not None:
                properties[prop] = [allowed_values.get(j) for j in range(allowed_values.size())]
            else:
                properties[prop] = None
        return properties

    @abstractmethod
    def set_option(self, option: str, value: str):
        pass

    @abstractmethod
    def set_exposure(self, val: int):
        pass

    @abstractmethod
    def capture(self) -> np.array:
        pass

class Camera(ICamera):
    def __init__(self, core, camera: str = 'AmScope', exposure: int = 15):
        super().__init__(core, camera)
        self.set_exposure(exposure)
        print("Available camera properties:")
        for prop, values in self.available_properties.items():
            print(f"{prop}: {values}")

    def set_option(self, option: str, value: str):
        try:
            if option in self.available_properties:
                if self.available_properties[option] is None or value in self.available_properties[option]:
                    self.core.set_property(self.camera, option, value)
                    print(f"Successfully set {option} to {value}")
                else:
                    print(f"Warning: {value} is not an allowed value for {option}. Allowed values: {self.available_properties[option]}")
            else:
                print(f"Warning: {option} is not a supported property for this camera")
        except Exception as e:
            print(f"Error setting camera option {option}: {str(e)}")

    def set_exposure(self, val: int):
        try:
            self.core.set_exposure(val)
            print(f"Exposure set to {val} ms")
        except Exception as e:
            print(f"Error setting exposure: {str(e)}")

    def capture(self) -> np.array:
        try:
            self.core.snap_image()
            img = self.core.get_image()
            
            self.width = self.core.get_image_width()
            self.height = self.core.get_image_height()
            byte_depth = self.core.get_bytes_per_pixel()
            pixel_type = self.core.get_property(self.camera, "PixelType")

            print(f"Image captured. Width: {self.width}, Height: {self.height}, Byte depth: {byte_depth}, Pixel type: {pixel_type}")

            if pixel_type == "GREY8":
                img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width))
            elif pixel_type == "RGB32":
                # RGB32 is typically stored as BGRA
                img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width, 4))
                # Convert BGRA to RGB
                img = img[:, :, [2, 1, 0]]  # Reorder channels from BGRA to RGB
            else:
                raise ValueError(f"Unsupported pixel type: {pixel_type}")
            
            print(f"Reshaped image. Shape: {img.shape}, dtype: {img.dtype}")
            
            self.snapped_image = img
            return self.snapped_image
        except Exception as e:
            print(f"Error capturing image: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

class SpectralCamera(ICamera):
    def __init__(self, core, camera: str = 'Andor'):
        super().__init__(core, camera)
    
    def set_option(self, option: str, value: str):
        # Implement for SpectralCamera if needed
        pass

    def set_exposure(self, val: int):
        # Implement for SpectralCamera if needed
        pass
    
    def capture(self) -> np.array:
        # Placeholder implementation
        return np.array([])