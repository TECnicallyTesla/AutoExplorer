# PiCar-X Robot Explorer

An autonomous robot exploration system built for the PiCar-X platform, featuring grid-based mapping, voice control, and ChatGPT integration.

## Features

- **Autonomous Exploration**: Grid-based mapping and frontier exploration
- **Voice Control**: Natural language commands for robot control
- **ChatGPT Integration**: AI-powered decision making and commentary
- **System Monitoring**: Real-time monitoring of battery, CPU, and system status
- **Web Interface**: Real-time visualization and control dashboard

## Requirements

### Hardware
- PiCar-X Robot Kit
- Raspberry Pi 4 (recommended) or 3B+
- USB Microphone
- Camera Module (optional)

### Software
- Python 3.7+
- Required Python packages listed in `requirements.txt`

## Installation

1. **System Dependencies**
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv portaudio19-dev python3-pyaudio
```

2. **Project Setup**
```bash
# Clone repository
git clone https://github.com/yourusername/picar-x-robot.git
cd picar-x-robot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. **Configuration**
```bash
# Copy example config
cp config/default_config.yaml config/production.yaml
# Edit configuration as needed
nano config/production.yaml
```

## Usage

1. **Start the Robot**
```bash
# Activate virtual environment
source venv/bin/activate

# Run the main program
python main.py
```

2. **Voice Commands**
- "Robot, move forward [distance]"
- "Robot, turn left/right [degrees]"
- "Robot, stop"
- "Robot, explore"
- "Robot, status"

3. **Web Interface**
- Access `http://robot-ip:8080` for the web dashboard
- View real-time map and sensor data
- Control robot manually
- Monitor system status

## Development

### Project Structure
```
picar-x-robot/
├── config/                 # Configuration files
├── modules/               # Core modules
│   ├── sensor_module.py   # Sensor handling
│   ├── navigation_module.py # Movement and pathfinding
│   ├── mapping_module.py  # Grid-based mapping
│   ├── voice_command_handler.py # Voice control
│   ├── system_monitor.py  # System monitoring
│   └── chatgpt_integration.py # AI integration
├── web/                   # Web interface
├── tests/                 # Unit tests
├── main.py               # Main entry point
└── requirements.txt      # Python dependencies
```

### Running Tests
```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PiCar-X platform and documentation
- OpenAI for ChatGPT API
- Contributors and maintainers

## Version History

- v1.0.0 (2024-01-02)
  - Initial release
  - Basic autonomous exploration
  - Voice command system
  - ChatGPT integration
  - System monitoring
  - Web interface
