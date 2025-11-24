# Betafly Optical Position Stabilization

A complete optical flow-based position stabilization system for the Betafly drone, optimized for Raspberry Pi Zero.

## ✨ New Features

- **🌐 Web Interface**: Beautiful real-time dashboard for monitoring and configuration (port 8080)
- **📷 Multiple Camera Support**: PMW3901, USB cameras, CSI cameras, and analog FPV cameras
- **🎮 Manual Stick Inputs**: RC receiver integration with SBUS/PWM support and smooth blending
- **🔧 Live Configuration**: Edit PID gains and settings through web GUI
- **📊 Real-time Visualization**: Live position tracking and control output graphs

## Core Features

- **Optical Flow Sensing**: Multiple sensor options for precise motion tracking
- **Position Hold**: Maintains GPS-free position hold using visual odometry
- **Velocity Damping**: Reduces drift and oscillations during flight
- **PID Control**: Tunable PID controllers for X and Y axis stabilization
- **Multiple Modes**: Off, velocity damping, and position hold modes
- **Real-time Logging**: Optional CSV logging for flight data analysis
- **Lightweight**: Optimized for Raspberry Pi Zero's limited resources

## Hardware Requirements

### Required Components
- **Raspberry Pi Zero W** (or Zero 2 W for better performance)
- **Optical Flow Sensor** (choose one):
  - PMW3901 Optical Flow Sensor (SPI) - Pimoroni or similar
  - **Caddx Infra 256 (I2C)** - Recommended for production ⭐
  - USB/CSI/Analog Camera (for computer vision approach)
- **Flight Controller** (Betaflight, iNav, or ArduPilot compatible)
- **Power Supply** (5V for Pi, shared with drone battery via BEC)

### Wiring Diagrams

#### Option 1: PMW3901 (SPI)
```
PMW3901 Sensor -> Raspberry Pi Zero
-----------------------------------------
VCC (3.3V)     -> Pin 1 (3.3V)
GND            -> Pin 6 (GND)
MOSI           -> Pin 19 (GPIO 10 / MOSI)
MISO           -> Pin 21 (GPIO 9 / MISO)
SCLK           -> Pin 23 (GPIO 11 / SCLK)
CS             -> Pin 24 (GPIO 8 / CE0)
```

#### Option 2: Caddx Infra 256 (I2C) ⭐ Recommended
```
Caddx Infra 256 -> Raspberry Pi Zero
-----------------------------------------
VCC (3.3V)      -> Pin 1 (3.3V)
GND             -> Pin 6 (GND)
SDA             -> Pin 3 (GPIO 2 / I2C SDA)
SCL             -> Pin 5 (GPIO 3 / I2C SCL)
```

**Benefits of Caddx Infra 256:**
- ✅ Simpler wiring (4 wires vs 6)
- ✅ Infrared technology (better in varied lighting)
- ✅ Lower power consumption
- ✅ I2C interface (easier debugging)

**Important**: Ensure the sensor is mounted facing downward with adequate lighting for optical tracking.

## Software Installation

### 1. Prepare Raspberry Pi Zero

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip (if not already installed)
sudo apt-get install python3 python3-pip -y

# Enable SPI interface
sudo raspi-config
# Navigate to: Interface Options -> SPI -> Enable
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization
```

### 3. Install Dependencies

```bash
# Install Python packages
pip3 install -r requirements.txt

# Make main script executable
chmod +x betafly_stabilizer.py
```

### 4. Test Sensor Connection

```bash
# Quick sensor test
python3 -c "from optical_flow_sensor import PMW3901; s = PMW3901(); print('Sensor OK')"
```

## Configuration

Edit `config.json` to customize the system for your setup:

### Key Parameters

```json
{
  "sensor": {
    "rotation": 0,  // Adjust based on sensor mounting orientation
  },
  "tracker": {
    "initial_height": 0.5,  // Expected flight height in meters
  },
  "pid": {
    "position_x": {
      "kp": 0.5,  // Increase for more aggressive position correction
      "ki": 0.1,  // Increase to eliminate steady-state error
      "kd": 0.2   // Increase to reduce oscillations
    }
  },
  "stabilizer": {
    "max_tilt_angle": 15.0,  // Maximum tilt command in degrees
    "velocity_damping": 0.3  // Damping factor (0-1)
  },
  "control": {
    "update_rate_hz": 50  // Control loop frequency
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

### Basic Command Line Usage

```bash
# Start with velocity damping (reduces drift)
./betafly_stabilizer.py --mode velocity_damping

# Start advanced system with all features
./betafly_stabilizer_advanced.py --mode position_hold

# Use custom config file
./betafly_stabilizer_advanced.py --config my_config.json

# Enable data logging
./betafly_stabilizer_advanced.py --log --mode position_hold

# Disable web interface
./betafly_stabilizer_advanced.py --no-web
```

### Using Different Camera Types

```bash
# PMW3901 sensor (default)
./betafly_stabilizer_advanced.py

# USB camera
# Edit config.json: "sensor": {"type": "usb_camera"}
./betafly_stabilizer_advanced.py --config config.json

# Analog camera via USB capture card
# Edit config.json: "sensor": {"type": "analog_usb"}
./betafly_stabilizer_advanced.py --config config.json
```

### Command Line Options

```
-c, --config FILE       Configuration file (JSON)
-m, --mode MODE         Initial mode: off, velocity_damping, position_hold
-l, --log              Enable CSV data logging
-v, --verbose          Enable verbose logging
```

### Operating Modes

1. **Off**: No stabilization (pass-through)
2. **Velocity Damping**: Reduces drift by opposing velocity
3. **Position Hold**: Maintains position at the point where mode was activated

## Integration with Flight Controller

The system outputs pitch and roll correction angles that need to be sent to your flight controller.

### Option 1: MAVLink (Recommended)

For ArduPilot or PX4:
- Connect Pi serial to FC telemetry port
- Set `"interface": "mavlink"` in config
- System sends `SET_POSITION_TARGET_LOCAL_NED` messages

### Option 2: MSP Protocol

For Betaflight/iNav:
- Connect Pi serial to FC UART
- Set `"interface": "msp"` in config
- Implement MSP message handling in `_send_corrections()`

### Option 3: PWM Override

- Connect Pi GPIO to FC receiver inputs
- Set `"interface": "pwm"` in config
- Use pigpio library for PWM generation

## Tuning Guide

### Step 1: Verify Optical Flow

1. Start system with logging enabled
2. Manually move drone and observe position tracking
3. Ensure `surface_quality` (squal) stays above 50

### Step 2: Tune Velocity Damping

1. Start in velocity_damping mode
2. Adjust `velocity_damping` factor (0.1 to 0.5)
3. Higher values = more aggressive damping

### Step 3: Tune Position Hold

1. Start with conservative PID gains
2. Increase Kp until position holds with minimal error
3. Add Kd to reduce oscillations
4. Add small Ki to eliminate steady-state error

### Tuning Tips

- **Too oscillatory?** Decrease Kp, increase Kd
- **Too slow to respond?** Increase Kp
- **Steady-state error?** Increase Ki (but keep small!)
- **Drifting away?** Check sensor mounting and height setting

## Performance Optimization

### For Raspberry Pi Zero

The Pi Zero is single-core and slower, so:

1. **Reduce update rate**: Try 30-40 Hz instead of 50 Hz
2. **Disable logging**: Reduces CPU and SD card writes
3. **Use lightweight OS**: Raspberry Pi OS Lite (no desktop)
4. **Overclock safely**: Add to `/boot/config.txt`:
   ```
   arm_freq=1000
   over_voltage=2
   ```

### For Raspberry Pi Zero 2 W

The quad-core Zero 2 W can handle:
- 100 Hz update rate
- Real-time logging
- Additional sensor fusion (IMU integration)

## Data Analysis

Flight logs are saved as CSV files with columns:
- `time`: Time in seconds
- `pos_x`, `pos_y`: Position in meters
- `vel_x`, `vel_y`: Velocity in m/s
- `pitch_cmd`, `roll_cmd`: Control outputs in degrees
- `mode`: Current stabilization mode
- `squal`: Surface quality (0-255)

Analyze with Python:

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('flight_log.csv')
plt.plot(df['time'], df['pos_x'], label='X position')
plt.plot(df['time'], df['pos_y'], label='Y position')
plt.legend()
plt.show()
```

## Troubleshooting

### Sensor Not Detected

- Verify SPI is enabled: `lsmod | grep spi`
- Check wiring connections
- Test with `spidev` directly

### Poor Tracking Quality

- Ensure adequate lighting (avoid direct sunlight)
- Check sensor is clean and unobstructed
- Verify height setting matches actual height
- Ensure surface below has visible texture (not blank/uniform)

### Position Drift

- Verify sensor rotation setting matches physical mounting
- Check for vibrations (dampen sensor mounting)
- Increase velocity damping factor
- Ensure height is set correctly (scales optical flow)

### Control Loop Running Slow

- Reduce update rate in config
- Disable data logging
- Close unnecessary processes
- Consider Pi Zero 2 W for better performance

## System Architecture

```
┌─────────────────────────────────────────────────┐
│          Betafly Stabilization System           │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐         ┌────────▼────────┐
│ Optical Flow   │         │  Stabilization  │
│    Tracking    │         │   Controller    │
│                │         │                 │
│ - PMW3901      │────────▶│ - Position PID  │
│ - Position Est │         │ - Velocity Damp │
│ - Velocity Est │         │ - Mode Control  │
└────────────────┘         └─────────┬───────┘
                                     │
                            ┌────────▼────────┐
                            │ Flight Control  │
                            │   Interface     │
                            │                 │
                            │ - MAVLink / MSP │
                            │ - PWM Output    │
                            └─────────────────┘
```

## API Reference

### OpticalFlowTracker

```python
tracker = OpticalFlowTracker(sensor, scale_factor=0.001, height_m=0.5)
pos_x, pos_y = tracker.update()  # Get current position
vel_x, vel_y = tracker.get_velocity()  # Get velocity
tracker.reset_position()  # Reset to origin
tracker.set_height(new_height)  # Update height
```

### PositionStabilizer

```python
stabilizer = PositionStabilizer(x_gains, y_gains, max_tilt_angle=15.0)
stabilizer.set_target_position(x, y)  # Set target
stabilizer.enable()  # Enable position hold
pitch, roll = stabilizer.update(current_x, current_y)  # Get corrections
```

### StabilizationController

```python
controller = StabilizationController(gains_x, gains_y, damping, max_tilt)
controller.set_mode("position_hold")  # Set mode
pitch, roll = controller.update(x, y, vx, vy)  # Update control
controller.hold_current_position(x, y)  # Hold at position
```

## New Features Documentation

For detailed information about new features:
- **[FEATURES.md](FEATURES.md)** - Complete guide to web interface, camera support, and stick inputs
- **[INSTALL.md](INSTALL.md)** - Installation and setup instructions

## Project Files

### Core System
- `betafly_stabilizer.py` - Original basic control script
- `betafly_stabilizer_advanced.py` - **New!** Advanced system with all features
- `optical_flow_sensor.py` - PMW3901 sensor interface
- `camera_optical_flow.py` - **New!** Camera-based optical flow (USB/CSI/Analog)
- `position_stabilizer.py` - PID control and stabilization algorithms
- `stick_input.py` - **New!** RC receiver input handling (SBUS/PWM)
- `web_interface.py` - **New!** Flask web server and API

### Web Interface
- `templates/index.html` - Web dashboard UI
- `static/css/style.css` - Styling
- `static/js/app.js` - Frontend JavaScript

### Configuration & Setup
- `config.json` - **Updated!** Configuration file with camera and stick input options
- `setup.sh` - Automated setup script
- `requirements.txt` - **Updated!** Python dependencies (includes OpenCV, Flask)

### Testing & Utilities
- `test_sensor.py` - Sensor testing utility

### Documentation
- `README.md` - This file
- `FEATURES.md` - **New!** Detailed guide for new features
- `INSTALL.md` - Installation guide

## Contributing

Contributions welcome! Areas for improvement:
- Flight controller integration implementations
- Additional sensor support (VL53L0X for height)
- Kalman filter for sensor fusion
- Auto-tuning algorithms
- Ground effect compensation
- Additional web interface features
- Mobile app development

## License

MIT License - See LICENSE file for details

## Safety Warning

⚠️ **IMPORTANT**: This system is experimental. Always:
- Test in a safe environment
- Have manual control override ready
- Start with low gains and gentle movements
- Monitor battery voltage (Pi can brownout)
- Never fly over people or property

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/yourusername/betafly-stabilization/issues
- Documentation: https://github.com/yourusername/betafly-stabilization/wiki

## Credits

Developed for the Betafly drone project using:
- PMW3901 optical flow sensor
- Raspberry Pi Zero platform
- PID control theory
- Visual odometry principles

---

**Happy Flying! 🚁**
