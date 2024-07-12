import numpy as np
import time
import os
import tifffile as tiff
from abc import ABC, abstractmethod
from pathlib import Path

class ICamera(ABC):
    def __init__(self, core, directory_setup, camera):
        self.core = core
        self.camera = camera
        self.directory_setup = directory_setup
        self.captured_images_dir = self.directory_setup.get_directory("captured_images")
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
    def set_camera_property(self, option: str, value: str):
        pass

    @abstractmethod
    def get_camera_property(self, option: str, value: str):
        pass

    @abstractmethod
    def set_exposure(self, val: int):
        pass

    @abstractmethod
    def get_exposure(self, val: int):
        pass

    @abstractmethod
    def capture(self) -> np.array:
        pass

    @abstractmethod
    def snap_image(self) -> np.array:
        pass

class Camera(ICamera):
    def __init__(self, core, directory_setup, camera: str = 'AmScope', exposure: int = 15):
        super().__init__(core, directory_setup, camera)
        self.set_exposure(exposure)
        print("Available camera properties:")
        for prop, values in self.available_properties.items():
            print(f"{prop}: {values}")

    def set_camera_property(self, option: str, value: str):
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


    def get_camera_property(self, option: str):
        try:
            if option in self.available_properties:
                value = self.core.get_property(self.camera, option)
                print(f"Current value of {option}: {value}")
                return value
            else:
                print(f"Warning: {option} is not a supported property for this camera")
                return None
        except Exception as e:
            print(f"Error getting camera option {option}: {str(e)}")
            return None

    def set_exposure(self, val: int):
        try:
            self.core.set_exposure(val)
            print(f"Exposure set to {val} ms")
        except Exception as e:
            print(f"Error setting exposure: {str(e)}")

    def get_exposure(self):
        try:
            exposure = self.core.get_exposure()
            print(f"Current exposure: {exposure} ms")
            return exposure
        except Exception as e:
            print(f"Error getting exposure: {str(e)}")
            return None

    def capture(self) -> np.array:
        try:
            self.core.snap_image()
            img = self.core.get_image()
            
            self.width = self.core.get_image_width()
            self.height = self.core.get_image_height()
            byte_depth = self.core.get_bytes_per_pixel()
            pixel_type = self.core.get_property(self.camera, "PixelType")

            print(f"Raw image data size: {len(img)} bytes")
            print(f"Image captured. Width: {self.width}, Height: {self.height}, Byte depth: {byte_depth}, Pixel type: {pixel_type}")

            if pixel_type == "GREY8":
                img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width))
            elif pixel_type == "RGB32":
                img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width, 4))
                img = img[:, :, :3]  # Remove alpha channel if present
            else:
                raise ValueError(f"Unsupported pixel type: {pixel_type}")
            
            print(f"Reshaped image. Shape: {img.shape}, dtype: {img.dtype}")
            print(f"Image statistics: Min: {np.min(img)}, Max: {np.max(img)}, Mean: {np.mean(img)}")
            
            if pixel_type == "RGB32":
                print("RGB channel statistics:")
                for i, color in enumerate(['Red', 'Green', 'Blue']):
                    channel = img[:,:,i]
                    print(f"  {color}: Min: {np.min(channel)}, Max: {np.max(channel)}, Mean: {np.mean(channel):.2f}")

            # Print white balance values without applying them
            try:
                r_gain = self.core.get_property(self.camera, "WhiteBalanceRGain")
                g_gain = self.core.get_property(self.camera, "WhiteBalanceGGain")
                b_gain = self.core.get_property(self.camera, "WhiteBalanceBGain")
                print(f"White balance gains: R={r_gain}, G={g_gain}, B={b_gain}")
            except Exception as e:
                print(f"Error getting white balance values: {str(e)}")

            self.captured_image = img

            # Save the captured image
            timestamp = time.strftime('%Y%m%d-%H%M%S')
            filename = f"Capture_{timestamp}.tif"
            filepath = Path(self.captured_images_dir) / filename
            tiff.imwrite(str(filepath), self.captured_image)
            print(f"Image saved: {filepath}")                
            
            return self.captured_image
        except Exception as e:
            print(f"Error capturing image: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None
        
    
    # Same logic as Capture, but capture saves image to "captured_images" directory
    def snap_image(self) -> np.array:
        try:
            self.core.snap_image()
            img = self.core.get_image()
            
            self.width = self.core.get_image_width()
            self.height = self.core.get_image_height()
            byte_depth = self.core.get_bytes_per_pixel()
            pixel_type = self.core.get_property(self.camera, "PixelType")

            print(f"Raw image data size: {len(img)} bytes")
            print(f"Image snapped. Width: {self.width}, Height: {self.height}, Byte depth: {byte_depth}, Pixel type: {pixel_type}")

            if pixel_type == "GREY8":
                img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width))
            elif pixel_type == "RGB32":
                img = np.frombuffer(img, dtype=np.uint8).reshape((self.height, self.width, 4))
                img = img[:, :, :3]  # Remove alpha channel if present
            else:
                raise ValueError(f"Unsupported pixel type: {pixel_type}")
            
            print(f"Reshaped image. Shape: {img.shape}, dtype: {img.dtype}")
            print(f"Image statistics: Min: {np.min(img)}, Max: {np.max(img)}, Mean: {np.mean(img)}")
            
            if pixel_type == "RGB32":
                print("RGB channel statistics:")
                for i, color in enumerate(['Red', 'Green', 'Blue']):
                    channel = img[:,:,i]
                    print(f"  {color}: Min: {np.min(channel)}, Max: {np.max(channel)}, Mean: {np.mean(channel):.2f}")

            # Print white balance values without applying them
            try:
                r_gain = self.core.get_property(self.camera, "WhiteBalanceRGain")
                g_gain = self.core.get_property(self.camera, "WhiteBalanceGGain")
                b_gain = self.core.get_property(self.camera, "WhiteBalanceBGain")
                print(f"White balance gains: R={r_gain}, G={g_gain}, B={b_gain}")
            except Exception as e:
                print(f"Error getting white balance values: {str(e)}")

            self.snapped_image = img             
            
            return self.snapped_image
        except Exception as e:
            print(f"Error capturing image: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

class SpectralCamera(ICamera):
    def __init__(self, core,  directory_setup, camera: str = 'Andor'):
        super().__init__(core,  directory_setup, camera)
    
    def set_camera_property(self, option: str, value: str):
        # Placeholder implementation
        pass

    def get_camera_property(self, option: str):
        # Placeholder implementation
        pass

    def set_exposure(self, val: int):
        # Placeholder implementation
        pass

    def get_exposure(self):
        # Placeholder implementation
        pass
    
    def capture(self) -> np.array:
        # Placeholder implementation
        return np.array([])        
    
    def snap_image(self) -> np.array:
        # Placeholder implementation
        pass