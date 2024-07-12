import tifffile as tiff
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
import os
from camera import ICamera, Camera, SpectralCamera
from lamp import Lamp
from stage import Stage
import time
import matplotlib.pyplot as plt

class Autofocus(ABC):
    def __init__(self, camera: ICamera, stage: Stage, lamp: Lamp, directory_setup):
        self.camera = camera
        self.lamp = lamp
        self.stage = stage
        self.directory_setup = directory_setup
        self.autofocus_dir = self.directory_setup.get_directory("autofocus")
        self.spectra_dir = self.directory_setup.get_directory("spectra")
        self.captures = []


    def zscan(self, start: int, end: int, step: float = 1) -> None:
        self.start = start
        self.end = end
        self.step = step

        self.stage.move(z=start)
        self.lamp.set_on()
        time.sleep(4)
        img = self.camera.snap_image()
        time.sleep(0.6)
        img = self.camera.snap_image()
        time.sleep(0.6)
        img = self.camera.snap_image()
        time.sleep(0.6)
        img = self.camera.snap_image()
        time.sleep(0.6)


        for i, z_val in enumerate(np.arange(start, end + 1 , step)):
            try:
                img = self.camera.snap_image()
                if isinstance(self.camera, Camera):
                    filename = f"capture_z{z_val:.2f}.tif"
                    pre_path = self.autofocus_dir / filename
                    tiff.imwrite(str(pre_path), img)
                    self.captures.append((pre_path, z_val))
                elif isinstance(self.camera, SpectralCamera):
                    filename = f"spectra_z{z_val:.2f}.tif"
                    pre_path = self.spectra_dir / filename
                    pd.DataFrame(img).to_csv(pre_path, index=False)
                    self.captures.append((pre_path, z_val))
            except Exception as e:
                print(f"Error capturing at z={z_val}: {e}")
            self.stage.move(z=z_val)

        self.stage.move(z=start)
        self.lamp.set_off()

    def plot_focus_measure(self, z_values, focus_measures):
        if not z_values or len(z_values) < 2:
            print("Not enough data points to plot focus measure.")
            return None

        plt.figure(figsize=(4, 3))
        plt.bar(z_values, focus_measures, width=0.8*(z_values[1]-z_values[0]))
        plt.xlabel('Z Position')
        plt.ylabel('Focus Measure')
        plt.title('Autofocus Results')
        plt.tight_layout()
        
        # Save the plot
        plot_path = os.path.join(self.autofocus_dir, "focus_measure_plot.png")
        plt.savefig(plot_path, dpi=100)
        plt.close()
        
        return plot_path

    @abstractmethod
    def focus(self, start: int, end: int, step: float) -> float:
        pass

class Amplitude(Autofocus):
    def __init__(self, camera: ICamera, stage: Stage, lamp: Lamp, directory_setup):
        super().__init__(camera, stage, lamp, directory_setup)


    def focus(self, start: int, end: int, step: float) -> float:
        self.zscan(start, end, step)
        max_var, max_index, variances = -1, -1, []
        z_values = []

        for i, (capture_path, z_val) in enumerate(self.captures):
            try:
                image = tiff.imread(capture_path)
                mean = np.mean(image)
                if mean == 0:
                    continue
                std = np.std(image)
                norm_var = std * std / mean
                variances.append(norm_var)
                z_values.append(z_val)
                if norm_var > max_var:
                    max_var, max_index = norm_var, i
            except Exception as e:
                print(f"Error processing capture {i} at z={z_val}: {e}")

        # Plot focus measure
        plot_path = self.plot_focus_measure(z_values, variances)

        return self.captures[max_index][1], plot_path  # Return the z-value of the best focus and the plot path
        # Update the Phase class similarly


class Phase(Autofocus):
    def __init__(self, camera: ICamera, stage: Stage, lamp: Lamp, image_dir="Autofocus"):
        super().__init__(camera, stage, lamp, image_dir)

    def focus(self, start: int, end: int, step: float) -> float:
        self.zscan(start, end, step)
        min_var, min_index, variances = 1e10, -1, []

        for i, capture_path in enumerate(self.captures):
            try:
                image = tiff.imread(capture_path)
                mean = np.mean(image)
                if mean == 0:
                    continue
                std = np.std(image)
                norm_var = std * std / mean
                variances.append(norm_var)
                if norm_var < min_var:
                    min_var, min_index = norm_var, i
            except Exception as e:
                print(f"Error processing capture {i}: {e}")

        return self.start + self.step * min_index

class Laser(Autofocus):
    def focus(self, start: int, end: int, step: float) -> float:
        pass

class RamanSpectra(Autofocus):
    def focus(self, start: int, end: int, step: float) -> float:
        pass
