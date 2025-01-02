"""
Sensor Module for PiCar-X Robot
"""

import cv2
import numpy as np
import threading
import time
import speech_recognition as sr
from typing import Optional, Tuple, Dict
import logging
from picarx import Picarx  # Import PiCar-X SDK

logger = logging.getLogger(__name__)

class SensorModule:
    def __init__(self):
        """Initialize sensor systems."""
        # Initialize PiCar-X hardware
        try:
            self.picar = Picarx()
            logger.info("PiCar-X hardware initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PiCar-X hardware: {e}")
            raise

        # Threading control
        self._running = False
        self._proximity_thread = None
        
        # Sensor data storage
        self._latest_proximity = {
            'left': float('inf'),
            'center': float('inf'),
            'right': float('inf')
        }
        self._proximity_lock = threading.Lock()
        
        # Camera settings
        self._camera_resolution = (640, 480)
        self._camera = None
        
        # Speech recognition
        self._recognizer = sr.Recognizer()
        self._microphone = None
        
        # Initialize subsystems
        self._init_proximity_sensor()
        self._init_camera()
        self._init_microphone()

    def _init_proximity_sensor(self):
        """Initialize the proximity sensor hardware."""
        try:
            # Configure ultrasonic sensors
            self.picar.set_grayscale_reference(1000)  # Set grayscale reference value
            logger.info("Proximity sensors initialized")
        except Exception as e:
            logger.error(f"Error initializing proximity sensors: {e}")
            raise

    def _init_camera(self):
        """Initialize the camera hardware."""
        try:
            self._camera = cv2.VideoCapture(0)  # Use default camera
            if not self._camera.isOpened():
                raise Exception("Could not open camera")
            
            # Set resolution
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self._camera_resolution[0])
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self._camera_resolution[1])
            logger.info("Camera initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            self._camera = None

    def start_proximity_polling(self):
        """Start the proximity sensor polling in a background thread."""
        if self._proximity_thread is None or not self._proximity_thread.is_alive():
            self._running = True
            self._proximity_thread = threading.Thread(target=self._proximity_polling_loop)
            self._proximity_thread.daemon = True
            self._proximity_thread.start()
            logger.info("Proximity polling started")

    def stop_proximity_polling(self):
        """Stop the proximity sensor polling."""
        self._running = False
        if self._proximity_thread:
            self._proximity_thread.join()
        logger.info("Proximity polling stopped")

    def _proximity_polling_loop(self):
        """Background thread function for polling proximity sensors."""
        while self._running:
            try:
                # Read ultrasonic sensors
                left_distance = self.picar.get_grayscale_data()[0]
                center_distance = self.picar.get_grayscale_data()[1]
                right_distance = self.picar.get_grayscale_data()[2]
                
                # Update stored values thread-safely
                with self._proximity_lock:
                    self._latest_proximity['left'] = left_distance
                    self._latest_proximity['center'] = center_distance
                    self._latest_proximity['right'] = right_distance
                
                time.sleep(0.1)  # 10Hz polling rate
                
            except Exception as e:
                logger.error(f"Error reading proximity sensors: {e}")
                time.sleep(1)  # Wait before retrying

    def get_proximity_data(self) -> Dict[str, float]:
        """Get the latest proximity sensor readings."""
        with self._proximity_lock:
            return self._latest_proximity.copy()

    def capture_image(self) -> Optional[np.ndarray]:
        """Capture an image from the camera."""
        if self._camera is None:
            logger.warning("Camera not initialized")
            return None
            
        ret, frame = self._camera.read()
        if not ret:
            logger.error("Failed to capture image")
            return None
            
        return frame

    def cleanup(self):
        """Clean up resources."""
        self.stop_proximity_polling()
        
        if self._camera is not None:
            self._camera.release()
            
        # Cleanup PiCar-X hardware
        try:
            self.picar.stop()
            logger.info("PiCar-X hardware cleaned up")
        except Exception as e:
            logger.error(f"Error during PiCar-X cleanup: {e}")
