# Betafly Camera-Based Position Stabilization

A complete camera-based position stabilization system for the Betafly drone, optimized for Raspberry Pi Zero. Uses computer vision optical flow from Raspberry Pi cameras or analog cameras for GPS-free position hold.

## ✨ Features

- **🌐 Web Interface**: Beautiful real-time dashboard for monitoring and configuration (port 8080)
- **📷 Multiple Camera Support**: Raspberry Pi Camera Module (IMX219, OV5647), USB cameras, and analog FPV cameras
- **🎮 Manual Stick Inputs**: RC receiver integration with SBUS/PWM support and smooth blending
- **🔧 Live Configuration**: Edit PID gains and settings through web GUI
- **📊 Real-time Visualization**: Live position tracking and control output graphs

## Core Features

- **Camera-Based Optical Flow**: Computer vision motion tracking using cameras
- **Position Hold**: Maintains GPS-free position hold using visual odometry
- **Velocity Damping**: Reduces drift and oscillations during flight
- **PID Control**: Tunable PID controllers for X and Y axis stabilization
- **Multiple Modes**: Off, velocity damping, and position hold modes
- **Real-time Logging**: Optional CSV logging for flight data analysis
- **Lightweight**: Optimized for Raspberry Pi Zero's limited resources

## Hardware Requirements

### Required Components
- **Raspberry Pi Zero W** (or Zero 2 W for better performance)
- **Camera** (choose one):
  - **Raspberry Pi Camera Module v2** (IMX219) - Recommended ⭐
  - **Raspberry Pi Camera Module v1** (OV5647)
  - USB webcam
  - Analog FPV camera with USB capture card
- **Flight Controller** (Betaflight, iNav, or ArduPilot compatible)
- **Power Supply** (5V for Pi, shared with drone battery via BEC)

### Camera Wiring Diagrams

#### Option 1: Raspberry Pi Camera Module v2 (IMX219) ⭐ Recommended

The Raspberry Pi Camera Module v2 uses the CSI (Camera Serial Interface) connector on the Raspberry Pi Zero.

```
Raspberry Pi Camera Module v2 (IMX219) -> Raspberry Pi Zero
------------------------------------------------------------
CSI Connector (15-pin ribbon cable)     -> CSI Port on Pi Zero
```

**Physical Connection:**
1. Locate the CSI connector on Raspberry Pi Zero (between HDMI and audio jack)
2. Lift the black plastic tab on the CSI connector
3. Insert the camera ribbon cable with the contacts facing away from the Ethernet port
4. Push the black tab down to lock the cable in place

**Pinout (for reference):**
```
Camera Module CSI Connector (15-pin):
Pin 1  (GND)      -> Ground
Pin 2  (CAM_IO1)  -> Camera I/O 1
Pin 3  (CAM_IO0)  -> Camera I/O 0
Pin 4  (GND)      -> Ground
Pin 5  (CAM_CLK)  -> Camera Clock
Pin 6  (GND)      -> Ground
Pin 7  (CAM_D1)   -> Camera Data 1
Pin 8  (CAM_D0)   -> Camera Data 0
Pin 9  (GND)      -> Ground
Pin 10 (CAM_D3)   -> Camera Data 3
Pin 11 (CAM_D2)   -> Camera Data 2
Pin 12 (GND)      -> Ground
Pin 13 (CAM_D5)   -> Camera Data 5
Pin 14 (CAM_D4)   -> Camera Data 4
Pin 15 (GND)      -> Ground
```

**Note**: The ribbon cable handles all connections automatically. No manual wiring needed!

#### Option 2: Raspberry Pi Camera Module v1 (OV5647)

The original Raspberry Pi Camera Module uses the same CSI connector:

```
Raspberry Pi Camera Module v1 (OV5647) -> Raspberry Pi Zero
-------------------------------------------------------------
CSI Connector (15-pin ribbon cable)      -> CSI Port on Pi Zero
```

**Connection Steps:**
1. Same as Camera Module v2 - use CSI connector
2. Ensure ribbon cable is inserted correctly (contacts facing away from Ethernet port)
3. Lock the connector tab

#### Option 3: Analog Camera with USB Capture Card

For analog FPV cameras (NTSC/PAL):

```
Analog FPV Camera -> USB Video Capture Card -> Raspberry Pi Zero USB Port
```

**Wiring:**
```
Analog Camera:
Video Out (Yellow RCA) -> USB Capture Card Video In
GND                    -> USB Capture Card GND
Power (5V/12V)         -> Camera power supply (separate)
```

**USB Capture Card Connection:**
- Connect USB capture card to Raspberry Pi Zero USB port (use USB OTG adapter if needed)
- Camera appears as `/dev/video0` or `/dev/video1`

**Recommended USB Capture Cards:**
- EasyCap DC60
- Elgato Cam Link 4K (high quality)
- Generic USB video capture dongles

#### Option 4: USB Webcam

Standard USB webcams connect directly:

```
USB Webcam -> Raspberry Pi Zero USB Port
```

**Connection:**
- Plug USB webcam into USB port
- Use USB OTG adapter if needed for Pi Zero
- Camera appears as `/dev/video0`

### Raspberry Pi Zero to Flight Controller Wiring

Connect Raspberry Pi Zero to your flight controller using the UART serial interface (TX/RX pads).

#### Wiring Diagram

```
Raspberry Pi Zero          Flight Controller
------------------         -----------------
GPIO 14 (TXD)      ------>  RX Pad (UART RX)
GPIO 15 (RXD)      <------  TX Pad (UART TX)
GND                -------  GND (Ground)
```

**Physical Pin Locations on Raspberry Pi Zero:**

```
Raspberry Pi Zero GPIO Header (40-pin):
Pin 8  (GPIO 14 / TXD)  -> Flight Controller RX
Pin 10 (GPIO 15 / RXD)  -> Flight Controller TX
Pin 6  (GND)            -> Flight Controller GND
```

**Visual Pinout:**
```
    3.3V  [1]  [2]  5V
   GPIO2  [3]  [4]  5V
   GPIO3  [5]  [6]  GND  <-- Connect FC GND here
   GPIO4  [7]  [8]  GPIO14 (TXD) <-- Connect to FC RX
     GND  [9]  [10] GPIO15 (RXD) <-- Connect to FC TX
  GPIO17 [11] [12] GPIO18
  GPIO27 [13] [14] GND
  GPIO22 [15] [16] GPIO23
    3.3V [17] [18] GPIO24
  GPIO10 [19] [20] GND
   GPIO9 [21] [22] GPIO25
  GPIO11 [23] [24] GPIO8
     GND [25] [26] GPIO7
   GPIO0 [27] [28] GPIO1
   GPIO5 [29] [30] GND
   GPIO6 [31] [32] GPIO12
  GPIO13 [33] [34] GND
  GPIO19 [35] [36] GPIO16
  GPIO26 [37] [38] GPIO20
     GND [39] [40] GPIO21
```

**Flight Controller Connection:**

Most flight controllers have labeled UART pads. Common locations:

1. **Betaflight/iNav FCs**: Look for UART pads labeled:
   - `TX` or `UART TX` - Connect to Pi GPIO 15 (RXD)
   - `RX` or `UART RX` - Connect to Pi GPIO 14 (TXD)
   - `GND` - Connect to Pi GND

2. **ArduPilot FCs**: Usually have multiple UARTs:
   - Use any available UART (e.g., TELEM1, TELEM2)
   - Connect TX/RX/GND pads

**Important Notes:**
- ⚠️ **Voltage Levels**: Most flight controllers use 3.3V logic levels, which matches Raspberry Pi Zero GPIO (3.3V). Do NOT connect to 5V UARTs without level shifter!
- ⚠️ **Cross Connection**: Pi TX connects to FC RX, Pi RX connects to FC TX (crossed)
- ⚠️ **Ground Connection**: Always connect GND for proper signal reference
- ⚠️ **Baud Rate**: Configure both Pi and FC to same baud rate (typically 115200)

**Serial Port Configuration:**

Enable serial port on Raspberry Pi:

```bash
sudo raspi-config
# Navigate to: Interface Options -> Serial Port
# - Login shell over serial: NO
# - Serial port hardware: YES
```

The serial port will be available at `/dev/ttyAMA0` (GPIO 14/15).

**Testing Connection:**

```bash
# On Raspberry Pi, test serial output
echo "test" > /dev/ttyAMA0

# Monitor serial input
cat /dev/ttyAMA0
```

**Important**: Ensure camera is mounted facing downward with clear view of ground surface for optical tracking.

## Software Installation

### 1. Prepare Raspberry Pi Zero

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip (if not already installed)
sudo apt-get install python3 python3-pip -y

# Enable Camera Interface (for CSI cameras)
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable

# Enable Serial Port (for FC communication)
sudo raspi-config
# Navigate to: Interface Options -> Serial Port
# - Login shell over serial: NO
# - Serial port hardware: YES
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

# Install additional camera dependencies
sudo apt-get install -y python3-opencv v4l-utils

# Make main script executable
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py
```

### 4. Test Camera Connection

**For CSI Camera (Raspberry Pi Camera Module):**
```bash
# Test camera capture
raspistill -o test.jpg

# Or using libcamera (Raspberry Pi OS Bullseye+)
libcamera-still -o test.jpg
```

**For USB Camera:**
```bash
# List available video devices
ls /dev/video*

# Test camera with OpenCV
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK:', cap.isOpened()); cap.release()"
```

## Configuration

Edit `config.json` to customize the system for your setup:

### Key Parameters

```json
{
  "camera": {
    "type": "csi_camera",  // or "usb_camera", "analog_usb"
    "device": 0,  // Camera device ID or "auto"
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback"  // or "lucas_kanade"
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
  },
  "output": {
    "interface": "mavlink",  // or "msp"
    "port": "/dev/ttyAMA0",  // Serial port for FC communication
    "baudrate": 115200
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
# Raspberry Pi Camera Module (CSI) - default
# Edit config.json: "camera": {"type": "csi_camera"}
./betafly_stabilizer_advanced.py --config config.json

# USB camera
# Edit config.json: "camera": {"type": "usb_camera"}
./betafly_stabilizer_advanced.py --config config.json

# Analog camera via USB capture card
# Edit config.json: "camera": {"type": "analog_usb"}
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

The system outputs pitch and roll correction angles that need to be sent to your flight controller via serial connection.

### Serial Connection Setup

**Hardware Wiring:**
- Raspberry Pi Zero GPIO 14 (TXD) → Flight Controller RX pad
- Raspberry Pi Zero GPIO 15 (RXD) → Flight Controller TX pad  
- Raspberry Pi Zero GND → Flight Controller GND

**Software Configuration:**

### Option 1: MAVLink (Recommended for ArduPilot/PX4)

For ArduPilot or PX4:
- Connect Pi serial to FC telemetry port (UART)
- Set `"interface": "mavlink"` in config.json
- Set `"port": "/dev/ttyAMA0"` and `"baudrate": 115200`
- System sends `SET_POSITION_TARGET_LOCAL_NED` messages

**Flight Controller Setup:**
- Configure telemetry port for MAVLink at 115200 baud
- Enable position hold mode support

### Option 2: MSP Protocol (For Betaflight/iNav)

For Betaflight/iNav:
- Connect Pi serial to FC UART
- Set `"interface": "msp"` in config.json
- Set `"port": "/dev/ttyAMA0"` and `"baudrate": 115200`
- Implement MSP message handling in `_send_corrections()`

**Flight Controller Setup:**
- Configure UART for MSP at 115200 baud
- Enable MSP on selected UART port

### Option 3: PWM Override (Advanced)

- Connect Pi GPIO pins to FC receiver inputs
- Set `"interface": "pwm"` in config
- Use pigpio library for PWM generation
- Requires additional hardware connections

## Tuning Guide

### Step 1: Verify Camera Optical Flow

1. Start system with logging enabled
2. Manually move drone and observe position tracking
3. Ensure `surface_quality` stays above 50
4. Check camera view has adequate texture/features

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
- **Drifting away?** Check camera mounting, height setting, and lighting
- **Poor tracking?** Ensure ground has visible texture, adequate lighting

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

### Camera Not Detected

**CSI Camera:**
- Verify camera is enabled: `sudo raspi-config` → Interface Options → Camera
- Check ribbon cable connection (contacts facing away from Ethernet port)
- Test with: `raspistill -o test.jpg` or `libcamera-still -o test.jpg`
- Ensure camera is compatible (IMX219 or OV5647)

**USB Camera:**
- List devices: `ls /dev/video*`
- Check USB connection and power
- Test with: `python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`
- Try different USB port or USB OTG adapter

### Poor Tracking Quality

- Ensure adequate lighting (avoid direct sunlight)
- Check camera lens is clean and unobstructed
- Verify height setting matches actual height
- Ensure surface below has visible texture (not blank/uniform)
- Try different optical flow method (farneback vs lucas_kanade)
- Reduce resolution if CPU is overloaded

### Position Drift

- Check for vibrations (dampen camera mounting)
- Increase velocity damping factor
- Ensure height is set correctly (scales optical flow)
- Verify camera is mounted facing downward
- Check ground surface has sufficient texture

### Serial Communication Issues

- Verify wiring: Pi TX → FC RX, Pi RX → FC TX, GND → GND
- Check serial port enabled: `sudo raspi-config` → Serial Port
- Verify baud rate matches (115200)
- Test serial port: `echo "test" > /dev/ttyAMA0`
- Check voltage levels (3.3V, not 5V)

### Control Loop Running Slow

- Reduce camera resolution (e.g., 320x240)
- Use lucas_kanade method instead of farneback
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
│ Camera Optical │         │  Stabilization  │
│    Flow        │         │   Controller    │
│                │         │                 │
│ - CSI/USB/Analog│────────▶│ - Position PID  │
│ - Position Est │         │ - Velocity Damp │
│ - Velocity Est │         │ - Mode Control  │
└────────────────┘         └─────────┬───────┘
                                     │
                            ┌────────▼────────┐
                            │ Flight Control  │
                            │   Interface     │
                            │                 │
                            │ - MAVLink / MSP │
                            │ - Serial (TX/RX)│
                            └─────────────────┘
```

## API Reference

### CameraFlowTracker

```python
from camera_optical_flow import CameraOpticalFlow, CameraFlowTracker

camera = CameraOpticalFlow(camera_id=0, width=640, height=480)
camera.start()
tracker = CameraFlowTracker(camera, scale_factor=0.001, height_m=0.5)
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
- `betafly_stabilizer.py` - Basic control script
- `betafly_stabilizer_advanced.py` - Advanced system with all features
- `camera_optical_flow.py` - Camera-based optical flow (CSI/USB/Analog)
- `position_stabilizer.py` - PID control and stabilization algorithms
- `stick_input.py` - RC receiver input handling (SBUS/PWM)
- `web_interface.py` - Flask web server and API

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
- Flight controller integration implementations (MAVLink/MSP)
- Additional camera support
- Kalman filter for sensor fusion
- Auto-tuning algorithms
- Ground effect compensation
- Additional web interface features
- Mobile app development
- Height sensor integration (VL53L0X)

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
- Raspberry Pi Camera Modules (IMX219, OV5647)
- Raspberry Pi Zero platform
- PID control theory
- Computer vision optical flow algorithms
- Visual odometry principles

---

**Happy Flying! 🚁**
