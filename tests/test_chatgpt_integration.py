"""
Test cases for the ChatGPT Integration Module
"""

import unittest
import os
import time
import numpy as np
from unittest.mock import Mock, patch
from modules.chatgpt_integration import ChatGPTClient

class TestChatGPTClient(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        # Use a mock API key for testing
        self.api_key = "test_key"
        with patch.dict(os.environ, {'OPENAI_API_KEY': self.api_key}):
            self.client = ChatGPTClient()

    def test_initialization(self):
        """Test client initialization."""
        # Test initialization with explicit API key
        client = ChatGPTClient(api_key=self.api_key)
        self.assertEqual(client._api_key, self.api_key)
        
        # Test initialization with environment variable
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env_key'}):
            client = ChatGPTClient()
            self.assertEqual(client._api_key, 'env_key')
        
        # Test initialization with no API key
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            with self.assertRaises(ValueError):
                ChatGPTClient()

    @patch('openai.OpenAI')
    def test_send_sensor_data(self, mock_openai):
        """Test sending sensor data."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Test with sample sensor data
        sensor_data = {
            'proximity': 30.5,
            'temperature': 25.0,
            'battery': 90
        }
        
        response = self.client.send_sensor_data(sensor_data)
        self.assertEqual(response, "Test response")
        
        # Verify API was called with correct format
        mock_openai.return_value.chat.completions.create.assert_called_once()

    @patch('openai.OpenAI')
    def test_send_image_for_analysis(self, mock_openai):
        """Test sending image for analysis."""
        # Create a dummy image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Image analysis result"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        response = self.client.send_image_for_analysis(image)
        self.assertEqual(response, "Image analysis result")
        
        # Verify API was called with vision model
        mock_openai.return_value.chat.completions.create.assert_called_once()
        call_args = mock_openai.return_value.chat.completions.create.call_args[1]
        self.assertEqual(call_args['model'], "gpt-4-vision-preview")

    @patch('openai.OpenAI')
    def test_get_navigation_advice(self, mock_openai):
        """Test getting navigation advice."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Navigation advice"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Test data
        current_pose = {'x': 10.0, 'y': 20.0, 'theta': 45.0}
        obstacle_data = {'front': 50.0, 'left': 30.0, 'right': 40.0}
        target = {'x': 100.0, 'y': 100.0}
        
        response = self.client.get_navigation_advice(current_pose, obstacle_data, target)
        self.assertEqual(response, "Navigation advice")

    @patch('openai.OpenAI')
    def test_get_exploration_strategy(self, mock_openai):
        """Test getting exploration strategy."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Exploration strategy"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Test data
        explored_percentage = 35.5
        frontier_points = [(10, 20), (30, 40), (50, 60)]
        
        response = self.client.get_exploration_strategy(explored_percentage, frontier_points)
        self.assertEqual(response, "Exploration strategy")

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        start_time = time.time()
        
        # Make two quick requests
        with patch('openai.OpenAI') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test response"))]
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            
            self.client._send_message("Test 1")
            self.client._send_message("Test 2")
            
            # Check that at least min_request_interval seconds passed
            elapsed = time.time() - start_time
            self.assertGreaterEqual(elapsed, self.client._min_request_interval)

    def test_conversation_history(self):
        """Test conversation history management."""
        # Add some messages
        with patch('openai.OpenAI') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Response"))]
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            
            for i in range(self.client._max_history_length + 5):
                self.client._send_message(f"Test message {i}")
            
            # Check history length is maintained
            history_length = len(self.client._conversation_history)
            self.assertLessEqual(history_length, self.client._max_history_length * 2)
        
        # Test clearing history
        self.client.clear_conversation_history()
        self.assertEqual(len(self.client._conversation_history), 0)

if __name__ == '__main__':
    unittest.main() 