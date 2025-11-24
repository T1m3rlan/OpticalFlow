# Betafly Optical Position Stabilization

A complete optical flow-based position stabilization system for the Betafly drone, optimized for Raspberry Pi Zero.

## ✨ New Features

- **🌐 Web Interface**: Beautiful real-time dashboard for monitoring and configuration (port 8080)
- **📷 Multiple Camera Support**: Raspberry Pi CSI modules (IMX219/OV5647), USB webcams, and analog FPV cameras via capture cards
- **🎮 Manual Stick Inputs**: RC receiver integration with SBUS/PWM support and smooth blending
- **🔧 Live Configuration**: Edit PID gains and settings through web GUI
- **📊 Real-time Visualization**: Live position tracking and control output graphs

## Core Features

- **Camera-Based Optical Flow**: Dense flow from CSI/USB/analog cameras for precise motion tracking
- **Position Hold**: Maintains GPS-free position hold using visual odometry
- **Velocity Damping**: Reduces drift and oscillations during flight
- **PID Control**: Tunable PID controllers for X and Y axis stabilization
- **Multiple Modes**: Off, velocity damping, and position hold modes
- **Real-time Logging**: Optional CSV logging for flight data analysis
- **Lightweight**: Optimized for Raspberry Pi Zero's limited resources

## Hardware Requirements

### Required Components
- **Raspberry Pi Zero W/Zero 2 W** (Zero 2 W strongly recommended for OpenCV throughput)
- **Camera** (pick one):
  - **Raspberry Pi CSI Camera Module v2 (IMX219)** – best balance of FOV + low light
  - **Raspberry Pi CSI Camera Module v1 (OV5647)** – works great for indoor testing
  - **Analog FPV camera + USB capture stick** – reuses existing FPV hardware
  - **USB webcam** – quick bench testing option
- **Flight Controller** (Betaflight, iNav, ArduPilot, etc.)
- **5 V Power** (BEC or regulator capable of ≥1 A for the Pi and camera)

### Camera Wiring & Orientation

#### CSI Cameras (IMX219 / OV5647)
```
IMX219 / OV5647  === FFC Ribbon ===  Raspberry Pi Zero (CAM0)
┌──────────────┐                      ┌────────────────────┐
│  Camera PCB  │=====================>│  CAM0 connector     │
└──────────────┘                      └────────────────────┘

FFC orientation tips:
- Exposed contacts on the ribbon face the **HDMI** connector when inserting into CAM0.
- Fully open the CAM0 latch, slide the ribbon in straight, then press the latch back down.
- Secure the camera so the lens points straight down; avoid vibrations where possible.
```

| Camera Wire / Label | Pi Zero Connection | Notes |
|---------------------|--------------------|-------|
| 3V3 | Pin 1 (3V3) | Use only if powering custom camera boards—official CSI modules pull power from CAM0 automatically |
| GND | Pin 6 (GND) | Tie to frame or PDB ground |
| CSI Data/Clock | CAM0 FFC | Provided through the ribbon cable |

#### Analog FPV Cameras via USB Capture
```
Analog Camera ----> USB Capture Stick ----> Pi Zero (USB OTG)
       | Video (yellow)   | HDMI-to-USB or UVC capture
       | +5V              | Powered from BEC (share ground with Pi)
       | GND              | Common ground to Pi & flight controller
```
1. Power the analog camera from a regulated 5 V rail (same BEC as the Pi works fine).
2. Feed the video line into a UVC-compatible USB capture dongle (EasyCAP, Elgato CamLink, etc.).
3. Connect the capture dongle to the Pi Zero via a USB OTG cable and set `"camera.type": "analog_usb"` in `config.json`.
4. Leave `camera.deinterlace` enabled to clean up interlaced NTSC/PAL feeds.

### Raspberry Pi Zero ↔ Flight Controller (UART) Wiring

Use the Pi’s primary UART (`/dev/ttyAMA0`) to pass stabilization corrections to the flight controller. Keep the wiring short and twist TX/RX pairs when possible.

```
Pi Zero (Top View)                         Flight Controller UART
┌──────────────────────────────┐          ┌──────────────────────┐
│ Pin 8  (GPIO14 / TXD0)  ----┼─────────▶│ RX (UART n)           │
│ Pin 10 (GPIO15 / RXD0)  ◀---┼──────────│ TX (UART n)           │
│ Pin 6  (GND)             ----┴─────────│ GND                   │
└──────────────────────────────┘          └──────────────────────┘
```

| Pi Pin | Signal | Connects To | Notes |
|--------|--------|-------------|-------|
| Pin 8  (GPIO14) | TX (3.3 V) | Flight controller **RX** | Carries Betafly corrections. Level shifting not required for 3.3 V controllers; do **not** connect to 5 V UARTs. |
| Pin 10 (GPIO15) | RX (3.3 V) | Flight controller **TX** | Receives mode/status if you implement MAVLink/MSP responses. |
| Pin 6          | GND        | Flight controller GND     | Must share ground for UART to work reliably. |

After wiring:
1. Enable the serial interface for `/dev/ttyAMA0` (disable the Linux console on that port).
2. Set the desired protocol under `output.interface` in `config.json` (`mavlink`, `msp`, etc.).
3. Match baud rates on both the Pi and the flight controller (115200 bps by default).

## Software Installation

### 1. Prepare Raspberry Pi Zero

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip (if not already installed)
sudo apt-get install python3 python3-pip -y

# Enable camera + UART interfaces
sudo raspi-config
# Interface Options -> Camera -> Enable
# Interface Options -> Serial -> Disable login shell, enable hardware serial

# Optional: verify camera feed
libcamera-hello -t 3000
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

### 4. Test Camera Optical Flow

```bash
# Quick camera test (auto-detect CSI/USB camera)
python3 test_sensor.py --type csi_camera --device auto --duration 10
```

## Configuration

Edit `config.json` to customize the system for your setup:

### Key Parameters

```json
{
  "camera": {
    "type": "csi_camera",      // csi_camera, usb_camera, analog_usb, opencv_any
    "device": "auto",          // Camera index, /dev/video*, or "auto"
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback",     // or lucas_kanade
    "deinterlace": true        // leave enabled for analog feeds
  },
  "tracker": {
    "scale_factor": 0.001,     // Adjust when changing lenses/height
    "initial_height": 0.5      // Expected flight height in meters
  },
  "pid": {
    "position_x": { "kp": 0.5, "ki": 0.1, "kd": 0.2 },
    "position_y": { "kp": 0.5, "ki": 0.1, "kd": 0.2 }
  },
  "stabilizer": {
    "max_tilt_angle": 15.0,
    "velocity_damping": 0.3
  },
  "control": {
    "update_rate_hz": 50
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

- **CSI camera (IMX219 / OV5647)**: Leave `"camera.type": "csi_camera"` and `"device": "auto"`. The system auto-detects the first CSI pipeline.
- **USB webcam**: Set `"camera.type": "usb_camera"` and `"device": 0` (or `/dev/video1`). Keep `method: "farneback"` for best results indoors.
- **Analog FPV camera**: Set `"camera.type": "analog_usb"`, point `"device"` at the capture stick (usually `/dev/video0`), and leave `"deinterlace": true`.
- **OpenCV auto-detect**: Use `"camera.type": "opencv_any"` to scan `/dev/video*` devices automatically—handy for debugging tethered laptops.

After editing `config.json`, restart `betafly_stabilizer_advanced.py --config config.json`.

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

### Step 1: Verify Camera Optical Flow

1. Start system with logging enabled
2. Manually move the airframe and observe position tracking in the web UI
3. Ensure `surface_quality` stays above ~50 (increase lighting or texture if it drops)

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
- **Drifting away?** Confirm the camera is level, in focus, and that the tracker height matches reality

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

- Run `libcamera-hello -t 3000` (CSI) or `v4l2-ctl --list-devices` (USB) to make sure Linux sees the camera.
- Double-check the CSI ribbon orientation (contacts toward HDMI) and that the latch is fully closed.
- For USB/analog capture sticks, confirm the device shows up under `/dev/video*` and that `camera.device` matches.
- Ensure the `pi` user belongs to the `video` group: `sudo usermod -aG video pi` then reboot.

### Poor Tracking Quality

- Improve lighting or add textured landing pads; plain white floors are hard for optical flow.
- Refocus the camera and ensure the lens is clean.
- Raise the flight height (`tracker.initial_height`) if the field of view is too zoomed-in.
- For analog feeds, keep `camera.deinterlace` enabled and try reducing resolution to 640×480.

### Position Drift

- Confirm the camera is rigidly mounted and points straight down (no sweeping gimbal motion).
- Re-check `scale_factor` and `initial_height` after changing camera lenses or altitude.
- Increase velocity damping slightly and review flight logs for bias.

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
│ Camera Flow    │         │  Stabilization  │
│  + Tracking    │         │   Controller    │
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
- `motion_tracker.py` - Optical flow integration and position estimation utilities
- `camera_optical_flow.py` - Camera-based optical flow (USB/CSI/Analog)
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
- `test_sensor.py` - Camera optical flow testing utility

### Documentation
- `README.md` - This file
- `FEATURES.md` - **New!** Detailed guide for new features
- `INSTALL.md` - Installation guide
- `CAMERA_WIRING_GUIDE.md` - Camera + flight controller wiring cheatsheet

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
- Raspberry Pi CSI camera modules (IMX219/OV5647) and analog FPV feeds
- Raspberry Pi Zero platform
- PID control theory
- Visual odometry principles

---

**Happy Flying! 🚁**
