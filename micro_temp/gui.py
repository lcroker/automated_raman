import sys
import os
import logging
import time
import gc
import numpy as np
import tifffile as tiff
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox, 
                             QGroupBox, QScrollArea, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from microscope import Microscope
from autofocus import Amplitude, Phase
from base_cell_identifier import ICellIdentifier, CustomCellIdentifier
from base_cell_filter import ICellFilter, Isolated

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MicroManagerInitThread(QThread):
    finished = pyqtSignal(object, str)

    def __init__(self, config_file, app_path):
        super().__init__()
        self.config_file = config_file
        self.app_path = app_path

    def run(self):
        try:
            microscope = Microscope(self.config_file, self.app_path)
            self.finished.emit(microscope, "Micro-Manager started successfully.")
        except Exception as e:
            logging.error(f"Error in MicroManagerInitThread: {e}", exc_info=True)
            self.finished.emit(None, f"Error starting Micro-Manager: {str(e)}")

class MicroscopeControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Control")
        self.setGeometry(100, 100, 1200, 800)  # Set a default size
        
        self.mm_app_path = "C:\\Program Files\\Micro-Manager-2.0"
        self.microscope = None
        self.init_thread = None

        # Add dictionaries to store available strategies
        self.cell_identifier_strategies = {
            "CustomCellIdentifier": CustomCellIdentifier,
        }
        self.cell_filter_strategies = {
            "Isolated": Isolated,
        }
        self.autofocus_strategies = {
            "Amplitude": Amplitude,
            "Phase": Phase,
        }

        self.setup_ui()

    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Create a scroll area for the left side (controls)
        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_scroll_area.setWidget(left_widget)

        # Create the right side widget (output)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Set the size policies
        left_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_widget.setFixedWidth(400)  # Adjust this value as needed

        # Add widgets to the main layout
        main_layout.addWidget(left_scroll_area, 2)  # Left side takes 2/3 of the space
        main_layout.addWidget(right_widget, 1)  # Right side takes 1/3 of the space

        # Configuration File Selection Section
        config_group = self.create_group_box("Configuration", [
            ("button", "Browse", "config_file_button"),
            ("line_edit", "", "config_file_path"),
            ("button", "Start Micro-Manager", "start_headless_button")
        ])

        # Camera Control Section
        camera_group = self.create_group_box("Camera Control", [
            ("label", "Binning"),
            ("combo", ["1x1", "2x2", "4x4"], "binning_input"),
            ("label", "Pixel Type"),
            ("combo", ["GREY8", "RGB32"], "pixel_type_input"),
            ("label", "Flip Horizontal"),
            ("combo", ["FALSE", "TRUE"], "flip_horizontal_input"),
            ("label", "Flip Vertical"),
            ("combo", ["FALSE", "TRUE"], "flip_vertical_input"),
            ("label", "Exposure Auto"),
            ("combo", ["0", "1"], "exposure_auto_input"),
            ("label", "Exposure (ms)"),
            ("line_edit", "", "exposure_input"),
            ("button", "Set Camera Options", "set_camera_button")
        ])

        # Autofocus Control Section
        autofocus_group = self.create_group_box("Autofocus Control", [
            ("label", "Autofocus Strategy"),
            ("combo", list(self.autofocus_strategies.keys()), "autofocus_strategy_dropdown"),
            ("label", "Start Position"),
            ("line_edit", "", "start_position_input"),
            ("label", "End Position"),
            ("line_edit", "", "end_position_input"),
            ("label", "Step Size"),
            ("line_edit", "", "step_size_input"),
            ("button", "Start Autofocus", "autofocus_button")
        ])

        # Stage Control Section
        stage_group = self.create_group_box("Stage Control", [
            ("label", "X Position"),
            ("line_edit", "", "stage_x_input"),
            ("label", "Y Position"),
            ("line_edit", "", "stage_y_input"),
            ("label", "Z Position"),
            ("line_edit", "", "stage_z_input"),
            ("button", "Move Stage", "move_stage_button")
        ])

        # Image Capture Section
        capture_group = self.create_group_box("Image Capture", [
            ("button", "Capture Image", "capture_image_button"),
            ("image", (400, 300), "image_label")
        ])

        # Cell Identification Strategy Section
        cell_id_group = self.create_group_box("Cell Identification", [
            ("label", "Cell Identification Strategy"),
            ("combo", list(self.cell_identifier_strategies.keys()), "cell_id_strategy_dropdown"),
            ("button", "Apply Cell ID Strategy", "apply_cell_id_strategy_button")
        ])

        # Cell Filtering Strategy Section
        cell_filter_group = self.create_group_box("Cell Filtering", [
            ("label", "Cell Filtering Strategy"),
            ("combo", list(self.cell_filter_strategies.keys()), "cell_filter_strategy_dropdown"),
            ("button", "Apply Cell Filter Strategy", "apply_cell_filter_strategy_button")
        ])

        # Test Script Button
        self.test_script_button = QPushButton("Run Test Script")

        # Add all sections to left layout
        for widget in [config_group, camera_group, autofocus_group, stage_group, capture_group,
                       cell_id_group, cell_filter_group, self.test_script_button]:
            left_layout.addWidget(widget)

        # Add a stretch to push everything to the top
        left_layout.addStretch()

        # Output Area (right side)
        right_layout.addWidget(QLabel("Output"))
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        right_layout.addWidget(self.output_area)

        # Connect signals to slots
        self.connect_signals()

    def create_group_box(self, title, items):
        group = QGroupBox(title)
        layout = QVBoxLayout()
        for item_type, *args in items:
            if item_type == "label":
                layout.addWidget(QLabel(args[0]))
            elif item_type == "line_edit":
                widget = QLineEdit(args[0])
                layout.addWidget(widget)
                if len(args) > 1:
                    setattr(self, args[1], widget)
            elif item_type == "button":
                widget = QPushButton(args[0])
                layout.addWidget(widget)
                if len(args) > 1:
                    setattr(self, args[1], widget)
            elif item_type == "combo":
                widget = QComboBox()
                widget.addItems(args[0])
                layout.addWidget(widget)
                if len(args) > 1:
                    setattr(self, args[1], widget)
            elif item_type == "image":
                widget = QLabel()
                widget.setFixedSize(*args[0])
                widget.setStyleSheet("border: 1px solid black;")
                layout.addWidget(widget)
                setattr(self, args[1], widget)
        group.setLayout(layout)
        return group

    def connect_signals(self):
        self.config_file_button.clicked.connect(self.browse_config_file)
        self.start_headless_button.clicked.connect(self.start_micromanager)
        self.set_camera_button.clicked.connect(self.set_camera_options)
        self.autofocus_button.clicked.connect(self.start_autofocus)
        self.move_stage_button.clicked.connect(self.move_stage)
        self.capture_image_button.clicked.connect(self.capture_image)
        self.test_script_button.clicked.connect(self.run_test_script)
        self.apply_cell_id_strategy_button.clicked.connect(self.apply_cell_id_strategy)
        self.apply_cell_filter_strategy_button.clicked.connect(self.apply_cell_filter_strategy)

    def browse_config_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Configuration File", "", "Config Files (*.cfg);;All Files (*)", options=options)
        if file_name:
            self.config_file_path.setText(file_name)

    def start_micromanager(self):
        config_file = self.config_file_path.text()
        if not config_file:
            QMessageBox.warning(self, "Warning", "Please select a configuration file.")
            return

        self.output_area.append("Starting Micro-Manager...")
        self.start_headless_button.setEnabled(False)

        self.init_thread = MicroManagerInitThread(config_file, self.mm_app_path)
        self.init_thread.finished.connect(self.on_micromanager_init_finished)
        self.init_thread.start()

    def on_micromanager_init_finished(self, microscope, message):
        self.start_headless_button.setEnabled(True)
        self.output_area.append(message)

        if microscope is not None:
            self.microscope = microscope
            QMessageBox.information(self, "Success", "Micro-Manager initialized successfully.")
        else:
            QMessageBox.critical(self, "Error", message)

    def set_camera_options(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        
        try:
            binning = self.binning_input.currentText()
            pixel_type = self.pixel_type_input.currentText()
            flip_horizontal = self.flip_horizontal_input.currentText()
            flip_vertical = self.flip_vertical_input.currentText()
            exposure_auto = self.exposure_auto_input.currentText()
            exposure = self.exposure_input.text()

            self.output_area.append(f"Setting camera options: Binning={binning}, PixelType={pixel_type}, "
                                    f"FlipHorizontal={flip_horizontal}, FlipVertical={flip_vertical}, "
                                    f"ExposureAuto={exposure_auto}, Exposure={exposure}ms")

            self.microscope.camera.set_option("Binning", binning)
            self.microscope.camera.set_option("PixelType", pixel_type)
            self.microscope.camera.set_option("FlipHorizontal", flip_horizontal)
            self.microscope.camera.set_option("FlipVertical", flip_vertical)
            self.microscope.camera.set_option("ExposureAuto", exposure_auto)
            
            if exposure_auto == "0":  # Only set exposure if auto exposure is off
                self.microscope.camera.set_exposure(int(exposure))

            self.output_area.append("Camera options set successfully.")
        except Exception as e:
            self.output_area.append(f"Error setting camera options: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to set camera options: {str(e)}")


    def start_autofocus(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        start = int(self.start_position_input.text())
        end = int(self.end_position_input.text())
        step = float(self.step_size_input.text())
        strategy_name = self.autofocus_strategy_dropdown.currentText()
        strategy_class = self.autofocus_strategies[strategy_name]
        
        self.output_area.append(f"Starting autofocus with {strategy_name}: Start={start}, End={end}, Step={step}")
        
        # Create an instance of the autofocus strategy
        autofocus_strategy = strategy_class(self.microscope.camera, self.microscope.stage, self.microscope.lamp)
        
        # Call the focus method of the strategy
        result = autofocus_strategy.focus(start, end, step)
        
        self.output_area.append(f"Autofocus result: Optimal position={result}")

    def move_stage(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        x = float(self.stage_x_input.text()) if self.stage_x_input.text() else None
        y = float(self.stage_y_input.text()) if self.stage_y_input.text() else None
        z = float(self.stage_z_input.text()) if self.stage_z_input.text() else None

        self.output_area.append(f"Moving stage to: X={x}, Y={y}, Z={z}")
        self.microscope.stage.move(x=x, y=y, z=z)
        self.output_area.append("Finished Moving!")

    # def capture_image(self):
    #     if not self.microscope:
    #         QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
    #         return
    #     self.output_area.append("Capturing image...")
    #     try:
    #         # Turn on the lamp
    #         self.microscope.lamp.set_on()
    #         time.sleep(0.5)  # Pause for 0.5 seconds to allow the lamp to stabilize

    #         # Additional delay for camera stabilization
    #         time.sleep(2)  # Adjust as needed based on your camera's requirements

    #         # Capture multiple frames and keep the last one
    #         # for _ in range(4):
    #         #     i = 1
    #         #     image = self.microscope.camera.capture()
    #         #     time.sleep(0.6)  # Short delay between captures
    #         #     pre_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", f"capture_{i}.tif")
    #         #     tiff.imwrite(pre_path, image)
    #         #     i = i + 1
    #         #     print(i)
    #         image = self.microscope.camera.capture()
    #         time.sleep(0.6)  # Short delay between captures
    #         pre_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", f"capture_{1}.tif")
    #         tiff.imwrite(pre_path, image)
    #         image = self.microscope.camera.capture()
    #         time.sleep(0.6)  # Short delay between captures
    #         pre_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", f"capture_{2}.tif")
    #         tiff.imwrite(pre_path, image)
    #         image = self.microscope.camera.capture()
    #         time.sleep(0.6)  # Short delay between captures
    #         pre_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", f"capture_{3}.tif")
    #         tiff.imwrite(pre_path, image)
    #         image = self.microscope.camera.capture()
    #         time.sleep(0.6)  # Short delay between captures
    #         pre_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", f"capture_{4}.tif")
    #         tiff.imwrite(pre_path, image)
    #         image = self.microscope.camera.capture()
    #         time.sleep(0.6)  # Short delay between captures
    #         pre_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", f"capture_{5}.tif")
    #         tiff.imwrite(pre_path, image)

    #         if image is not None:
    #             # Debug statement to check the captured image
    #             print(f"Image captured with shape: {image.shape}, dtype: {image.dtype}")
    #             self.display_image(image)
    #             self.output_area.append("Image captured successfully.")
    #         else:
    #             self.output_area.append("Failed to capture image.")
            
    #         # Turn off the lamp
    #         self.microscope.lamp.set_off()
    #     except Exception as e:
    #         self.output_area.append(f"Error capturing image: {e}")
    #         print(f"Detailed error in capture_image: {str(e)}")
    #         import traceback
    #         print(f"Traceback in capture_image: {traceback.format_exc()}")
    # 
    # 
    # def display_image(self, image):
    #     try:
    #         if image is not None:
    #             if len(image.shape) == 2:
    #                 height, width = image.shape
    #                 channels = 1
    #             elif len(image.shape) == 3:
    #                 height, width, channels = image.shape
    #             else:
    #                 raise ValueError(f"Unexpected image shape: {image.shape}")

    #             bytes_per_line = width * channels
                
    #             # Debug statement to check the QImage parameters
    #             print(f"Creating QImage with width: {width}, height: {height}, channels: {channels}, bytes_per_line: {bytes_per_line}")
                
    #             if channels == 1:
    #                 q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    #             elif channels == 3:
    #                 q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
    #             else:
    #                 raise ValueError(f"Unsupported number of channels: {channels}")

    #             pixmap = QPixmap.fromImage(q_image)
    #             self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio))
    #             self.image_label.setScaledContents(True)
    #         else:
    #             print("No image to display")
    #     except Exception as e:
    #         print(f"Error in display_image: {str(e)}")
    #         import traceback
    #         print(f"Traceback in display_image: {traceback.format_exc()}")


    def capture_image(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        self.output_area.append("Capturing image...")
        try:
            self.microscope.lamp.set_on()
            time.sleep(0.5)
            time.sleep(2)

            image = self.microscope.camera.capture()
            if image is not None:
                print(f"Image captured with shape: {image.shape}, dtype: {image.dtype}")
                self.display_image(image)
                self.output_area.append("Image captured successfully.")
                
                # Save the image
                pixel_type = self.microscope.camera.core.get_property(self.microscope.camera.camera, "PixelType")
                file_name = f"capture_{pixel_type}_{time.strftime('%Y%m%d-%H%M%S')}.tif"
                save_path = os.path.join('C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\', "Captures", file_name)
                tiff.imwrite(save_path, image)
                self.output_area.append(f"Image saved as {file_name}")
            else:
                self.output_area.append("Failed to capture image.")
            
            self.microscope.lamp.set_off()
        except Exception as e:
            self.output_area.append(f"Error capturing image: {e}")
            print(f"Detailed error in capture_image: {str(e)}")
            import traceback
            print(f"Traceback in capture_image: {traceback.format_exc()}")

    def display_image(self, image):
        try:
            if image is not None:
                height, width = image.shape[:2]
                bytes_per_line = width * (3 if len(image.shape) == 3 else 1)
                
                # Convert image data to bytes
                image_bytes = image.tobytes()
                
                if len(image.shape) == 2:  # Grayscale
                    q_image = QImage(image_bytes, width, height, bytes_per_line, QImage.Format_Grayscale8)
                elif len(image.shape) == 3:  # RGB
                    q_image = QImage(image_bytes, width, height, bytes_per_line, QImage.Format_RGB888)
                else:
                    raise ValueError(f"Unexpected image shape: {image.shape}")
                
                print(f"Creating QImage with width: {width}, height: {height}, channels: {3 if len(image.shape) == 3 else 1}, bytes_per_line: {bytes_per_line}")
                
                pixmap = QPixmap.fromImage(q_image)
                self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio))
                self.image_label.setScaledContents(True)
            else:
                print("No image to display")
        except Exception as e:
            print(f"Error in display_image: {str(e)}")
            import traceback
            print(f"Traceback in display_image: {traceback.format_exc()}")



    def run_test_script(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        self.output_area.append("Running test script...")
        self.microscope.camera.set_option("Binning", "1x1")
        self.microscope.camera.set_option("PixelType", "GREY8")
        self.microscope.camera.set_option("ExposureAuto", "0")
        self.microscope.camera.set_exposure(17)
        result = self.microscope.auto_focus(strategy=Amplitude, start=1350, end=1400)
        self.output_area.append(f"Test script result: {result}")

    def apply_cell_id_strategy(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        
        strategy_name = self.cell_id_strategy_dropdown.currentText()
        strategy_class = self.cell_identifier_strategies[strategy_name]
        
        self.output_area.append(f"Applying Cell Identification Strategy: {strategy_name}")
        try:
            # Capture an image
            image = self.microscope.camera.capture()
            
            # Identify cells using the selected strategy
            identified_cells = self.microscope.identify_cells(identifier_strategy=strategy_class)
            
            self.output_area.append(f"Identified {len(identified_cells)} cells.")
            
            # You might want to visualize the identified cells on the image here
            # For now, we'll just display the captured image
            self.display_image(image)
        except Exception as e:
            self.output_area.append(f"Error applying cell identification strategy: {e}")

    def apply_cell_filter_strategy(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        
        strategy_name = self.cell_filter_strategy_dropdown.currentText()
        strategy_class = self.cell_filter_strategies[strategy_name]
        
        self.output_area.append(f"Applying Cell Filtering Strategy: {strategy_name}")
        try:
            # For this example, we'll assume we have already identified cells
            # In a real scenario, you might want to chain this with cell identification
            identified_cells = self.microscope.identify_cells()  # Using default strategy
            
            # Filter cells using the selected strategy
            filtered_cells = self.microscope.filter_cells(identified_cells, filter_strategy=strategy_class)
            
            self.output_area.append(f"Filtered down to {len(filtered_cells)} cells.")
            
            # You might want to visualize the filtered cells on the image here
            # For now, we'll just update the output
        except Exception as e:
            self.output_area.append(f"Error applying cell filtering strategy: {e}")

    def closeEvent(self, event):
        if self.microscope:
            self.output_area.append("Shutting down Micro-Manager...")
            QApplication.processEvents()  # Process any pending events
            self.microscope.shutdown()
            self.microscope = None  # Ensure the microscope instance is released
            time.sleep(1)  # Give a short delay for cleanup
            gc.collect()  # Force garbage collection again
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MicroscopeControlApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()