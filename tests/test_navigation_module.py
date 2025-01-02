"""
Test cases for the Navigation Module
"""

import unittest
import math
import time
from modules.mapping_module import OccupancyGrid, RobotPose
from modules.navigation_module import NavigationController, MovementCommand

class TestNavigationController(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.grid = OccupancyGrid(width_cm=100, height_cm=100, resolution_cm=1)
        self.nav = NavigationController(self.grid)

    def test_initialization(self):
        """Test controller initialization."""
        self.assertTrue(self.nav._hardware_initialized)
        self.assertEqual(self.nav._current_pose.x, 0)
        self.assertEqual(self.nav._current_pose.y, 0)
        self.assertEqual(self.nav._current_pose.theta, 0)

    def test_basic_movements(self):
        """Test basic movement commands."""
        # Test moving forward
        self.assertTrue(self.nav.move_forward())
        self.assertTrue(self.nav.move_forward(10))  # With specific speed
        
        # Test turning
        self.assertTrue(self.nav.turn(math.pi/2))  # 90 degrees left
        self.assertTrue(self.nav.turn(-math.pi/2))  # 90 degrees right
        
        # Test stopping
        self.assertTrue(self.nav.stop())

    def test_pose_updates(self):
        """Test pose updating and retrieval."""
        # Create a new pose
        new_pose = RobotPose(x=10, y=20, theta=math.pi/4)
        
        # Update pose
        self.nav.update_pose(new_pose)
        
        # Get and verify pose
        current_pose = self.nav.get_pose()
        self.assertEqual(current_pose.x, 10)
        self.assertEqual(current_pose.y, 20)
        self.assertEqual(current_pose.theta, math.pi/4)

    def test_obstacle_avoidance(self):
        """Test obstacle avoidance behavior."""
        # Test when obstacle is far (should return True without avoidance)
        self.assertTrue(self.nav.avoid_obstacle(100, 0))
        
        # Test when obstacle is close
        success = self.nav.avoid_obstacle(10, math.pi/4)
        self.assertTrue(success)
        
        # Verify that the robot turned away from the obstacle
        current_pose = self.nav.get_pose()
        self.assertNotEqual(current_pose.theta, 0)  # Should have turned

    def test_navigation_to_point(self):
        """Test navigation to a specific point."""
        # Try navigating to a point
        target_x, target_y = 50, 50
        success = self.nav.navigate_to_point(target_x, target_y)
        self.assertTrue(success)
        
        # Get final pose
        final_pose = self.nav.get_pose()
        
        # Robot should have turned towards target
        target_angle = math.atan2(target_y, target_x)
        angle_diff = abs(target_angle - final_pose.theta)
        while angle_diff > math.pi:
            angle_diff -= 2*math.pi
        self.assertLess(abs(angle_diff), 0.2)  # Allow small angle error

    def test_frontier_finding(self):
        """Test frontier detection and navigation."""
        # Create some explored area
        robot_pose = RobotPose(x=0, y=0, theta=0)
        self.grid.update_occupancy(50, 0, robot_pose)
        
        # Find nearest frontier
        frontier = self.nav.find_nearest_frontier()
        
        # Should find at least one frontier
        self.assertIsNotNone(frontier)
        self.assertEqual(len(frontier), 2)  # Should return (x, y) coordinates

    def test_movement_command_execution(self):
        """Test execution of movement commands."""
        # Create a test command
        command = MovementCommand(
            linear_speed=10,
            angular_speed=math.pi/4,
            duration=1.0
        )
        
        # Execute command
        start_time = time.time()
        success = self.nav.execute_command(command)
        end_time = time.time()
        
        # Verify execution
        self.assertTrue(success)
        self.assertGreaterEqual(end_time - start_time, command.duration)

if __name__ == '__main__':
    unittest.main() 