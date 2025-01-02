"""
Test cases for the Mapping Module
"""

import unittest
import os
import math
import numpy as np
from modules.mapping_module import OccupancyGrid, RobotPose

class TestOccupancyGrid(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.grid = OccupancyGrid(width_cm=100, height_cm=100, resolution_cm=1)

    def test_initialization(self):
        """Test grid initialization."""
        self.assertEqual(self.grid.width_cells, 100)
        self.assertEqual(self.grid.height_cells, 100)
        self.assertEqual(self.grid.resolution_cm, 1)
        
        # Check that grid is initialized with unknown values (0.5)
        self.assertTrue(np.allclose(self.grid._grid, 0.5))
        
        # Check that visited grid is initialized with False
        self.assertFalse(np.any(self.grid._visited))

    def test_coordinate_conversion(self):
        """Test robot-to-grid and grid-to-robot coordinate conversion."""
        # Test center point
        grid_x, grid_y = self.grid.robot_to_grid(0, 0)
        self.assertEqual(grid_x, self.grid._origin_x)
        self.assertEqual(grid_y, self.grid._origin_y)
        
        # Test conversion back to robot coordinates
        x_robot, y_robot = self.grid.grid_to_robot(grid_x, grid_y)
        self.assertEqual(x_robot, 0)
        self.assertEqual(y_robot, 0)
        
        # Test some non-zero coordinates
        test_coords = [(10, 20), (-15, 25), (-30, -30)]
        for x, y in test_coords:
            grid_x, grid_y = self.grid.robot_to_grid(x, y)
            x_back, y_back = self.grid.grid_to_robot(grid_x, grid_y)
            # Allow for small rounding errors due to discretization
            self.assertAlmostEqual(x, x_back, delta=self.grid.resolution_cm)
            self.assertAlmostEqual(y, y_back, delta=self.grid.resolution_cm)

    def test_occupancy_update(self):
        """Test updating occupancy probabilities."""
        # Create a simple scenario with robot at origin
        robot_pose = RobotPose(x=0, y=0, theta=0)
        
        # Simulate a sensor reading straight ahead at 50cm
        self.grid.update_occupancy(50, 0, robot_pose)
        
        # Check that cells along the path are marked as free
        grid_x, grid_y = self.grid.robot_to_grid(25, 0)  # Midpoint
        self.assertLess(self.grid.get_cell_probability(grid_x, grid_y), 0.5)
        
        # Check that the endpoint is marked as occupied
        grid_x, grid_y = self.grid.robot_to_grid(50, 0)  # Endpoint
        self.assertGreater(self.grid.get_cell_probability(grid_x, grid_y), 0.5)

    def test_file_io(self):
        """Test saving and loading the grid."""
        # Create some test data
        robot_pose = RobotPose(x=0, y=0, theta=0)
        self.grid.update_occupancy(50, 0, robot_pose)
        
        # Save the grid
        test_file = "test_grid.json"
        self.grid.save_grid_to_file(test_file)
        
        # Create a new grid and load the data
        new_grid = OccupancyGrid(width_cm=100, height_cm=100, resolution_cm=1)
        success = new_grid.load_grid_from_file(test_file)
        
        # Verify the load was successful
        self.assertTrue(success)
        
        # Check that the grids are identical
        self.assertTrue(np.array_equal(self.grid._grid, new_grid._grid))
        self.assertTrue(np.array_equal(self.grid._visited, new_grid._visited))
        
        # Clean up
        os.remove(test_file)

    def test_frontier_detection(self):
        """Test frontier cell detection."""
        # Create a simple scenario with some explored and unexplored areas
        robot_pose = RobotPose(x=0, y=0, theta=0)
        self.grid.update_occupancy(50, 0, robot_pose)
        
        # Get frontiers
        frontiers = self.grid.get_frontiers()
        
        # Should have some frontier cells
        self.assertGreater(len(frontiers), 0)
        
        # Check that frontier cells are adjacent to visited cells
        for fx, fy in frontiers:
            has_visited_neighbor = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = fx + dx, fy + dy
                    if (0 <= nx < self.grid.width_cells and 
                        0 <= ny < self.grid.height_cells and 
                        self.grid.is_cell_visited(nx, ny)):
                        has_visited_neighbor = True
                        break
                if has_visited_neighbor:
                    break
            self.assertTrue(has_visited_neighbor)

    def test_bresenham_line(self):
        """Test the Bresenham line algorithm implementation."""
        # Test horizontal line
        cells = self.grid._get_line_cells(0, 0, 5, 0)
        self.assertEqual(len(cells), 6)
        self.assertEqual(cells[0], (0, 0))
        self.assertEqual(cells[-1], (5, 0))
        
        # Test vertical line
        cells = self.grid._get_line_cells(0, 0, 0, 5)
        self.assertEqual(len(cells), 6)
        self.assertEqual(cells[0], (0, 0))
        self.assertEqual(cells[-1], (0, 5))
        
        # Test diagonal line
        cells = self.grid._get_line_cells(0, 0, 5, 5)
        self.assertEqual(len(cells), 6)
        self.assertEqual(cells[0], (0, 0))
        self.assertEqual(cells[-1], (5, 5))

if __name__ == '__main__':
    unittest.main() 