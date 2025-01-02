"""
Test cases for the Sensor Module
"""

import unittest
import time
import numpy as np
import speech_recognition as sr
from modules.sensor_module import SensorModule

class TestSensorModule(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.sensor = SensorModule()

    def tearDown(self):
        """Clean up after tests."""
        self.sensor.release()

    def test_proximity_polling(self):
        """Test that proximity polling works and returns reasonable values."""
        self.sensor.start_proximity_polling()
        
        # Wait for some readings to accumulate
        time.sleep(0.5)
        
        # Get a reading
        reading = self.sensor.read_proximity()
        
        # Check that reading is within expected range
        self.assertIsNotNone(reading)
        self.assertGreaterEqual(reading, 0)
        self.assertLessEqual(reading, 100)
        
        self.sensor.stop_proximity_polling()

    def test_camera_capture(self):
        """Test that camera capture returns expected format."""
        success, frame = self.sensor.capture_image()
        
        if success:
            # If camera is available, check frame properties
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(len(frame.shape), 3)  # Height, width, channels
            self.assertEqual(frame.shape[0], 480)  # Height
            self.assertEqual(frame.shape[1], 640)  # Width
        else:
            # If no camera available, frame should be None
            self.assertIsNone(frame)

    def test_audio_capture_start_stop(self):
        """Test that audio capture can be started and stopped."""
        # Start audio capture
        started = self.sensor.start_audio_capture()
        
        if self.sensor._microphone is not None:
            # If microphone is available, it should start successfully
            self.assertTrue(started)
            self.assertTrue(self.sensor._is_listening)
            self.assertIsNotNone(self.sensor._audio_thread)
            self.assertTrue(self.sensor._audio_thread.is_alive())
            
            # Stop audio capture
            self.sensor.stop_audio_capture()
            time.sleep(0.1)  # Give thread time to stop
            self.assertFalse(self.sensor._is_listening)
            self.assertFalse(self.sensor._audio_thread.is_alive())
        else:
            # If no microphone available, it should fail gracefully
            self.assertFalse(started)

    def test_speech_recognition(self):
        """Test speech recognition with mock audio data."""
        # Create a mock AudioData object
        # Note: This is a basic test that just verifies the method handles None correctly
        result, text = self.sensor.recognize_speech(None)
        self.assertFalse(result)
        self.assertIsNone(text)
        
        # Note: Testing with real AudioData would require actual audio input
        # or mock audio data, which is beyond the scope of this basic test

if __name__ == '__main__':
    unittest.main() 