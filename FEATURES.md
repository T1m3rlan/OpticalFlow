# New Features Guide

## Web Interface

### Overview
The Betafly system now includes a beautiful web-based GUI for real-time monitoring and configuration.

### Starting the Web Interface

```bash
# Start the advanced stabilizer with web interface (default)
./betafly_stabilizer_advanced.py

# Web interface will be available at:
# http://raspberrypi.local:8080
# or
# http://192.168.1.XXX:8080
```

### Features

#### 1. **Real-time Dashboard**
- Live position tracking with 2D visualization
- Velocity display
- Surface quality indicator
- System status and mode

#### 2. **Control Panel**
- One-click mode switching
- Height adjustment slider
- Position reset button
- Real-time control output visualization

#### 3. **Configuration Editor**
- **Camera Tab**: Select camera type (CSI/USB/analog), device path, resolution, optical flow method, and scale factor
- **PID Tuning Tab**: Adjust PID gains for both axes
- **Control Tab**: Update rate, max tilt, velocity damping

#### 4. **Manual Stick Inputs Display**
- Real-time RC stick position visualization
- Shows pitch, roll, throttle, yaw inputs
- Helps verify RC receiver connection

### Accessing from Different Devices

```bash
# From your computer on same network:
http://192.168.1.100:8080  # Replace with Pi's IP

# From smartphone:
http://raspberrypi.local:8080

# To find your Pi's IP:
hostname -I
```

### Configuration via Web
1. Navigate to Configuration card
2. Select appropriate tab (Sensor/PID/Control/Camera)
3. Modify values
4. Click "Save Configuration"
5. Restart system to apply changes

---

## Camera Input Options

### Supported camera transports
- **CSI cameras** – Raspberry Pi Camera Module v1 (OV5647) & v2 (IMX219)
- **USB webcams** – Any UVC-compliant webcam
- **Analog FPV cameras** – Via UVC capture sticks
- **OpenCV auto-detect** – Scans `/dev/video*` for the first working device

All camera types share the same `camera` block inside `config.json`:

```json
{
  "camera": {
    "type": "csi_camera",
    "device": "auto",
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback",
    "deinterlace": true
  }
}
```

#### CSI Cameras (IMX219 / OV5647)
- Set `"camera.type": "csi_camera"` and `"device": "auto"`.
- Enable the camera interface via `sudo raspi-config`.
- Use `libcamera-hello -t 3000` to confirm the stream.

#### USB Webcams
- Set `"camera.type": "usb_camera"`.
- Assign `"device": 0` or `/dev/video1` depending on your system.
- Works best with Farneback flow at 640×480; drop to 320×240 for Pi Zero.

#### Analog FPV Cameras
```
Analog Camera -> UVC Capture Stick -> Pi Zero USB OTG port
```
- Set `"camera.type": "analog_usb"` and `"device": "/dev/video0"`.
- Keep `"deinterlace": true` to clean up interlaced NTSC/PAL feeds.
- Recommended capture dongles: EasyCAP DC60, Elgato CamLink, generic UVC sticks.

#### OpenCV Auto-Detect
- Set `"camera.type": "opencv_any"` and `"device": "auto"`.
- The system will probe `/dev/video0-4` until it finds a working feed.

### Testing a Camera

```bash
# List video devices
ls /dev/video*

# Smoke-test with OpenCV
python3 - <<'EOF'
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
print("Camera OK:", ok, "Shape:", frame.shape if ok else None)
cap.release()
EOF
```

### Optical Flow Methods

Two methods available:

**Farneback (Recommended for analog)**
- Dense optical flow
- Better for textured scenes
- More robust to noise
- Slower but more accurate

**Lucas-Kanade**
- Sparse optical flow (tracks features)
- Faster computation
- Better for high-contrast scenes
- Good for Pi Zero

```json
{
  "camera": {
    "method": "farneback"  // or "lucas_kanade"
  }
}
```

### Performance Tips

**For Raspberry Pi Zero:**
- Use 320×240 resolution
- Prefer `lucas_kanade` method for lighter CPU usage
- Reduce control update rate to 30 Hz

```json
{
  "camera": {
    "width": 320,
    "height": 240,
    "fps": 30,
    "method": "lucas_kanade"
  },
  "control": {
    "update_rate_hz": 30
  }
}
```

**For Raspberry Pi Zero 2 W / Pi 4:**
- 640×480 with Farneback at 50 Hz works well
- Leave `fps` at 30 for thermal headroom

---

## Manual Stick Inputs

### Overview
Allows pilot to manually control the drone while position stabilization is active. System blends manual stick inputs with stabilization corrections.

### Features
- **Manual Override**: Stick inputs override position hold
- **Smooth Blending**: Configurable mix between manual and stabilization
- **Mode Switching**: Use RC switch to change modes
- **Failsafe**: Reverts to stabilization-only if RC signal lost

### Supported Protocols

#### 1. SBUS (Recommended)
```json
{
  "stick_input": {
    "enabled": true,
    "protocol": "sbus",
    "device": "/dev/ttyAMA0",
    "channels": 16
  }
}
```

**Wiring:**
```
FrSky Receiver SBUS -> Pi GPIO 15 (RXD) + Ground
```

**Setup:**
```bash
# Disable serial console
sudo raspi-config
# Interface Options -> Serial Port
# - Login shell over serial: NO
# - Serial port hardware: YES
```

#### 2. PWM (Individual Channels)
```json
{
  "stick_input": {
    "enabled": true,
    "protocol": "pwm",
    "channels": 6
  }
}
```

**Wiring:**
Connect each RC channel to GPIO pin:
- CH1 (Roll): GPIO 17
- CH2 (Pitch): GPIO 18
- CH3 (Throttle): GPIO 22
- CH4 (Yaw): GPIO 23
- CH5 (AUX1): GPIO 24
- CH6 (AUX2): GPIO 25

#### 3. Mock (Testing)
```json
{
  "stick_input": {
    "enabled": true,
    "protocol": "mock"
  }
}
```

Generates simulated stick inputs for testing without RC hardware.

### Configuration

#### Mix Ratio
Controls how much manual input overrides stabilization:

```json
{
  "stick_input": {
    "mix_ratio": 0.5
  }
}
```

- `0.0`: Full stabilization, no manual control
- `0.5`: Blend 50/50 (default)
- `1.0`: Full manual control

**Behavior:**
- When sticks centered → Full stabilization
- When sticks moved → Blend in manual control
- Amount of blend based on stick deflection and mix_ratio

#### Mode Channel
Use RC switch to change stabilization modes:

```json
{
  "stick_input": {
    "mode_channel": 4
  }
}
```

**Switch Positions (3-position switch):**
- Position 0 (Down): Off
- Position 1 (Middle): Velocity Damping
- Position 2 (Up): Position Hold

### Usage Example

1. **Configure RC Input:**
```bash
nano config.json
# Set stick_input.enabled = true
# Set protocol and device
```

2. **Start System:**
```bash
./betafly_stabilizer_advanced.py --config config.json
```

3. **Flying:**
   - Switch to "Velocity Damping" mode
   - Take off manually
   - Switch to "Position Hold"
   - Drone maintains position
   - Move sticks to override and reposition
   - Release sticks to hold new position

### Stick Deadzone
Built-in 5% deadzone prevents drift when sticks are centered.

### Failsafe
If RC signal lost for >1 second:
- Switches to stabilization-only mode
- Ignores last stick positions
- Maintains current position hold
- Logs warning message

---

## Quick Start with New Features

### 1. Basic Web Interface Test
```bash
# Start with web interface and mock stick input
./betafly_stabilizer_advanced.py --config config.json

# Open browser to http://raspberrypi.local:8080
# Monitor real-time data
# Change settings via GUI
```

### 2. USB Camera Setup
```bash
# Edit config
nano config.json
# Set camera.type = "usb_camera" and camera.device = 0

# Start system
./betafly_stabilizer_advanced.py --config config.json
```

### 3. Full Manual Control Setup
```bash
# Edit config
nano config.json
# Enable stick_input
# Set protocol to "sbus" or "pwm"

# Start system
./betafly_stabilizer_advanced.py --config config.json --log

# Check web interface to see stick inputs
```

---

## Troubleshooting

### Web Interface Won't Load
```bash
# Check if port is already in use
sudo netstat -tulpn | grep 8080

# Try different port
# Edit config.json: "web_interface": {"port": 8081}
```

### Camera Not Detected
```bash
# List video devices
v4l2-ctl --list-devices

# Test camera
python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"

# Install v4l-utils if needed
sudo apt-get install v4l-utils
```

### SBUS Not Working
```bash
# Check serial port
ls -l /dev/ttyAMA0

# Check serial config
sudo raspi-config
# Ensure serial hardware enabled, console disabled

# Test serial data
sudo cat /dev/ttyAMA0  # Should see garbage if SBUS working
```

### High CPU Usage
```bash
# Reduce resolution
# "camera": {"width": 320, "height": 240}

# Reduce update rate
# "control": {"update_rate_hz": 30}

# Use lighter optical flow method
# "camera": {"method": "lucas_kanade"}
```

---

## Performance Comparison

| Feature | Pi Zero | Pi Zero 2 W | Pi 4 |
|---------|---------|-------------|------|
| CSI 320×240 (Lucas-Kanade) | 40 Hz ✓ | 80 Hz ✓ | 100 Hz ✓ |
| CSI 640×480 (Farneback) | 20 Hz ⚠️ | 50 Hz ✓ | 100 Hz ✓ |
| USB 320×240 | 30 Hz ✓ | 60 Hz ✓ | 100 Hz ✓ |
| Analog 720×480 | 12 Hz ⚠️ | 35 Hz ✓ | 60 Hz ✓ |
| Web Interface | ✓ | ✓ | ✓ |
| SBUS Input | ✓ | ✓ | ✓ |

✓ = Works well
⚠️ = Works but slow

---

## Example Configurations

### Configuration 1: High Performance (Pi 4)
```json
{
  "camera": {
    "type": "usb_camera",
    "device": "/dev/video0",
    "width": 640,
    "height": 480,
    "fps": 60,
    "method": "farneback"
  },
  "control": {"update_rate_hz": 100},
  "stick_input": {"enabled": true, "protocol": "sbus"}
}
```

### Configuration 2: Lightweight (Pi Zero)
```json
{
  "camera": {
    "type": "csi_camera",
    "device": "auto",
    "width": 320,
    "height": 240,
    "fps": 30,
    "method": "lucas_kanade"
  },
  "control": {"update_rate_hz": 30},
  "web_interface": {"enabled": true}
}
```

### Configuration 3: Analog FPV Camera
```json
{
  "camera": {
    "type": "analog_usb",
    "device": "/dev/video0",
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback",
    "deinterlace": true
  },
  "tracker": {"initial_height": 0.7}
}
```
