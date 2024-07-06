from abc import ABC, abstractmethod
from typing import List
import numpy as np


class ICellFilter(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def filter(self, list, int): 
        pass
    

class Isolated(ICellFilter):
    def __init__(self):
        super().__init__()

    def filter(cell_xy: list, n_filtered: int = 10) -> list:
        n_cells = len(cell_xy)
        if n_cells < n_filtered:
            n_filtered = n_cells

        min_distance = np.full(n_cells, np.inf)
        cell_pos = np.array(cell_xy)

        # Calculate the nearest neighbor distances for each cell
        for i in range(n_cells):
            for j in range(n_cells):
                if i != j:
                    distance = np.linalg.norm(cell_pos[i] - cell_pos[j])  # Euclidean distance
                    if distance < min_distance[i]:
                        min_distance[i] = distance

        # Sort the distances and determine the threshold for isolation
        min_distance_sorted = np.sort(min_distance)
        threshold = min_distance_sorted[-n_filtered]

        # Filter the cells based on the isolation threshold
        cell_filtered = []
        for i in range(n_cells):
            if min_distance[i] >= threshold and len(cell_filtered) < n_filtered:
                cell_filtered.append(tuple(cell_pos[i]))

        return cell_filtered
