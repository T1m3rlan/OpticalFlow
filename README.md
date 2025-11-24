# Betafly Optical Position Stabilization

A complete optical flow-based position stabilization system for the Betafly drone, optimized for Raspberry Pi Zero using camera-based optical flow.

## ✨ Key Features

- **🌐 Web Interface**: Beautiful real-time dashboard for monitoring and configuration (port 8080)
- **📷 Camera Support**: Supports Raspberry Pi Cameras (CSI), USB cameras, and Analog cameras (via capture card)
- **🎮 Manual Stick Inputs**: RC receiver integration with SBUS/PWM support and smooth blending
- **🔧 Live Configuration**: Edit PID gains and settings through web GUI
- **📊 Real-time Visualization**: Live position tracking and control output graphs

## Core Features

- **Optical Flow Sensing**: Uses camera visual odometry for precise motion tracking
- **Position Hold**: Maintains GPS-free position hold
- **Velocity Damping**: Reduces drift and oscillations during flight
- **PID Control**: Tunable PID controllers for X and Y axis stabilization
- **Multiple Modes**: Off, velocity damping, and position hold modes
- **Real-time Logging**: Optional CSV logging for flight data analysis
- **Lightweight**: Optimized for Raspberry Pi Zero's limited resources

## Hardware Requirements

### Required Components
- **Raspberry Pi Zero W** (or Zero 2 W for better performance)
- **Camera** (choose one):
  - Raspberry Pi Camera (V1, V2, or ZeroCam) with CSI cable
  - USB Webcam
  - Analog FPV Camera + USB Capture Card
- **Flight Controller** (Betaflight, iNav, or ArduPilot compatible)
- **Power Supply** (5V for Pi, shared with drone battery via BEC)

### Wiring & Setup
See [CAMERA_SETUP.md](CAMERA_SETUP.md) for detailed camera wiring and flight controller connection diagrams.

## Software Installation

### 1. Prepare Raspberry Pi Zero

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip (if not already installed)
sudo apt-get install python3 python3-pip git libopencv-dev python3-opencv -y

# Enable Camera
# Run raspi-config and enable Legacy Camera or Camera interface
sudo raspi-config
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization
```

### 3. Install Dependencies

```bash
# Run automated setup script
./setup.sh
```

### 4. Test Camera Connection

```bash
# Run advanced script with verbose logging to check camera
./betafly_stabilizer_advanced.py --verbose
```

## Configuration

Edit `config.json` to customize the system for your setup:

### Key Parameters

```json
{
  "camera": {
    "device": "auto", // "auto", 0, 1, or path "/dev/video0"
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback" // "farneback" (dense) or "lucas_kanade" (sparse)
  },
  "tracker": {
    "initial_height": 0.5  // Expected flight height in meters
  },
  "pid": {
    "position_x": {
      "kp": 0.5,
      "ki": 0.1,
      "kd": 0.2
    }
  },
  "stabilizer": {
    "max_tilt_angle": 15.0,
    "velocity_damping": 0.3
  }
}
```

## Usage

### Quick Start with Web Interface

```bash
# Start advanced system with web interface (recommended)
./betafly_stabilizer_advanced.py

# Access web interface at:
# http://raspberrypi.local:8080
```

The web interface provides:
- Real-time position and velocity display
- Live control output visualization
- Configuration editor
- Mode switching controls
- Stick input monitoring

### Command Line Usage

```bash
# Start with velocity damping (reduces drift)
./betafly_stabilizer.py --mode velocity_damping

# Start advanced system with all features
./betafly_stabilizer_advanced.py --mode position_hold

# Analog camera usage
# Edit config.json to use "analog_usb" or pass via command line arguments if implemented
```

### Command Line Options

```
-c, --config FILE       Configuration file (JSON)
-m, --mode MODE         Initial mode: off, velocity_damping, position_hold
-l, --log              Enable CSV data logging
-v, --verbose          Enable verbose logging
--no-web               Disable web interface (advanced script only)
```

## Integration with Flight Controller

The system outputs pitch and roll correction angles that need to be sent to your flight controller.
See [CAMERA_SETUP.md](CAMERA_SETUP.md) for wiring details.

## Project Files

### Core System
- `betafly_stabilizer.py` - Basic control script (Camera-based)
- `betafly_stabilizer_advanced.py` - Advanced system with web/stick support
- `optical_flow_sensor.py` - Generic optical flow tracker logic
- `camera_optical_flow.py` - Camera-based optical flow implementation
- `position_stabilizer.py` - PID control and stabilization algorithms
- `stick_input.py` - RC receiver input handling (SBUS/PWM)
- `web_interface.py` - Flask web server and API

### Documentation
- `README.md` - This file
- `CAMERA_SETUP.md` - Camera and wiring guide
- `FEATURES.md` - Detailed guide for features
- `INSTALL.md` - Installation guide

## Contributing

Contributions welcome!

## License

MIT License - See LICENSE file for details

## Safety Warning

⚠️ **IMPORTANT**: This system is experimental. Always:
- Test in a safe environment
- Have manual control override ready
- Start with low gains and gentle movements
- Monitor battery voltage (Pi can brownout)
- Never fly over people or property

## Credits

Developed for the Betafly drone project.
