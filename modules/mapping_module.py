"""
Optimized mapping module for the PiCar-X robot.

This module handles:
- Occupancy grid management using NumPy arrays
- Efficient grid updates and queries
- Memory-efficient storage
- Fast spatial operations
"""

import numpy as np
import json
import logging
from typing import Tuple, List, Optional
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class RobotPose:
    """Robot pose in 2D space."""
    x: float  # cm
    y: float  # cm
    theta: float  # radians

class OccupancyGrid:
    """
    Memory and computationally efficient occupancy grid implementation.
    
    Uses NumPy arrays for fast operations and implements caching for
    frequently accessed computations.
    """
    
    def __init__(self, width_cm: int, height_cm: int, resolution_cm: float = 1.0) -> None:
        """
        Initialize the occupancy grid.
        
        Args:
            width_cm: Width of the area to map in centimeters
            height_cm: Height of the area to map in centimeters
            resolution_cm: Size of each grid cell in centimeters
        """
        self.resolution_cm = resolution_cm
        self.width_cells = int(np.ceil(width_cm / resolution_cm))
        self.height_cells = int(np.ceil(height_cm / resolution_cm))
        
        # Initialize grid with unknown values (0.5)
        # Use float16 to save memory while maintaining sufficient precision
        self.grid = np.full((self.height_cells, self.width_cells), 0.5, dtype=np.float16)
        
        # Cache for coordinate transformations
        self._coord_cache = {}
        self._max_cache_size = 1000
        
        logger.info(f"Created occupancy grid: {self.width_cells}x{self.height_cells} cells")
    
    @property
    def shape(self) -> Tuple[int, int]:
        """Get the shape of the grid."""
        return self.grid.shape
    
    @lru_cache(maxsize=1024)
    def _world_to_grid(self, x_cm: float, y_cm: float) -> Tuple[int, int]:
        """
        Convert world coordinates to grid indices.
        
        Uses LRU cache to speed up repeated transformations.
        """
        grid_x = int(np.floor(x_cm / self.resolution_cm))
        grid_y = int(np.floor(y_cm / self.resolution_cm))
        return grid_x, grid_y
    
    @lru_cache(maxsize=1024)
    def _grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Convert grid indices to world coordinates.
        
        Uses LRU cache to speed up repeated transformations.
        """
        world_x = (grid_x + 0.5) * self.resolution_cm
        world_y = (grid_y + 0.5) * self.resolution_cm
        return world_x, world_y
    
    def update_occupancy(self, distance: float, angle: float, robot_pose: RobotPose) -> None:
        """
        Update the occupancy grid with a new sensor reading.
        
        Uses vectorized operations for efficiency.
        
        Args:
            distance: Distance to obstacle in cm
            angle: Angle of the sensor reading in radians
            robot_pose: Current pose of the robot
        """
        try:
            # Calculate the endpoint of the sensor reading
            end_x = robot_pose.x + distance * np.cos(robot_pose.theta + angle)
            end_y = robot_pose.y + distance * np.sin(robot_pose.theta + angle)
            
            # Convert to grid coordinates
            start_x, start_y = self._world_to_grid(robot_pose.x, robot_pose.y)
            end_x, end_y = self._world_to_grid(end_x, end_y)
            
            # Use Bresenham's line algorithm for efficient ray tracing
            # Implemented using NumPy for speed
            cells = self._bresenham_line(start_x, start_y, end_x, end_y)
            
            # Update probabilities along the ray
            # Free space update
            self._update_cells_vectorized(cells[:-1], is_occupied=False)
            # Occupied space update (endpoint)
            if cells.size > 0:
                self._update_cells_vectorized(cells[-1:], is_occupied=True)
                
        except Exception as e:
            logger.error(f"Error updating occupancy grid: {str(e)}", exc_info=True)
    
    def _bresenham_line(self, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
        """
        Efficient Bresenham's line algorithm implementation using NumPy.
        
        Returns array of (x, y) coordinates along the line.
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        if dx == 0 and dy == 0:
            return np.array([[x0, y0]])
        
        # Determine step direction
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        
        # Calculate points along the line
        if dx > dy:
            # Horizontal-ish lines
            points = np.column_stack((
                np.arange(x0, x1 + sx, sx),
                np.round(np.interp(
                    np.arange(x0, x1 + sx, sx),
                    [x0, x1],
                    [y0, y1]
                )).astype(int)
            ))
        else:
            # Vertical-ish lines
            points = np.column_stack((
                np.round(np.interp(
                    np.arange(y0, y1 + sy, sy),
                    [y0, y1],
                    [x0, x1]
                )).astype(int),
                np.arange(y0, y1 + sy, sy)
            ))
        
        # Filter points within grid bounds
        mask = (
            (points[:, 0] >= 0) & 
            (points[:, 0] < self.width_cells) & 
            (points[:, 1] >= 0) & 
            (points[:, 1] < self.height_cells)
        )
        return points[mask]
    
    def _update_cells_vectorized(self, cells: np.ndarray, is_occupied: bool) -> None:
        """
        Update occupancy probabilities using vectorized operations.
        
        Args:
            cells: Array of (x, y) coordinates to update
            is_occupied: Whether the cells are occupied
        """
        if cells.size == 0:
            return
            
        # Log odds update
        log_odds_update = 0.4 if is_occupied else -0.4
        current = self.grid[cells[:, 1], cells[:, 0]]
        
        # Convert to log odds, update, and back to probability
        log_odds = np.log(current / (1 - current))
        log_odds += log_odds_update
        self.grid[cells[:, 1], cells[:, 0]] = 1 / (1 + np.exp(-log_odds))
    
    def get_frontiers(self) -> List[Tuple[int, int]]:
        """
        Find frontier cells (boundaries between known and unknown space).
        
        Uses efficient NumPy operations for speed.
        """
        # Create binary masks
        unknown = np.abs(self.grid - 0.5) < 0.1
        free = self.grid < 0.3
        
        # Convolve to find boundaries
        kernel = np.ones((3, 3))
        unknown_expanded = np.zeros_like(unknown)
        cv2.dilate(unknown.astype(np.uint8), kernel, unknown_expanded)
        
        # Find frontier cells
        frontier_mask = free & unknown_expanded
        frontier_coords = np.argwhere(frontier_mask)
        
        return [(int(x), int(y)) for y, x in frontier_coords]
    
    def save_grid_to_file(self, filepath: str) -> None:
        """Save the occupancy grid to a compressed NPZ file."""
        try:
            # Save as compressed NumPy array
            np.savez_compressed(
                filepath,
                grid=self.grid,
                resolution=self.resolution_cm
            )
            logger.info(f"Saved occupancy grid to {filepath}")
        except Exception as e:
            logger.error(f"Error saving occupancy grid: {str(e)}", exc_info=True)
    
    def load_grid_from_file(self, filepath: str) -> bool:
        """Load the occupancy grid from a compressed NPZ file."""
        try:
            data = np.load(filepath)
            self.grid = data['grid']
            self.resolution_cm = float(data['resolution'])
            self.height_cells, self.width_cells = self.grid.shape
            logger.info(f"Loaded occupancy grid from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading occupancy grid: {str(e)}", exc_info=True)
            return False
    
    def get_explored_area_percentage(self) -> float:
        """Calculate the percentage of explored area."""
        total_cells = self.grid.size
        unknown_cells = np.sum(np.abs(self.grid - 0.5) < 0.1)
        return 100 * (1 - unknown_cells / total_cells)
