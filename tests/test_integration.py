"""
Integration Tests for PiCar-X Robot System
Tests the interaction between all modules in an end-to-end manner.
"""

import unittest
import time
import math
import numpy as np
from unittest.mock import Mock, patch
import os

from modules.mapping_module import OccupancyGrid, RobotPose
from modules.navigation_module import NavigationController, MovementCommand
from modules.voice_command_handler import VoiceCommandHandler
from modules.chatgpt_integration import ChatGPTClient
from modules.sensor_module import SensorModule

class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        """Set up the complete robot system for testing."""
        # Initialize all components
        self.grid = OccupancyGrid(width_cm=500, height_cm=500, resolution_cm=1)
        self.nav = NavigationController(self.grid)
        self.sensors = SensorModule()
        
        # Mock ChatGPT client to avoid API calls
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            self.chatgpt = ChatGPTClient()
        
        self.voice_handler = VoiceCommandHandler(self.nav)

    def tearDown(self):
        """Clean up after tests."""
        self.sensors.release()
        self.voice_handler.stop_listening()

    def test_sensor_to_mapping_integration(self):
        """Test sensor data integration with mapping."""
        # Start sensor polling
        self.sensors.start_proximity_polling()
        time.sleep(0.2)  # Wait for some readings
        
        # Get sensor reading
        distance = self.sensors.read_proximity()
        self.assertIsNotNone(distance)
        
        # Update map with sensor reading
        robot_pose = RobotPose(x=0, y=0, theta=0)
        self.grid.update_occupancy(distance, 0, robot_pose)
        
        # Verify map update
        grid_x, grid_y = self.grid.robot_to_grid(distance, 0)
        prob = self.grid.get_cell_probability(grid_x, grid_y)
        self.assertGreater(prob, 0.5)  # Should be marked as likely occupied

    def test_mapping_to_navigation_integration(self):
        """Test mapping integration with navigation."""
        # Create some obstacles in the map
        robot_pose = RobotPose(x=0, y=0, theta=0)
        self.grid.update_occupancy(50, 0, robot_pose)  # Obstacle ahead
        
        # Try to navigate
        target_x, target_y = 100, 0  # Try to go past obstacle
        success = self.nav.navigate_to_point(target_x, target_y)
        
        # Should have turned to avoid obstacle
        current_pose = self.nav.get_pose()
        self.assertNotEqual(current_pose.theta, 0)

    def test_voice_to_navigation_integration(self):
        """Test voice command integration with navigation."""
        # Mock the speech recognition to simulate voice command
        with patch('speech_recognition.Recognizer.recognize_google') as mock_recognize:
            mock_recognize.return_value = "move forward 50 centimeters"
            
            # Process command
            success = self.voice_handler._process_command(mock_recognize.return_value)
            self.assertTrue(success)
            
            # Verify navigation response
            current_pose = self.nav.get_pose()
            self.assertGreater(current_pose.x, 0)

    @patch('openai.OpenAI')
    def test_chatgpt_to_navigation_integration(self, mock_openai):
        """Test ChatGPT integration with navigation system."""
        # Mock ChatGPT response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(
            content="I recommend turning right to avoid the obstacle and then proceeding forward."
        ))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Get navigation advice
        current_pose = {'x': 0, 'y': 0, 'theta': 0}
        obstacle_data = {'front': 30.0}  # Obstacle close ahead
        advice = self.chatgpt.get_navigation_advice(current_pose, obstacle_data)
        
        # Verify advice was received
        self.assertIn("turning right", advice.lower())

    def test_full_exploration_sequence(self):
        """Test a complete exploration sequence using all components."""
        # Start sensor systems
        self.sensors.start_proximity_polling()
        
        # Mock ChatGPT for exploration strategy
        with patch('openai.OpenAI') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(
                content="Explore the nearest frontier point."
            ))]
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            
            # Create some explored area
            robot_pose = RobotPose(x=0, y=0, theta=0)
            for angle in [0, math.pi/2, math.pi, -math.pi/2]:
                distance = self.sensors.read_proximity()
                if distance:
                    self.grid.update_occupancy(distance, angle, robot_pose)
            
            # Get frontiers
            frontier = self.nav.find_nearest_frontier()
            self.assertIsNotNone(frontier)
            
            # Get exploration strategy
            strategy = self.chatgpt.get_exploration_strategy(
                explored_area_percentage=10.0,
                frontier_points=[frontier]
            )
            self.assertIn("frontier", strategy.lower())
            
            # Navigate to frontier
            if frontier:
                success = self.nav.navigate_to_point(frontier[0], frontier[1])
                self.assertTrue(success)

    def test_error_handling_integration(self):
        """Test error handling across module interactions."""
        # Test sensor failure handling
        self.sensors.release()  # Simulate sensor failure
        distance = self.sensors.read_proximity()
        self.assertIsNone(distance)  # Should handle gracefully
        
        # Test navigation with invalid target
        success = self.nav.navigate_to_point(float('inf'), float('inf'))
        self.assertFalse(success)  # Should handle invalid coordinates
        
        # Test voice command with invalid command
        success = self.voice_handler._process_command("invalid command")
        self.assertFalse(success)  # Should handle invalid command
        
        # Test ChatGPT API failure
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
            response = self.chatgpt.send_sensor_data({'test': 'data'})
            self.assertIn("error", response.lower())  # Should handle API failure

    def test_concurrent_operations(self):
        """Test multiple components operating concurrently."""
        # Start background processes
        self.sensors.start_proximity_polling()
        self.voice_handler.start_listening()
        
        # Simulate concurrent operations
        time.sleep(0.5)  # Let threads initialize
        
        # Verify all systems are running
        self.assertTrue(self.sensors._proximity_thread.is_alive())
        self.assertTrue(self.voice_handler._command_thread.is_alive())
        
        # Test sensor reading while voice processing is active
        distance = self.sensors.read_proximity()
        self.assertIsNotNone(distance)
        
        # Clean up
        self.sensors.stop_proximity_polling()
        self.voice_handler.stop_listening()
        
        # Verify clean shutdown
        time.sleep(0.2)
        self.assertFalse(self.sensors._proximity_thread.is_alive())
        self.assertFalse(self.voice_handler._command_thread.is_alive())

if __name__ == '__main__':
    unittest.main() 