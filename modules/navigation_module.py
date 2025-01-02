"""
Optimized navigation module for the PiCar-X robot.
"""

import numpy as np
import logging
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass
from picarx import Picarx
from os import geteuid
import time

from modules.mapping_module import OccupancyGrid, RobotPose

logger = logging.getLogger(__name__)

# Check for root privileges
if geteuid() != 0:
    print("\033[0;33mThe program needs to be run using sudo, otherwise hardware control may fail.\033[0m")

# Set GPIO backend
os.environ["GPIOZERO_PIN_FACTORY"] = "rpi"

@dataclass
class MovementCommand:
    """Represents a movement command for the robot."""
    linear_speed: float  # Speed in cm/s
    angular_speed: float  # Speed in rad/s
    duration: float  # Duration in seconds

class NavigationController:
    """
    Efficient navigation controller with optimized path planning.
    
    Features:
    - Cached motion primitives
    - Vectorized collision checking
    - Efficient A* implementation
    - Dynamic obstacle avoidance
    """
    
    def __init__(self, grid: OccupancyGrid) -> None:
        """
        Initialize the navigation controller.
        
        Args:
            grid: The occupancy grid for mapping and planning
        """
        self.grid = grid
        self._current_pose = RobotPose(x=0.0, y=0.0, theta=0.0)
        
        # Initialize PiCar-X hardware with retries
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                self.picar = Picarx()
                logger.info("PiCar-X hardware initialized successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to initialize PiCar-X hardware (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to initialize PiCar-X hardware after {max_retries} attempts: {e}")
                    logger.error("Please check: 1) You are running with sudo, 2) I2C is enabled, 3) GPIO permissions are set")
                    raise
        
        # Navigation parameters
        self.min_obstacle_distance = 20.0  # cm
        self.robot_radius = 15.0  # cm
        self.safety_margin = 5.0  # cm
        self.max_speed = 50  # Maximum speed (percentage)
        
        # Motion primitives (pre-computed for efficiency)
        self._motion_primitives = self._generate_motion_primitives()
        
        # Path planning cache
        self._current_path: List[Tuple[int, int]] = []
        self._path_target: Optional[Tuple[int, int]] = None
        
        logger.info("Navigation controller initialized")
    
    def move_forward(self, speed: Optional[float] = None) -> bool:
        """
        Move the robot forward.
        
        Args:
            speed: Speed percentage (0-100), uses max_speed if None
        
        Returns:
            bool: True if command was successful
        """
        try:
            speed = speed if speed is not None else self.max_speed
            self.picar.forward(speed)
            return True
        except Exception as e:
            logger.error(f"Error moving forward: {e}")
            return False
    
    def move_backward(self, speed: Optional[float] = None) -> bool:
        """
        Move the robot backward.
        
        Args:
            speed: Speed percentage (0-100), uses max_speed if None
        
        Returns:
            bool: True if command was successful
        """
        try:
            speed = speed if speed is not None else self.max_speed
            self.picar.backward(speed)
            return True
        except Exception as e:
            logger.error(f"Error moving backward: {e}")
            return False
    
    def turn_left(self, angle: float = 90) -> bool:
        """
        Turn the robot left.
        
        Args:
            angle: Angle in degrees
        
        Returns:
            bool: True if command was successful
        """
        try:
            self.picar.set_dir_servo_angle(angle)
            return True
        except Exception as e:
            logger.error(f"Error turning left: {e}")
            return False
    
    def turn_right(self, angle: float = -90) -> bool:
        """
        Turn the robot right.
        
        Args:
            angle: Angle in degrees (negative for right turn)
        
        Returns:
            bool: True if command was successful
        """
        try:
            self.picar.set_dir_servo_angle(angle)
            return True
        except Exception as e:
            logger.error(f"Error turning right: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop all robot movement.
        
        Returns:
            bool: True if command was successful
        """
        try:
            self.picar.stop()
            self.picar.set_dir_servo_angle(0)  # Reset steering
            return True
        except Exception as e:
            logger.error(f"Error stopping: {e}")
            return False
    
    def emergency_stop(self) -> None:
        """Immediately stop all motion."""
        try:
            self.picar.stop()
            self.picar.set_dir_servo_angle(0)
            logger.critical("Emergency stop executed")
        except Exception as e:
            logger.error(f"Error in emergency stop: {e}")
    
    def set_speed(self, speed: float) -> bool:
        """
        Set the robot's movement speed.
        
        Args:
            speed: Speed percentage (0-100)
        
        Returns:
            bool: True if command was successful
        """
        try:
            self.max_speed = min(max(0, speed), 100)
            return True
        except Exception as e:
            logger.error(f"Error setting speed: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up hardware resources."""
        try:
            self.stop()
            logger.info("Navigation system cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
