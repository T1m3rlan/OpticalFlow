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
- **Sensor Tab**: Select sensor type, rotation, scale factor
- **PID Tuning Tab**: Adjust PID gains for both axes
- **Control Tab**: Update rate, max tilt, velocity damping
- **Camera Tab**: Configure camera settings (resolution, FPS, device)

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

## Analog Camera Support

### Overview
Now supports multiple camera types for optical flow:
- **PMW3901**: Dedicated optical flow sensor (SPI) - Original
- **Caddx Infra 256**: Infrared optical flow sensor (I2C) - **NEW!**
- **USB Cameras**: Standard webcams
- **CSI Cameras**: Raspberry Pi Camera Module
- **Analog Cameras**: FPV cameras via USB capture cards

### Why Use Analog Cameras?
- Already have FPV camera on drone
- No additional sensor needed
- Works with existing camera setup
- Better for daylight outdoor flying

### Setup for Analog Camera

#### 1. Hardware Connection
```
Analog FPV Camera -> USB Video Capture Card -> Raspberry Pi USB Port
```

Recommended capture cards:
- EasyCap DC60
- Elgato Cam Link 4K (high quality)
- Generic USB video capture dongles

#### 2. Software Configuration

Edit `config.json`:
```json
{
  "sensor": {
    "type": "analog_usb"
  },
  "camera": {
    "device": "/dev/video0",
    "width": 720,
    "height": 480,
    "fps": 30,
    "method": "farneback",
    "deinterlace": true
  }
}
```

#### 3. Test Camera

```bash
# List available video devices
ls /dev/video*

# Test camera capture
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print(f'Camera works: {ret}, Resolution: {frame.shape}')
cap.release()
"
```

### Camera Types Configuration

#### Caddx Infra 256 (I2C Infrared Sensor)
```json
{
  "sensor": {
    "type": "caddx_infra256"
  },
  "sensor": {
    "i2c_bus": 1,
    "i2c_address": 41,
    "rotation": 0
  }
}
```

**Advantages:**
- Infrared technology (better in various lighting)
- Simple I2C wiring (4 wires vs 6 for SPI)
- Lower power consumption
- Excellent for indoor/outdoor use

**Setup:**
1. Enable I2C: `sudo raspi-config` -> Interface Options -> I2C
2. Wire to Pi: VCC(3.3V), GND, SDA(Pin 3), SCL(Pin 5)
3. Test: `sudo i2cdetect -y 1` (should show 0x29)
4. Run: `python3 caddx_infra256.py` to test

See **[CADDX_INFRA256_GUIDE.md](CADDX_INFRA256_GUIDE.md)** for complete setup guide.

#### USB Camera (Webcam)
```json
{
  "sensor": {
    "type": "usb_camera"
  },
  "camera": {
    "device": 0,  // or "/dev/video0"
    "width": 640,
    "height": 480,
    "method": "farneback"
  }
}
```

#### Raspberry Pi Camera (CSI)
```bash
# Enable camera interface first
sudo raspi-config
# Interface Options -> Camera -> Enable
```

```json
{
  "sensor": {
    "type": "csi_camera"
  },
  "camera": {
    "device": 0,
    "width": 640,
    "height": 480
  }
}
```

#### Analog Camera via USB
```json
{
  "sensor": {
    "type": "analog_usb"
  },
  "camera": {
    "device": "/dev/video0",
    "width": 720,
    "height": 480,
    "deinterlace": true
  }
}
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
- Use 320x240 resolution
- Use Lucas-Kanade method
- Reduce update rate to 30Hz

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

**For Raspberry Pi Zero 2W or Pi 4:**
- Can use 640x480 resolution
- Farneback method works well
- 50Hz update rate

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
# Change sensor.type to "usb_camera"

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

| Feature | Pi Zero | Pi Zero 2W | Pi 4 |
|---------|---------|------------|------|
| PMW3901 | 50Hz ✓ | 100Hz ✓ | 100Hz ✓ |
| Caddx Infra 256 | 50Hz ✓ | 100Hz ✓ | 100Hz ✓ |
| USB Camera 320x240 | 30Hz ✓ | 50Hz ✓ | 100Hz ✓ |
| USB Camera 640x480 | 15Hz ⚠️ | 30Hz ✓ | 60Hz ✓ |
| Analog 720x480 | 10Hz ⚠️ | 30Hz ✓ | 50Hz ✓ |
| Web Interface | ✓ | ✓ | ✓ |
| SBUS Input | ✓ | ✓ | ✓ |

✓ = Works well
⚠️ = Works but slow

---

## Example Configurations

### Configuration 1: High Performance (Pi 4)
```json
{
  "sensor": {"type": "usb_camera"},
  "camera": {
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
  "sensor": {"type": "pmw3901"},
  "control": {"update_rate_hz": 50},
  "stick_input": {"enabled": true, "protocol": "sbus"},
  "web_interface": {"enabled": true}
}
```

### Configuration 4: Caddx Infra 256 (Recommended for Production)
```json
{
  "sensor": {
    "type": "caddx_infra256",
    "i2c_address": 41,
    "rotation": 0
  },
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.8
  },
  "control": {"update_rate_hz": 50},
  "stick_input": {"enabled": true, "protocol": "sbus"}
}
```

### Configuration 3: Camera Only (No PMW3901)
```json
{
  "sensor": {"type": "analog_usb"},
  "camera": {
    "device": "/dev/video0",
    "width": 320,
    "height": 240,
    "method": "lucas_kanade",
    "deinterlace": true
  },
  "control": {"update_rate_hz": 30}
}
```
