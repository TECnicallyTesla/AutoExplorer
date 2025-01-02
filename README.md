# PiCar-X Robot

An intelligent autonomous robot system built for the PiCar-X platform, featuring grid-based mapping, voice command capabilities, and ChatGPT integration.

## Features

- Grid-based environment mapping and navigation
- Voice command control
- Real-time system monitoring (CPU, temperature, battery)
- ChatGPT integration for intelligent responses
- Computer vision capabilities

## Setup

1. Clone the repository:
```bash
git clone [your-repo-url]
cd picar-x-robot
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
picar_x_robot/
  ├─ modules/           # Core functionality modules
  │   ├─ sensor_module.py
  │   ├─ navigation_module.py
  │   ├─ chatgpt_integration.py
  │   ├─ voice_command_handler.py
  │   ├─ system_monitor.py
  │   └─ mapping_module.py
  ├─ tests/            # Test files
  ├─ main.py          # Main application entry point
  ├─ requirements.txt  # Project dependencies
  └─ README.md        # This file
```

## Usage

[Usage instructions will be added as features are implemented]

## Dependencies

- Python 3.x
- See `requirements.txt` for complete list of dependencies

## License

[Add your chosen license]

## Contributing

[Add contribution guidelines if applicable]
