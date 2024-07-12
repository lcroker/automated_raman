import logging
import time
import gc
import psutil
import multiprocessing
from pycromanager import Core, start_headless, stop_headless
from camera import Camera
from stage import Stage
from lamp import Lamp
from autofocus import Autofocus, Amplitude, Phase
from base_cell_filter import ICellFilter, Isolated
from base_cell_identifier import ICellIdentifier, CustomCellIdentifier, CellposeCellIdentifier
import cv2
import numpy as np
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def shutdown_core():
    try:
        core = Core()
        core.reset()
        stop_headless(debug=True)
    except Exception as e:
        logging.error(f"Error during core shutdown: {e}")
    finally:
        logging.info("Core shutdown process completed.")

class Microscope:
    def __init__(self, config_file, directory_setup, app_path="C:\\Program Files\\Micro-Manager-2.0", headless=True):
        self.directory_setup = directory_setup
        self.config_file = config_file
        self.app_path = app_path
        self.headless = headless
        self.core = self.initialize_core()
        
        if self.core is None:
            raise Exception("Failed to initialize Micro-Manager core.")
        
        self.camera = None
        self.stage = None
        self.lamp = None
        self.autofocus = None
        self.cell_identifier = None
        self.cell_filter = None
        self.java_process = None
        self.cell_coordinates = []  # Initialize an empty list to store coordinates
        self.initialize_components()

    def initialize_core(self, max_attempts=10, delay=5):
        for attempt in range(1, max_attempts + 1):
            try:
                logging.info(f"Attempt {attempt} to initialize Micro-Manager")
                if self.headless:
                    start_headless(mm_app_path=self.app_path, config_file=self.config_file, debug=True)
                    logging.info("Waiting for ZMQ server to start...")
                    time.sleep(10)  # Wait for the ZMQ server to start properly
                    self.find_java_process()
                
                core = Core()
                if not self.headless:
                    core.load_system_configuration(self.config_file)
                
                logging.info("Micro-Manager core initialized successfully")
                return core
            except Exception as e:
                logging.error(f"Attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error("All attempts to initialize Micro-Manager have failed.")
                    return None

    def initialize_components(self):        
        self.camera = Camera(self.core, self.directory_setup)
        self.stage = Stage(self.core)
        self.lamp = Lamp(self.core)

    def set_autofocus_strategy(self, autofocus_strategy_class):
        print(f"Setting autofocus strategy to {autofocus_strategy_class.__name__}")
        if not self.camera or not self.stage or not self.lamp:
            raise ValueError("Camera, Stage, or Lamp is not initialized.")
        self.autofocus = autofocus_strategy_class(self.camera, self.stage, self.lamp, self.directory_setup)
        print(f"Autofocus strategy set: {self.autofocus}")

    # Autofocussing strategy
    def auto_focus(self, start=1315, end=1350, step=1):
        if not self.autofocus:
            raise ValueError("Autofocus strategy is not set.")
        
        # Record current Camera setting values
        exposure = self.camera.get_exposure()
        auto_exposure = self.camera.get_camera_property("ExposureAuto")
        pixel_type = self.camera.get_camera_property("PixelType")
        binning = self.camera.get_camera_property("Binning")
        filter_position = self.get_microscope_property("FilterCube", "Label")

        # Set to optimal values for autofocus.
        self.camera.set_exposure(8)
        self.camera.set_camera_property("ExposureAuto", "0")
        self.camera.set_camera_property("PixelType", "GREY8")
        self.camera.set_camera_property("Binning", "1x1")
        self.set_microscope_property("FilterCube", "Label", "Position-2")

        print(f"Starting autofocus: start={start}, end={end}, step={step}")
        result = self.autofocus.focus(start, end, step)
        print(f"Autofocus result: {result}")

        # Set values to values to original values prior to autofocussing
        self.camera.set_exposure(exposure)
        self.camera.set_camera_property("ExposureAuto", auto_exposure)
        self.camera.set_camera_property("PixelType", pixel_type)
        self.camera.set_camera_property("Binning", binning)
        self.set_microscope_property("FilterCube", "Label", filter_position)

        return result
    
    # Image capturing method    
    def capture_image(self):
        try:
            # Turn on the lamp
            self.lamp.set_on()
            time.sleep(4)
            image = self.camera.snap_image()
            time.sleep(0.6)
            image = self.camera.snap_image()
            time.sleep(0.6)
            image = self.camera.snap_image()
            time.sleep(0.6)
            image = self.camera.snap_image()
            time.sleep(0.6)

            image = self.camera.capture()
            
            if image is not None:
                print(f"Image captured with shape: {image.shape}, dtype: {image.dtype}")
                # The image saving is handled by the Camera class
            
            self.lamp.set_off()
            return image
        except Exception as e:
            print(f"Detailed error in capture_image: {str(e)}")
            import traceback
            print(f"Traceback in capture_image: {traceback.format_exc()}")
            return None
    
    # Setter for cell_identifier_strategy
    def set_cell_identifier_strategy(self, cell_identifier_strategy_class=CellposeCellIdentifier):
        print(f"Setting cell identifier strategy to {cell_identifier_strategy_class.__name__}")
        if not issubclass(cell_identifier_strategy_class, ICellIdentifier):
            raise ValueError("The provided class must be a subclass of ICellIdentifier")
        self.cell_identifier = cell_identifier_strategy_class(self.directory_setup)
        print(f"Cell identifier strategy set: {self.cell_identifier}")

    
    # Cell identification strategy
    def identify_cells(self, **kwargs):
        if not self.cell_identifier:
            raise ValueError("Cell identifier strategy is not set.")        

        ############################### May remove if leaving it to user to decide ###############################
        # Record current Camera setting values
        auto_exposure = self.camera.get_camera_property("ExposureAuto")
        pixel_type = self.camera.get_camera_property("PixelType")
        binning = self.camera.get_camera_property("Binning")
        filter_position = self.get_microscope_property("FilterCube", "Label")

        # Set to optimal values for identifying cells.
        self.camera.set_camera_property("ExposureAuto", "1")
        self.camera.set_camera_property("PixelType", "RGB32")
        self.camera.set_camera_property("Binning", "4x4")
        self.set_microscope_property("FilterCube", "Label", "Position-2")
        ###########################################################################################################
        
        self.lamp.set_on()
        time.sleep(4)
        image = self.camera.snap_image()
        time.sleep(0.6)
        image = self.camera.snap_image()
        time.sleep(0.6)
        image = self.camera.snap_image()
        time.sleep(0.6)
        image = self.camera.snap_image()
        time.sleep(0.6)
        # Snap image
        image = self.camera.snap_image()        

        ############################### May remove if leaving it to user to decide ###############################
        # Set values to values to original values prior to identifying cells
        self.camera.set_camera_property("ExposureAuto", auto_exposure)
        self.camera.set_camera_property("PixelType", pixel_type)
        self.camera.set_camera_property("Binning", binning)
        self.set_microscope_property("FilterCube", "Label", filter_position)
        ###########################################################################################################      
        
        # Convert image to numpy array if it's not already
        if not isinstance(image, np.ndarray):
            image = np.array(image)
        
        cell_coordinates, marked_image = self.cell_identifier.identify(image, **kwargs)
        
        # Ensure the marked_image is in the correct format for display
        if len(marked_image.shape) == 2:
            marked_image = cv2.cvtColor(marked_image, cv2.COLOR_GRAY2RGB)
        elif marked_image.shape[2] == 4:
            marked_image = cv2.cvtColor(marked_image, cv2.COLOR_RGBA2RGB)
        
        self.cell_coordinates = cell_coordinates
        return cell_coordinates, marked_image
    
    def get_cell_coordinates(self):
        return self.cell_coordinates    
    
    # Cell filtering strategy
    def filter_cells(self, cell_coordinates, filter_strategy=Isolated, **kwargs):
        filter_instance = filter_strategy()
        return filter_instance.filter(cell_coordinates, **kwargs)
    
    # previously set_option
    def set_microscope_property(self, device, property_name, value):
        try:
            if device == "FilterCube":
                self.core.set_property(device, "Label", value)
                logging.info(f"Set FilterCube Label to {value}")
            else:
                # For future extensions, you can add more device-specific logic here
                self.core.set_property(device, property_name, value)
                logging.info(f"Set {device} {property_name} to {value}")
        except Exception as e:
            logging.error(f"Error setting {device} {property_name}: {str(e)}")
            raise

    def get_microscope_property(self, device, property_name):
        try:
            if device == "FilterCube" and property_name == "Label":
                value = self.core.get_property(device, "Label")
                logging.info(f"Got FilterCube Label: {value}")
            else:
                # For future extensions, you can add more device-specific logic here
                value = self.core.get_property(device, property_name)
                logging.info(f"Got {device} {property_name}: {value}")
            return value
        except Exception as e:
            logging.error(f"Error getting {device} {property_name}: {str(e)}")
            raise


    def find_java_process(self):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'java' in proc.info['name'].lower() and any('micro-manager' in arg.lower() for arg in proc.info['cmdline']):
                self.java_process = proc
                logging.info(f"Found Java process for Micro-Manager: PID {proc.pid}")
                break


    def shutdown(self):
        logging.info("Initiating Micro-Manager shutdown...")
        try:
            # Release resources
            self.camera = None
            self.stage = None
            self.lamp = None
            # self.autofocus = None

            # Run the shutdown helper in a separate process
            p = multiprocessing.Process(target=shutdown_core)
            p.start()
            p.join(timeout=10)  # Wait for up to 10 seconds
            
            if p.is_alive():
                logging.warning("Core shutdown process timed out. Terminating...")
                p.terminate()
                p.join()

            # Nullify the core object
            self.core = None
            
            # Force garbage collection
            gc.collect()

            logging.info("Core reference released and garbage collection forced.")

            # If we found a Java process, try to terminate it
            if self.java_process:
                try:
                    self.java_process.terminate()
                    self.java_process.wait(timeout=5)  # Wait up to 5 seconds for the process to terminate
                    logging.info(f"Java process (PID {self.java_process.pid}) terminated.")
                except psutil.NoSuchProcess:
                    logging.info("Java process already terminated.")
                except psutil.TimeoutExpired:
                    logging.warning(f"Timeout while waiting for Java process (PID {self.java_process.pid}) to terminate. Forcing kill.")
                    self.java_process.kill()
                except Exception as e:
                    logging.error(f"Error terminating Java process: {e}")

            logging.info("Micro-Manager shutdown complete.")
        except Exception as e:
            logging.error(f"Unexpected error during shutdown: {e}")


    def __del__(self):
        if hasattr(self, 'core') and self.core is not None:
            self.shutdown()