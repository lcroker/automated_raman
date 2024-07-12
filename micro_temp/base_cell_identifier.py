from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np
from cellpose import models
import cv2
import os
from datetime import datetime
from pathlib import Path
from skimage.feature import peak_local_max

class ICellIdentifier(ABC):
    def __init__(self, directory_setup):
        self.directory_setup = directory_setup
        self.identified_cell_images_dir = self.directory_setup.get_directory("identified_cell_images")

    @abstractmethod
    def identify(self, image: np.ndarray, **kwargs) -> Tuple[List[Tuple[int, int]], np.ndarray]:
        pass

class CustomCellIdentifier(ICellIdentifier):
    def __init__(self, directory_setup):
        super().__init__(directory_setup)

    def identify(self,  image: np.ndarray, min_distance: int = 60, threshold_abs: int = 5) -> Tuple[List[Tuple[int, int]], np.ndarray]:
        cells = peak_local_max(image, min_distance=min_distance, threshold_abs=threshold_abs)
        
        marked_image = image.copy()
        if len(marked_image.shape) == 2:
            marked_image = cv2.cvtColor(marked_image, cv2.COLOR_GRAY2RGB)
        for cell in cells:
            y, x = cell
            cv2.rectangle(marked_image, (x-2, y-2), (x+2, y+2), (255, 0, 0), 1)
        
        return cells.tolist(), marked_image

class CellposeCellIdentifier(ICellIdentifier):
    def __init__(self, directory_setup, model_type='cyto'):
        super().__init__(directory_setup)
        self.model = models.Cellpose(model_type=model_type)

    def identify(self, image: np.ndarray, diameter: int = 30, **kwargs) -> Tuple[List[Tuple[int, int]], np.ndarray]:
        # Ensure the image is in the correct format for Cellpose
        if len(image.shape) == 2:
            image = np.stack((image,)*3, axis=-1)
        elif image.shape[2] == 4:  # If RGBA, convert to RGB
            image = image[:, :, :3]
        
        masks, flows, styles, diams = self.model.eval(image, diameter=diameter, channels=[0,0], **kwargs)
        
        cells = []
        for cell_id in range(1, masks.max() + 1):
            y, x = np.where(masks == cell_id)
            center_y, center_x = int(np.mean(y)), int(np.mean(x))
            cells.append((center_x, center_y))
        
        # Create a marked image
        marked_image = image.copy()
        for cell in cells:
            x, y = cell
            cv2.circle(marked_image, (x, y), 5, (0, 255, 0), -1)
        
        # Overlay mask outlines
        outlines = np.zeros(masks.shape, dtype=np.uint8)
        for i in range(1, masks.max()+1):
            contours, _ = cv2.findContours((masks == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(outlines, contours, -1, 1, 1)
        
        marked_image[outlines > 0] = [255, 0, 0]  # Red outline for cells
        
        # Save the marked image
        self.save_image(marked_image)
        
        return cells, marked_image

    def save_image(self, image):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cellpose_marked_image_{timestamp}.png"
        filepath = self.identified_cell_images_dir / filename
        cv2.imwrite(str(filepath), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        print(f"Marked image saved as: {filepath}")