import matplotlib.pyplot as plt
import tifffile as tiff
import numpy as np
import skimage as ski
import os
import time
from os.path import join
from pycromanager import Core, start_headless, stop_headless

core = Core()
print(core)
# core.load_system_configuration(config_file)
print("MMCore Loaded")

def autofocus_plane(core:Core=None, path="", n_images=40, z_start=1350, step=1) -> None:
    # Record images along z axis
    # core.set_serial_port_command("COM13", "CURRENT=0", "\r\n")
    core.set_property("TransmittedLamp", "Label", "On")
    core.set_camera_device("AmScope")
    camera_name = core.get_camera_device()
    core.set_property(camera_name, "Binning", "1x1")
    core.set_property(camera_name, "PixelType", "GREY8")
    core.set_property(camera_name, "ExposureAuto", "0")
    core.set_exposure(15)
    
    width = core.get_image_width()
    height = core.get_image_height()
    byte_depth = core.get_bytes_per_pixel()
    zstage = core.get_focus_device()

    
    
    time.sleep(2)
    z_pos = core.get_position(zstage)
    offset = n_images // 2

    for z_val in range(z_start - offset, z_start + offset + 2, step):
        core.snap_image()
        img = core.get_image()
        # img = np.max(img) - img
        if byte_depth == 1:
            ip = np.reshape(img, (height, width)).astype(np.uint8)
        elif byte_depth == 2:
            ip = np.reshape(img, (height, width)).astype(np.uint16)
        elif byte_depth == 4:
            ip = np.reshape(img, (height, width)).astype(np.uint32)
        else:
            raise ValueError(f'byte depth should be 1, 2 or 4. byte depth: {byte_depth}')
        
        img_index = z_val - z_start + offset

        if img_index == 0 or img_index == 1:
            pre_path = join(path, f"Autofocus/temp/image_{img_index}.tif")
        else:
            pre_path = join(path, f"Autofocus/temp/image_{img_index-2}.tif")
        
        tiff.imwrite(pre_path, ip) # photometric='minisblack'
        z_pos = z_val
        core.set_position(zstage, z_pos)

    max_var, max_var_index, variances = -1, -1, []
    for i in range(n_images):
        image = tiff.imread(join(path, f"Autofocus/temp/image_{i}.tif"))
        mean, std = np.mean(image), np.std(image)
        norm_var = std * std / mean
        variances.append(norm_var)
        if norm_var > max_var:
            max_var, max_var_index = norm_var, i
    
    z_pos = (z_start - offset) + (step * max_var_index)
    core.set_position(zstage, z_pos)
    return max_var_index, max_var, variances

max_i, max_var, variances = autofocus_plane(core, n_images=40, z_start=1330)
print(max_i, max_var)

plt.bar(list(range(len(variances))), variances, color='blue', edgecolor='black')
plt.xticks(list(range(len(variances))))
plt.title('Image Variance')
plt.xlabel('Image')
plt.ylabel('Variance')
plt.show()