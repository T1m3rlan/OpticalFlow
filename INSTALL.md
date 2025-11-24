# Installation Guide

## Hardware Setup

### 1. Connect Camera to Raspberry Pi Zero

#### Option A: Raspberry Pi Camera Module (Recommended)

**Connection Steps:**
1. Locate the CSI connector on Raspberry Pi Zero (between HDMI and audio jack)
2. Lift the black plastic tab on the CSI connector
3. Insert the camera ribbon cable with the contacts facing away from the Ethernet port
4. Push the black tab down to lock the cable in place

**Pinout (for reference - handled automatically by ribbon cable):**
- Camera Module uses 15-pin CSI connector
- All connections handled by ribbon cable - no manual wiring needed

**Mounting**: Camera should face downward with clear view of ground surface.

#### Option B: USB Camera

**Connection:**
- Plug USB webcam into Raspberry Pi Zero USB port
- Use USB OTG adapter if needed for Pi Zero

#### Option C: Analog Camera with USB Capture Card

**Connection:**
- Connect analog FPV camera video output to USB capture card
- Plug USB capture card into Raspberry Pi Zero USB port

### 2. Power Supply

- Raspberry Pi Zero requires stable 5V supply
- Use a BEC (Battery Eliminator Circuit) from drone battery
- Minimum 2A capacity recommended
- Add capacitor (100-470µF) near Pi for stability

## Software Installation

### Quick Install (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization

# Run setup script
./setup.sh

# Reboot to enable SPI (if prompted)
sudo reboot
```

### Manual Install

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install dependencies
sudo apt-get install -y python3 python3-pip python3-dev git

# 3. Enable Camera Interface (for CSI cameras)
sudo raspi-config
# Interface Options -> Camera -> Enable

# 4. Enable Serial Port (for FC communication)
sudo raspi-config
# Interface Options -> Serial Port
# - Login shell over serial: NO
# - Serial port hardware: YES

# 4. Install Python packages
pip3 install -r requirements.txt

# 5. Make scripts executable
chmod +x betafly_stabilizer.py test_sensor.py setup.sh

# 6. Reboot
sudo reboot
```

## Verification

### 1. Test Camera Connection

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

### 2. Test Camera Optical Flow

```bash
# Start the stabilizer and observe camera feed
./betafly_stabilizer_advanced.py --mode velocity_damping
```

Move the drone and verify position tracking in the web interface.

### 3. Test Serial Connection to Flight Controller

```bash
# Test serial output
echo "test" > /dev/ttyAMA0

# Monitor serial input (if FC is sending data)
cat /dev/ttyAMA0
```

## Configuration

### 1. Edit Config File

```bash
nano config.json
```

### 2. Key Settings to Adjust

**Camera Type**: Select your camera
```json
"camera": {
  "type": "csi_camera"  // or "usb_camera", "analog_usb"
}
```

**Flight Height**: Expected altitude above ground
```json
"initial_height": 0.5  // meters
```

**PID Gains**: Start conservative, tune later
```json
"position_x": {
  "kp": 0.5,
  "ki": 0.1,
  "kd": 0.2
}
```

## Running the System

### Manual Start

```bash
# Velocity damping mode (recommended for first flight)
./betafly_stabilizer.py --mode velocity_damping

# Position hold mode
./betafly_stabilizer.py --mode position_hold

# With logging enabled
./betafly_stabilizer.py --mode position_hold --log
```

### Auto-Start on Boot (Optional)

```bash
# Copy service file
sudo cp betafly-stabilizer.service /etc/systemd/system/

# Edit paths in service file if needed
sudo nano /etc/systemd/system/betafly-stabilizer.service

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable betafly-stabilizer.service

# Start service
sudo systemctl start betafly-stabilizer.service

# Check status
sudo systemctl status betafly-stabilizer.service

# View logs
sudo journalctl -u betafly-stabilizer.service -f
```

## Flight Controller Integration

### Serial Connection Setup

**Hardware Wiring:**
- Raspberry Pi Zero GPIO 14 (TXD) → Flight Controller RX pad
- Raspberry Pi Zero GPIO 15 (RXD) → Flight Controller TX pad
- Raspberry Pi Zero GND → Flight Controller GND

**Physical Pin Locations:**
- Pin 8 (GPIO 14 / TXD) → FC RX
- Pin 10 (GPIO 15 / RXD) → FC TX
- Pin 6 (GND) → FC GND

**Software Configuration:**

1. Enable serial port (if not already done):
```bash
sudo raspi-config
# Interface Options -> Serial Port
# - Login shell over serial: NO
# - Serial port hardware: YES
```

2. Update config.json:
```json
"output": {
  "interface": "mavlink",  // or "msp" for Betaflight/iNav
  "port": "/dev/ttyAMA0",
  "baudrate": 115200
}
```

3. Configure flight controller UART for MAVLink or MSP at 115200 baud

**Important**: Ensure voltage levels match (3.3V for most FCs). Do NOT connect to 5V UARTs without level shifter!

## Initial Flight Test

### Safety Checklist

- [ ] Camera securely mounted and facing down
- [ ] All connections secure and insulated
- [ ] Pi powered from stable BEC (not USB)
- [ ] Serial connection to FC verified (TX/RX/GND)
- [ ] Manual control mode configured as backup
- [ ] Test area is safe and clear
- [ ] Adequate lighting for optical tracking
- [ ] Textured surface below (not uniform/blank)

### Test Procedure

1. **Ground Test**
   ```bash
   ./betafly_stabilizer_advanced.py --mode velocity_damping --log
   ```
   - Move drone manually on ground
   - Verify camera tracking responds correctly
   - Check web interface shows position changes
   - Check logs show reasonable values

2. **Hover Test**
   - Start in manual mode
   - Take off and hover at ~0.5m height
   - Enable velocity damping via web interface or RC switch
   - Verify drift reduction

3. **Position Hold Test**
   - Hover stable in velocity damping mode
   - Switch to position hold via web interface or RC switch
   - Release controls
   - Verify drone maintains position

## Troubleshooting

### Camera Not Detected

**CSI Camera:**
```bash
# Check camera is enabled
sudo raspi-config
# Interface Options -> Camera -> Enable

# Test camera
raspistill -o test.jpg
# Or: libcamera-still -o test.jpg

# Check ribbon cable connection
# Ensure contacts face away from Ethernet port
```

**USB Camera:**
```bash
# List video devices
ls /dev/video*

# Test with OpenCV
python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"

# Check USB connection
lsusb
```

### Serial Port Not Working

```bash
# Check serial port is enabled
sudo raspi-config
# Interface Options -> Serial Port
# - Login shell over serial: NO
# - Serial port hardware: YES

# Test serial port
echo "test" > /dev/ttyAMA0

# Check wiring
# Pi GPIO 14 (TXD) -> FC RX
# Pi GPIO 15 (RXD) -> FC TX
# Pi GND -> FC GND
```

### Poor Tracking

- Ensure good lighting (not direct sun)
- Check surface has visible texture
- Clean sensor lens
- Verify height setting is accurate
- Reduce vibrations (add damping)

### Permission Errors

```bash
# Add user to video group (for camera access)
sudo usermod -a -G video,gpio pi

# Make scripts executable
chmod +x *.py *.sh

# Reboot
sudo reboot
```

## Performance Optimization

### For Raspberry Pi Zero

```json
{
  "control": {
    "update_rate_hz": 30  // Reduce from 50
  },
  "logging": {
    "enabled": false  // Disable for production
  }
}
```

Optional overclock (`/boot/config.txt`):
```
arm_freq=1000
over_voltage=2
```

### For Raspberry Pi Zero 2 W

Can handle higher rates:
```json
{
  "control": {
    "update_rate_hz": 100
  }
}
```

## Next Steps

1. ✓ Verify sensor working
2. ✓ Configure for your setup
3. ✓ Ground test tracking
4. → Tune PID gains (see README.md)
5. → Implement flight controller interface
6. → Flight test in safe area

## Support

- Documentation: [README.md](README.md)
- Tuning Guide: See "Tuning Guide" section in README.md
- Issues: Create GitHub issue with logs

## Safety Reminder

⚠️ **Always have manual override ready**
⚠️ **Test in safe, controlled environment**
⚠️ **Monitor battery voltage**
⚠️ **Never fly over people**
