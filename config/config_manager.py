"""
Configuration management for the PiCar-X robot.

This module handles:
- Loading configuration from YAML files
- Validating configuration values
- Providing typed configuration access
- Merging default and user configurations
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SystemConfig:
    """System-wide configuration parameters."""
    log_level: str
    log_file: str
    log_max_size_mb: int
    log_backup_count: int

@dataclass
class MappingConfig:
    """Mapping module configuration."""
    width_cm: int
    height_cm: int
    resolution_cm: float
    save_interval_sec: int
    compression_enabled: bool
    cache_size: int
    unknown_threshold: float
    free_threshold: float
    occupied_threshold: float

@dataclass
class NavigationConfig:
    """Navigation module configuration."""
    min_obstacle_distance_cm: float
    robot_radius_cm: float
    safety_margin_cm: float
    max_planning_time_sec: float
    replan_interval_sec: float
    path_smoothing: bool
    motion_primitives: Dict[str, Any]

@dataclass
class HardwareConfig:
    """Hardware-specific configuration."""
    motor_max_speed: int
    motor_acceleration: int
    servo_max_angle: int
    camera_resolution: tuple
    camera_fps: int

@dataclass
class SafetyConfig:
    """Safety-related configuration."""
    battery: Dict[str, float]
    temperature: Dict[str, float]
    emergency_stop: Dict[str, Any]

@dataclass
class WebConfig:
    """Web interface configuration."""
    host: str
    port: int
    update_interval_ms: int
    features: Dict[str, bool]
    security: Dict[str, Any]

@dataclass
class ProcessingConfig:
    """Multiprocessing configuration."""
    mapping: Dict[str, Any]
    planning: Dict[str, Any]
    vision: Dict[str, Any]

class ConfigManager:
    """
    Manages robot configuration loading and validation.
    
    Features:
    - YAML configuration loading
    - Type validation
    - Default value handling
    - Configuration merging
    """
    
    def __init__(self, config_dir: Optional[str] = None) -> None:
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir or os.path.dirname(__file__))
        self._load_config()
    
    def _load_config(self) -> None:
        """Load and validate configuration from files."""
        try:
            # Load default configuration
            default_path = self.config_dir / "default_config.yaml"
            with open(default_path) as f:
                self._config = yaml.safe_load(f)
            
            # Load user configuration if it exists
            user_path = self.config_dir / "config.yaml"
            if user_path.exists():
                with open(user_path) as f:
                    user_config = yaml.safe_load(f)
                # Merge configurations
                self._merge_configs(self._config, user_config)
            
            # Create typed configuration objects
            self._create_typed_configs()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}", exc_info=True)
            raise
    
    def _merge_configs(self, base: Dict, overlay: Dict) -> None:
        """
        Recursively merge two configuration dictionaries.
        
        Args:
            base: Base configuration to merge into
            overlay: Configuration to merge from
        """
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
    
    def _create_typed_configs(self) -> None:
        """Create typed configuration objects from raw dictionary."""
        self.system = SystemConfig(**self._config['system'])
        self.mapping = MappingConfig(**self._config['mapping'])
        self.navigation = NavigationConfig(**self._config['navigation'])
        self.hardware = HardwareConfig(**self._config['hardware'])
        self.safety = SafetyConfig(**self._config['safety'])
        self.web = WebConfig(**self._config['web'])
        self.processing = ProcessingConfig(**self._config['processing'])
    
    def validate(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Validate system configuration
            if self.system.log_max_size_mb <= 0:
                raise ValueError("Log max size must be positive")
            
            # Validate mapping configuration
            if self.mapping.width_cm <= 0 or self.mapping.height_cm <= 0:
                raise ValueError("Map dimensions must be positive")
            if self.mapping.resolution_cm <= 0:
                raise ValueError("Map resolution must be positive")
            
            # Validate navigation configuration
            if self.navigation.min_obstacle_distance_cm <= 0:
                raise ValueError("Minimum obstacle distance must be positive")
            
            # Validate hardware configuration
            if not (0 <= self.hardware.motor_max_speed <= 100):
                raise ValueError("Motor speed must be between 0 and 100")
            
            # Validate safety configuration
            if self.safety.battery['critical_voltage'] >= self.safety.battery['warning_voltage']:
                raise ValueError("Critical voltage must be less than warning voltage")
            
            # Validate web configuration
            if self.web.port < 0 or self.web.port > 65535:
                raise ValueError("Web port must be between 0 and 65535")
            
            # Validate processing configuration
            for config in [self.processing.mapping, self.processing.planning, self.processing.vision]:
                if config['enabled'] and config.get('num_workers', 0) <= 0:
                    raise ValueError("Number of workers must be positive when enabled")
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}", exc_info=True)
            return False
    
    def save_user_config(self) -> None:
        """Save current configuration as user configuration."""
        try:
            user_path = self.config_dir / "config.yaml"
            with open(user_path, 'w') as f:
                yaml.safe_dump(self._config, f, default_flow_style=False)
            logger.info(f"User configuration saved to {user_path}")
        except Exception as e:
            logger.error(f"Error saving user configuration: {str(e)}", exc_info=True)
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary."""
        return self._config.copy() 