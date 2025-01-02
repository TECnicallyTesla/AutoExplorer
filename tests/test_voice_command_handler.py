"""
Test cases for the Voice Command Handler Module
"""

import unittest
import math
from unittest.mock import Mock, patch
import speech_recognition as sr
from modules.mapping_module import OccupancyGrid, RobotPose
from modules.navigation_module import NavigationController
from modules.voice_command_handler import VoiceCommandHandler

class TestVoiceCommandHandler(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.grid = OccupancyGrid(width_cm=100, height_cm=100, resolution_cm=1)
        self.nav = NavigationController(self.grid)
        self.voice_handler = VoiceCommandHandler(self.nav)

    def test_initialization(self):
        """Test handler initialization."""
        self.assertEqual(self.voice_handler._wake_word, "robot")
        self.assertFalse(self.voice_handler._is_listening)
        self.assertIsNone(self.voice_handler._command_thread)
        
        # Check that all command types are initialized
        commands = self.voice_handler.get_available_commands()
        self.assertIn('stop', commands)
        self.assertIn('move', commands)
        self.assertIn('turn', commands)
        self.assertIn('explore', commands)
        self.assertIn('status', commands)

    def test_command_processing(self):
        """Test command text processing."""
        # Test stop command
        self.assertTrue(self.voice_handler._process_command("stop"))
        self.assertTrue(self.voice_handler._process_command("halt"))
        
        # Test move commands
        self.assertTrue(self.voice_handler._process_command("move forward"))
        self.assertTrue(self.voice_handler._process_command("move forward 30 centimeters"))
        
        # Test turn commands
        self.assertTrue(self.voice_handler._process_command("turn left"))
        self.assertTrue(self.voice_handler._process_command("turn right 45 degrees"))
        
        # Test invalid command
        self.assertFalse(self.voice_handler._process_command("invalid command"))

    def test_wake_word(self):
        """Test wake word functionality."""
        # Test default wake word
        self.assertEqual(self.voice_handler._wake_word, "robot")
        
        # Test setting new wake word
        self.voice_handler.set_wake_word("assistant")
        self.assertEqual(self.voice_handler._wake_word, "assistant")
        
        # Test wake word is case insensitive
        self.voice_handler.set_wake_word("PICAR")
        self.assertEqual(self.voice_handler._wake_word, "picar")

    def test_custom_command(self):
        """Test adding custom commands."""
        # Create a mock handler
        mock_handler = Mock(return_value=True)
        
        # Add custom command
        self.voice_handler.add_custom_command(
            "test",
            [r"test command (\d+)"],
            mock_handler
        )
        
        # Verify command was added
        commands = self.voice_handler.get_available_commands()
        self.assertIn('test', commands)
        
        # Test processing custom command
        self.assertTrue(self.voice_handler._process_command("test command 123"))
        mock_handler.assert_called_once()

    @patch('speech_recognition.Recognizer.recognize_google')
    def test_command_handlers(self, mock_recognize):
        """Test individual command handlers."""
        # Test stop handler
        match = Mock()
        self.assertTrue(self.voice_handler._handle_stop(match))
        
        # Test move handler
        match = Mock()
        match.group = Mock(side_effect=[None, "forward"])  # No distance, forward direction
        self.assertTrue(self.voice_handler._handle_move(match))
        
        # Test turn handler
        match = Mock()
        match.group = Mock(side_effect=["90", "left"])  # 90 degrees, left direction
        self.assertTrue(self.voice_handler._handle_turn(match))
        
        # Test explore handler
        match = Mock()
        # Mock a frontier point
        self.nav.find_nearest_frontier = Mock(return_value=(50, 50))
        self.assertTrue(self.voice_handler._handle_explore(match))
        
        # Test status handler
        match = Mock()
        self.assertTrue(self.voice_handler._handle_status(match))

    def test_start_stop_listening(self):
        """Test starting and stopping voice command listening."""
        # Start listening
        self.assertTrue(self.voice_handler.start_listening())
        self.assertTrue(self.voice_handler._is_listening)
        self.assertIsNotNone(self.voice_handler._command_thread)
        
        # Try starting again (should return False)
        self.assertFalse(self.voice_handler.start_listening())
        
        # Stop listening
        self.voice_handler.stop_listening()
        self.assertFalse(self.voice_handler._is_listening)

if __name__ == '__main__':
    unittest.main() 