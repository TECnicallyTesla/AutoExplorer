"""
Web interface for the PiCar-X robot.

This module provides:
- Real-time monitoring dashboard
- Manual control interface
- System configuration
- Data visualization
"""

import os
from flask import Flask, render_template, jsonify, request, Response, send_file
from flask_socketio import SocketIO, emit
import logging
import json
import cv2
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import asdict
import time
from threading import Lock
import io

from config.config_manager import ConfigManager, WebConfig
from modules.system_monitor import SystemMonitor, SystemStatus
from modules.mapping_module import OccupancyGrid

logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app)
config_lock = Lock()

class WebInterface:
    """
    Web interface for robot monitoring and control.
    
    Features:
    - Real-time status updates
    - Live camera feed
    - Manual control interface
    - Configuration management
    """
    
    def __init__(self, config: WebConfig, system_monitor: SystemMonitor, occupancy_grid: OccupancyGrid) -> None:
        """
        Initialize the web interface.
        
        Args:
            config: Web interface configuration
            system_monitor: System monitor instance
            occupancy_grid: Occupancy grid instance
        """
        self.config = config
        self.system_monitor = system_monitor
        self.occupancy_grid = occupancy_grid
        
        # Initialize Flask routes
        self._setup_routes()
        
        # Initialize WebSocket events
        self._setup_websocket_events()
        
        # Status update thread
        self._last_update = 0
        
        logger.info("Web interface initialized")
    
    def _setup_routes(self) -> None:
        """Set up Flask routes."""
        
        @app.route('/')
        def index():
            """Render the main dashboard."""
            return render_template('index.html', config=self.config)
        
        @app.route('/control')
        def control():
            """Render the manual control interface."""
            return render_template('control.html', config=self.config)
        
        @app.route('/config')
        def config():
            """Render the configuration interface."""
            return render_template('config.html', config=self.config)
        
        @app.route('/api/status')
        def get_status():
            """Get current system status."""
            status = self.system_monitor.get_current_status()
            return jsonify(asdict(status))
        
        @app.route('/api/config', methods=['GET', 'POST'])
        def handle_config():
            """Get or update configuration."""
            if request.method == 'GET':
                return jsonify(self.config.get_raw_config())
            else:
                with config_lock:
                    new_config = request.json
                    # Validate and update configuration
                    if self._validate_config(new_config):
                        self.config.update(new_config)
                        return jsonify({"status": "success"})
                    return jsonify({"status": "error", "message": "Invalid configuration"})
        
        @app.route('/api/map')
        def get_map():
            """Get the current occupancy grid map."""
            grid_data = self.occupancy_grid.get_grid_data()
            return jsonify({
                "grid": grid_data.tolist(),
                "width": self.occupancy_grid.width_cm,
                "height": self.occupancy_grid.height_cm,
                "resolution": self.occupancy_grid.resolution_cm
            })
        
        @app.route('/api/map/download')
        def download_map():
            """Download the current map as a file."""
            grid_data = self.occupancy_grid.get_grid_data()
            
            # Create JSON with map data
            map_data = {
                "grid": grid_data.tolist(),
                "metadata": {
                    "width_cm": self.occupancy_grid.width_cm,
                    "height_cm": self.occupancy_grid.height_cm,
                    "resolution_cm": self.occupancy_grid.resolution_cm,
                    "timestamp": time.time()
                }
            }
            
            # Convert to bytes
            map_bytes = json.dumps(map_data).encode('utf-8')
            
            return send_file(
                io.BytesIO(map_bytes),
                mimetype='application/json',
                as_attachment=True,
                download_name='map.json'
            )
        
        @app.route('/video_feed')
        def video_feed():
            """Video streaming route."""
            return Response(
                self._generate_frame(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
    
    def _setup_websocket_events(self) -> None:
        """Set up WebSocket event handlers."""
        
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info("Client connected")
            # Send initial map data
            self._send_map_update()
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info("Client disconnected")
        
        @socketio.on('control_command')
        def handle_control(data):
            """Handle manual control commands."""
            command = data.get('command')
            if command:
                self._execute_control_command(command)
        
        @socketio.on('map_command')
        def handle_map_command(data):
            """Handle map-related commands."""
            command = data.get('command')
            if command == 'center':
                # Center map on robot's current position
                self.occupancy_grid.center_on_robot()
                self._send_map_update()
            elif command == 'clear':
                # Clear the occupancy grid
                self.occupancy_grid.clear()
                self._send_map_update()
            elif command == 'save':
                # Save the current map
                try:
                    self.occupancy_grid.save('maps/current_map.json')
                    emit('map_command_response', {
                        'status': 'success',
                        'message': 'Map saved successfully'
                    })
                except Exception as e:
                    logger.error(f"Error saving map: {str(e)}", exc_info=True)
                    emit('map_command_response', {
                        'status': 'error',
                        'message': 'Failed to save map'
                    })
        
        @socketio.on('request_update')
        def handle_update_request():
            """Handle status update request."""
            self._send_status_update()
    
    def _generate_frame(self):
        """Generate video streaming frames."""
        while True:
            # Implementation would go here
            # This is a placeholder that should be replaced with actual implementation
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    
    def _send_status_update(self) -> None:
        """Send status update to connected clients."""
        current_time = time.time()
        if current_time - self._last_update >= self.config.update_interval_ms / 1000:
            status = self.system_monitor.get_current_status()
            socketio.emit('status_update', asdict(status))
            self._last_update = current_time
    
    def _send_map_update(self) -> None:
        """Send map update to connected clients."""
        grid_data = self.occupancy_grid.get_grid_data()
        path_data = self.occupancy_grid.get_current_path()
        
        socketio.emit('map_update', {
            'grid': grid_data.tolist(),
            'path': path_data
        })
    
    def _execute_control_command(self, command: Dict[str, Any]) -> None:
        """
        Execute a manual control command.
        
        Args:
            command: Control command parameters
        """
        # Implementation would go here
        logger.info(f"Executing control command: {command}")
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration changes.
        
        Args:
            config: New configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Basic validation
            if not isinstance(config, dict):
                return False
            
            # Validate web-specific configuration
            web_config = config.get('web', {})
            if not isinstance(web_config, dict):
                return False
            
            # Validate port
            port = web_config.get('port')
            if port is not None and not (0 <= port <= 65535):
                return False
            
            # Add more validation as needed
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {str(e)}", exc_info=True)
            return False
    
    def run(self, debug: bool = False) -> None:
        """
        Run the web interface.
        
        Args:
            debug: Whether to run in debug mode
        """
        host = self.config.host
        port = self.config.port
        
        logger.info(f"Starting web interface on {host}:{port}")
        socketio.run(app, host=host, port=port, debug=debug) 