from abc import ABC, abstractmethod
from typing import List
from skimage.feature import peak_local_max
import numpy as np

class ICellIdentifier(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def identify(self, image: np.ndarray, min_distance: int, threshold_abs: int) -> List[List[int]]:
        pass

class CustomCellIdentifier(ICellIdentifier):
    def __init__(self):
        super().__init__()

    def identify(self, image: np.ndarray, min_distance: int = 60, threshold_abs: int = 5) -> List[List[int]]:
        cells = peak_local_max(image, min_distance=min_distance, threshold_abs=threshold_abs)
        return cells.tolist()
