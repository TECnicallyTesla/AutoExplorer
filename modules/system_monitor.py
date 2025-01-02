"""
System monitoring and safety management for the PiCar-X robot.

This module handles:
- Battery voltage monitoring
- CPU temperature monitoring
- System resource tracking
- Emergency shutdown conditions
"""

import logging
import time
import threading
from typing import Optional, Dict, List, Callable
import psutil
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    """Container for system health metrics."""
    battery_voltage: float
    cpu_temperature: float
    cpu_usage: float
    memory_usage: float
    timestamp: float

class SystemMonitor:
    """
    Monitors system health and manages safety features.
    
    This class provides:
    - Real-time monitoring of system metrics
    - Safety thresholds and automatic shutdown
    - Warning notifications
    - Health status history
    """
    
    # Safety thresholds
    BATTERY_CRITICAL_VOLTAGE = 6.4  # Volts
    BATTERY_WARNING_VOLTAGE = 6.8   # Volts
    CPU_TEMP_CRITICAL = 80.0        # Celsius
    CPU_TEMP_WARNING = 70.0         # Celsius
    CPU_USAGE_WARNING = 90.0        # Percent
    
    def __init__(self, emergency_stop_callback: Callable[[], None]) -> None:
        """
        Initialize the system monitor.
        
        Args:
            emergency_stop_callback: Function to call for emergency shutdown
        """
        self.emergency_stop_callback = emergency_stop_callback
        self.is_running: bool = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Status history (last 60 seconds, 1 reading per second)
        self.status_history: List[SystemStatus] = []
        self.status_history_max_size = 60
        
        # Warning flags to prevent spam
        self._battery_warning_sent = False
        self._cpu_temp_warning_sent = False
        
        logger.info("System monitor initialized")
    
    def start(self) -> None:
        """Start the monitoring thread."""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="SystemMonitorThread"
        )
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop(self) -> None:
        """Stop the monitoring thread."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("System monitoring stopped")
    
    def get_current_status(self) -> SystemStatus:
        """Get the most recent system status."""
        return self._collect_system_metrics()
    
    def get_status_history(self) -> List[SystemStatus]:
        """Get the history of system status readings."""
        return self.status_history.copy()
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        while self.is_running:
            try:
                status = self._collect_system_metrics()
                self._check_safety_thresholds(status)
                self._update_history(status)
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}", exc_info=True)
                continue
    
    def _collect_system_metrics(self) -> SystemStatus:
        """Collect current system metrics."""
        try:
            # Get CPU temperature (implementation depends on hardware)
            cpu_temp = self._read_cpu_temperature()
            
            # Get battery voltage (implementation depends on hardware)
            battery_voltage = self._read_battery_voltage()
            
            # Get CPU and memory usage
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            return SystemStatus(
                battery_voltage=battery_voltage,
                cpu_temperature=cpu_temp,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}", exc_info=True)
            raise
    
    def _check_safety_thresholds(self, status: SystemStatus) -> None:
        """Check if any metrics exceed safety thresholds."""
        # Check battery voltage
        if status.battery_voltage <= self.BATTERY_CRITICAL_VOLTAGE:
            logger.critical("CRITICAL: Battery voltage critically low! Initiating emergency shutdown.")
            self.emergency_stop_callback()
        elif status.battery_voltage <= self.BATTERY_WARNING_VOLTAGE and not self._battery_warning_sent:
            logger.warning(f"Low battery warning: {status.battery_voltage:.1f}V")
            self._battery_warning_sent = True
        elif status.battery_voltage > self.BATTERY_WARNING_VOLTAGE:
            self._battery_warning_sent = False
        
        # Check CPU temperature
        if status.cpu_temperature >= self.CPU_TEMP_CRITICAL:
            logger.critical("CRITICAL: CPU temperature too high! Initiating emergency shutdown.")
            self.emergency_stop_callback()
        elif status.cpu_temperature >= self.CPU_TEMP_WARNING and not self._cpu_temp_warning_sent:
            logger.warning(f"High CPU temperature warning: {status.cpu_temperature:.1f}°C")
            self._cpu_temp_warning_sent = True
        elif status.cpu_temperature < self.CPU_TEMP_WARNING:
            self._cpu_temp_warning_sent = False
        
        # Check CPU usage
        if status.cpu_usage >= self.CPU_USAGE_WARNING:
            logger.warning(f"High CPU usage: {status.cpu_usage:.1f}%")
    
    def _update_history(self, status: SystemStatus) -> None:
        """Update the status history, maintaining the maximum size."""
        self.status_history.append(status)
        if len(self.status_history) > self.status_history_max_size:
            self.status_history = self.status_history[-self.status_history_max_size:]
    
    def _read_cpu_temperature(self) -> float:
        """Read the CPU temperature."""
        # TODO: Implement actual hardware reading
        # This is a placeholder that should be replaced with actual hardware implementation
        return 45.0  # Example value
    
    def _read_battery_voltage(self) -> float:
        """Read the battery voltage."""
        # TODO: Implement actual hardware reading
        # This is a placeholder that should be replaced with actual hardware implementation
        return 7.2  # Example value
