"""
Optimized navigation module for the PiCar-X robot.
"""

import numpy as np
import logging
import os
import sys
from typing import List, Tuple, Optional
from dataclasses import dataclass
from picarx import Picarx
from os import geteuid
import time

from modules.mapping_module import OccupancyGrid, RobotPose

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check for root privileges
if geteuid() != 0:
    print("\033[0;33mThe program needs to be run using sudo, otherwise hardware control may fail.\033[0m")

# Check if running on Raspberry Pi
def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except:
        return False

@dataclass
class MovementCommand:
    """Represents a movement command for the robot."""
    linear_speed: float  # Speed in cm/s
    angular_speed: float  # Speed in rad/s
    duration: float  # Duration in seconds

class NavigationController:
    def __init__(self, grid: OccupancyGrid) -> None:
        """
        Initialize the navigation controller.
        
        Args:
            grid: The occupancy grid for mapping and planning
        """
        self.grid = grid
        self._current_pose = RobotPose(x=0.0, y=0.0, theta=0.0)
        self.picar = None
        
        # Try to initialize PiCar-X hardware
        try:
            logger.debug("Attempting to initialize PiCar-X hardware...")
            self.picar = Picarx()
            logger.info("PiCar-X hardware initialized successfully")
        except Exception as e:
            logger.debug(f"Detailed hardware initialization error: {str(e)}", exc_info=True)
            logger.warning("Hardware initialization failed - some functions may be limited")
        
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
    
    def _generate_motion_primitives(self) -> List[MovementCommand]:
        """
        Generate a set of basic motion primitives for navigation.
        
        Returns:
            List[MovementCommand]: List of basic movement commands
        """
        primitives = []
        
        # Forward movement
        primitives.append(MovementCommand(
            linear_speed=self.max_speed,
            angular_speed=0.0,
            duration=1.0
        ))
        
        # Turns (left and right)
        for angle in [-90, 90]:  # degrees
            primitives.append(MovementCommand(
                linear_speed=0.0,
                angular_speed=float(angle),
                duration=1.0
            ))
        
        logger.debug(f"Generated {len(primitives)} motion primitives")
        return primitives
    
    def _safe_hardware_call(self, func_name: str, *args, **kwargs):
        """
        Safely call a hardware function, logging errors but not crashing.
        
        Args:
            func_name: Name of the PiCar-X function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            bool: True if successful, False if failed
        """
        if self.picar is None:
            logger.debug(f"Hardware call to {func_name} skipped - no hardware initialized")
            return False
            
        try:
            func = getattr(self.picar, func_name)
            func(*args, **kwargs)
            return True
        except Exception as e:
            logger.debug(f"Hardware call to {func_name} failed: {str(e)}")
            return False
    
    def move_forward(self, speed: Optional[float] = None) -> bool:
        """
        Move the robot forward.
        
        Args:
            speed: Speed percentage (0-100), uses max_speed if None
        
        Returns:
            bool: True if command was successful
        """
        speed = speed if speed is not None else self.max_speed
        return self._safe_hardware_call('forward', speed)
    
    def move_backward(self, speed: Optional[float] = None) -> bool:
        """
        Move the robot backward.
        
        Args:
            speed: Speed percentage (0-100), uses max_speed if None
        
        Returns:
            bool: True if command was successful
        """
        speed = speed if speed is not None else self.max_speed
        return self._safe_hardware_call('backward', speed)
    
    def turn_left(self, angle: float = 90) -> bool:
        """
        Turn the robot left.
        
        Args:
            angle: Angle in degrees
        
        Returns:
            bool: True if command was successful
        """
        return self._safe_hardware_call('set_dir_servo_angle', angle)
    
    def turn_right(self, angle: float = -90) -> bool:
        """
        Turn the robot right.
        
        Args:
            angle: Angle in degrees (negative for right turn)
        
        Returns:
            bool: True if command was successful
        """
        return self._safe_hardware_call('set_dir_servo_angle', angle)
    
    def stop(self) -> bool:
        """
        Stop all robot movement.
        
        Returns:
            bool: True if command was successful
        """
        stop_success = self._safe_hardware_call('stop')
        angle_success = self._safe_hardware_call('set_dir_servo_angle', 0)
        return stop_success and angle_success
    
    def emergency_stop(self) -> None:
        """Immediately stop all motion."""
        self.stop()
        logger.critical("Emergency stop executed")
    
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
