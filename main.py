"""
Main Application for PiCar-X Robot
Integrates all modules and provides the main control loop.

This module serves as the entry point for the PiCar-X robot system, orchestrating
all subsystems including sensors, navigation, voice commands, and ChatGPT integration.
"""

import os
import time
import signal
import sys
import logging
import logging.handlers
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from modules.mapping_module import OccupancyGrid, RobotPose
from modules.navigation_module import NavigationController
from modules.voice_command_handler import VoiceCommandHandler
from modules.chatgpt_integration import ChatGPTClient
from modules.sensor_module import SensorModule
from modules.system_monitor import SystemMonitor, SystemStatus

# Configure logging
def setup_logging() -> None:
    """Configure the logging system with both file and console handlers."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        'robot.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

class RobotSystem:
    """
    Main robot control system that integrates all subsystems and manages the robot's operation.
    
    This class is responsible for:
    - Initializing and managing all subsystems (sensors, navigation, voice, etc.)
    - Running the main control loop
    - Handling autonomous exploration
    - Managing system shutdown
    - Ensuring safe operation through system monitoring
    """
    
    def __init__(self) -> None:
        """Initialize the complete robot system."""
        logger.info("Initializing robot system...")
        
        # System state
        self.is_running: bool = False
        self.autonomous_mode: bool = False
        self.emergency_stop_triggered: bool = False
        
        # Initialize system monitor first for safety
        self.system_monitor: SystemMonitor = SystemMonitor(
            emergency_stop_callback=self._handle_emergency_stop
        )
        
        # Initialize mapping
        self.grid: OccupancyGrid = OccupancyGrid(width_cm=500, height_cm=500, resolution_cm=1)
        
        # Initialize navigation
        self.nav: NavigationController = NavigationController(self.grid)
        
        # Initialize sensors
        self.sensors: SensorModule = SensorModule()
        
        # Initialize voice commands with emergency stop
        self.voice_handler: VoiceCommandHandler = VoiceCommandHandler(
            navigation=self.nav,
            emergency_stop_callback=self._handle_emergency_stop
        )
        
        # Initialize ChatGPT if API key is available
        self.chatgpt: Optional[ChatGPTClient] = None
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                self.chatgpt = ChatGPTClient(api_key)
                logger.info("ChatGPT integration initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize ChatGPT: {str(e)}")
        else:
            logger.warning("No OpenAI API key found in environment variables")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info("Robot system initialization complete")

    def _handle_emergency_stop(self) -> None:
        """
        Handle emergency stop condition.
        
        This method:
        1. Immediately stops all motion
        2. Disables autonomous mode
        3. Sets emergency stop flag
        4. Initiates safe shutdown if necessary
        """
        logger.critical("EMERGENCY STOP TRIGGERED")
        
        self.emergency_stop_triggered = True
        self.autonomous_mode = False
        
        try:
            # Immediately stop all motion
            self.nav.emergency_stop()
            
            # If the emergency was triggered by a critical system condition,
            # initiate shutdown
            current_status = self.system_monitor.get_current_status()
            if (current_status.battery_voltage <= SystemMonitor.BATTERY_CRITICAL_VOLTAGE or
                current_status.cpu_temperature >= SystemMonitor.CPU_TEMP_CRITICAL):
                logger.critical("Critical system condition detected - initiating shutdown")
                self.shutdown()
                
        except Exception as e:
            logger.error(f"Error during emergency stop: {str(e)}", exc_info=True)
            # Force shutdown if emergency stop handling fails
            self.shutdown()

    def start(self) -> None:
        """Start the robot system and begin the main control loop."""
        try:
            logger.info("Starting PiCar-X Robot System...")
            
            # Start system monitoring first
            self.system_monitor.start()
            logger.info("System monitoring active")
            
            # Check initial system status
            initial_status = self.system_monitor.get_current_status()
            if not self._check_safe_to_start(initial_status):
                logger.error("System not safe to start - aborting")
                return
            
            # Start sensor systems
            self.sensors.start_proximity_polling()
            logger.info("Sensors initialized and polling started")
            
            # Start voice command handling
            self.voice_handler.start_listening()
            logger.info("Voice command system activated")
            
            # Main control loop
            self.is_running = True
            self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start robot system: {str(e)}", exc_info=True)
            self.shutdown()

    def _check_safe_to_start(self, status: SystemStatus) -> bool:
        """
        Check if it's safe to start the system.
        
        Args:
            status: Current system status
            
        Returns:
            bool: True if safe to start, False otherwise
        """
        if status.battery_voltage <= SystemMonitor.BATTERY_WARNING_VOLTAGE:
            logger.error(f"Battery voltage too low to start: {status.battery_voltage:.1f}V")
            return False
            
        if status.cpu_temperature >= SystemMonitor.CPU_TEMP_WARNING:
            logger.error(f"CPU temperature too high to start: {status.cpu_temperature:.1f}°C")
            return False
            
        if status.cpu_usage >= SystemMonitor.CPU_USAGE_WARNING:
            logger.error(f"CPU usage too high to start: {status.cpu_usage:.1f}%")
            return False
            
        return True

    def _main_loop(self) -> None:
        """
        Main control loop for the robot.
        
        This method runs continuously while the robot is active, handling:
        - Sensor updates
        - Autonomous exploration
        - System monitoring
        - Safety checks
        """
        logger.info("Entering main control loop")
        
        last_sensor_update: float = 0
        last_status_check: float = 0
        sensor_update_interval: float = 0.1  # 10 Hz
        status_check_interval: float = 1.0   # 1 Hz
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # Regular sensor updates
                if current_time - last_sensor_update >= sensor_update_interval:
                    self._update_sensors()
                    last_sensor_update = current_time
                
                # Regular system status check
                if current_time - last_status_check >= status_check_interval:
                    status = self.system_monitor.get_current_status()
                    if not self._check_safe_to_continue(status):
                        logger.warning("Unsafe conditions detected - pausing operation")
                        self.autonomous_mode = False
                    last_status_check = current_time
                
                # Autonomous exploration if enabled and safe
                if self.autonomous_mode and not self.emergency_stop_triggered:
                    self._autonomous_update()
                
                # Small sleep to prevent CPU overuse
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                continue

    def _check_safe_to_continue(self, status: SystemStatus) -> bool:
        """
        Check if it's safe to continue operation.
        
        Args:
            status: Current system status
            
        Returns:
            bool: True if safe to continue, False otherwise
        """
        if self.emergency_stop_triggered:
            return False
            
        if status.battery_voltage <= SystemMonitor.BATTERY_WARNING_VOLTAGE:
            return False
            
        if status.cpu_temperature >= SystemMonitor.CPU_TEMP_WARNING:
            return False
            
        return True

    def _update_sensors(self) -> None:
        """
        Update sensor readings and mapping.
        
        This method:
        - Reads proximity sensors
        - Updates the occupancy grid
        - Checks for obstacles
        - Processes camera data
        - Sends data to ChatGPT if available
        """
        try:
            # Get proximity reading
            distance: Optional[float] = self.sensors.read_proximity()
            if distance is not None:
                # Update map
                current_pose: RobotPose = self.nav.get_pose()
                self.grid.update_occupancy(distance, current_pose.theta, current_pose)
                
                # Check for obstacles
                if distance < self.nav._min_obstacle_distance:
                    logger.warning(f"Obstacle detected at distance: {distance:.2f}cm")
                    self.nav.avoid_obstacle(distance, 0)  # Assuming obstacle is straight ahead
                
                # Get ChatGPT insights if available
                if self.chatgpt:
                    sensor_data: Dict[str, float] = {
                        'proximity': distance,
                        'pose_x': current_pose.x,
                        'pose_y': current_pose.y,
                        'pose_theta': current_pose.theta
                    }
                    self.chatgpt.send_sensor_data(sensor_data)
            
            # Capture and analyze camera image periodically
            success, frame = self.sensors.capture_image()
            if success and self.chatgpt:
                self.chatgpt.send_image_for_analysis(frame)
                
        except Exception as e:
            logger.error(f"Error updating sensors: {str(e)}", exc_info=True)

    def _autonomous_update(self) -> None:
        """
        Update autonomous exploration behavior.
        
        This method:
        - Finds unexplored areas (frontiers)
        - Gets exploration strategy from ChatGPT
        - Navigates to selected points
        """
        try:
            # Find nearest frontier
            frontier = self.nav.find_nearest_frontier()
            if frontier:
                # Get exploration strategy from ChatGPT if available
                if self.chatgpt:
                    strategy = self.chatgpt.get_exploration_strategy(
                        explored_area_percentage=10.0,  # TODO: Calculate actual percentage
                        frontier_points=[frontier]
                    )
                    logger.debug(f"Received exploration strategy: {strategy}")
                
                # Navigate to frontier
                logger.info(f"Navigating to frontier at ({frontier[0]}, {frontier[1]})")
                self.nav.navigate_to_point(frontier[0], frontier[1])
                
        except Exception as e:
            logger.error(f"Error in autonomous update: {str(e)}", exc_info=True)

    def toggle_autonomous_mode(self) -> None:
        """Toggle autonomous exploration mode on/off."""
        self.autonomous_mode = not self.autonomous_mode
        status = "enabled" if self.autonomous_mode else "disabled"
        logger.info(f"Autonomous mode {status}")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number received
            frame: Current stack frame
        """
        logger.info(f"Shutdown signal {signum} received")
        self.shutdown()

    def shutdown(self) -> None:
        """
        Perform a clean shutdown of all systems.
        
        This method:
        - Stops the main control loop
        - Releases all hardware resources
        - Saves the final map state
        - Exits the program
        """
        logger.info("Initiating robot system shutdown...")
        
        # Stop main loop
        self.is_running = False
        
        # Stop all subsystems
        try:
            # Stop monitoring first to prevent false alarms during shutdown
            self.system_monitor.stop()
            
            # Stop other subsystems
            self.sensors.release()
            self.voice_handler.stop_listening()
            self.nav.stop()
            
            # Save final map state
            self.grid.save_grid_to_file('final_map.json')
            logger.info("Final map state saved")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
        
        logger.info("Shutdown complete")
        sys.exit(0)

def main() -> None:
    """Main entry point for the robot system."""
    robot = RobotSystem()
    robot.start()

if __name__ == '__main__':
    main()
