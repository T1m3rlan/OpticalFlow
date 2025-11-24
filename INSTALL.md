# Installation Guide

## Hardware Setup

### 1. Connect Camera to Raspberry Pi Zero

#### Raspberry Pi Camera (CSI)
1. Locate the CSI camera connector on the Pi Zero (the smaller connector).
2. Use the specific Pi Zero camera cable.
3. Insert cable with metal contacts facing **towards the board**.
4. Connect other end to camera module.

#### USB Camera / Analog Capture
1. Use a USB OTG adapter (Micro USB to USB A).
2. Plug in your USB webcam or USB Capture Card.

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

# Reboot to enable Camera (if prompted)
sudo reboot
```

### Manual Install

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install dependencies
sudo apt-get install -y python3 python3-pip python3-dev git libopencv-dev python3-opencv

# 3. Enable Camera
sudo raspi-config
# Interface Options -> Legacy Camera (or Camera) -> Enable

# 4. Install Python packages
pip3 install -r requirements.txt

# 5. Make scripts executable
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py setup.sh

# 6. Reboot
sudo reboot
```

## Verification

### 1. Test Camera
```bash
python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```
Should print `True`.

### 2. Run Advanced Script
```bash
./betafly_stabilizer_advanced.py --verbose
```
Check logs for "Camera initialized" and "Pos: ..." updates.

## Configuration

### 1. Edit Config File

```bash
nano config.json
```

### 2. Key Settings to Adjust

**Camera Resolution/Method**:
```json
"camera": {
  "width": 320,
  "height": 240,
  "method": "lucas_kanade"
}
```
(Use lower resolution and "lucas_kanade" for Pi Zero)

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
# Start advanced system
./betafly_stabilizer_advanced.py

# Start with specific mode
./betafly_stabilizer_advanced.py --mode velocity_damping

# With logging enabled
./betafly_stabilizer_advanced.py --log
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

### Option A: Serial Connection (MAVLink/MSP)

1. Connect Pi TX to FC RX (telemetry/UART port)
2. Update config:
```json
"output": {
  "interface": "mavlink",
  "port": "/dev/ttyAMA0",
  "baudrate": 115200
}
```
3. Implement `_send_corrections()` method for your protocol

### Option B: PWM Output

1. Connect Pi GPIO pins to FC receiver inputs
2. Update config:
```json
"output": {
  "interface": "pwm"
}
```
3. Install pigpio: `sudo apt-get install pigpio python3-pigpio`
4. Implement PWM generation in `_send_corrections()`

## Initial Flight Test

### Safety Checklist

- [ ] Camera securely mounted and facing down
- [ ] All connections secure and insulated
- [ ] Pi powered from stable BEC (not USB)
- [ ] Manual control mode configured as backup
- [ ] Test area is safe and clear
- [ ] Adequate lighting
- [ ] Textured surface below (not uniform/blank)

### Test Procedure

1. **Ground Test**
   ```bash
   ./betafly_stabilizer_advanced.py --mode velocity_damping --log
   ```
   - Move drone manually on ground
   - Verify position tracking responds correctly
   - Check web interface for visualization

2. **Hover Test**
   - Start in manual mode
   - Take off and hover at ~0.5m height
   - Enable velocity damping
   - Verify drift reduction

3. **Position Hold Test**
   - Hover stable in velocity damping mode
   - Switch to position hold
   - Release controls
   - Verify drone maintains position

## Troubleshooting

### Camera Not Working

```bash
# Check if device exists
ls /dev/video*

# Check permissions
groups
# Should include 'video'
```

### Poor Tracking

- Ensure good lighting (not direct sun)
- Check surface has visible texture
- Clean camera lens
- Verify height setting is accurate
- Reduce vibrations (add damping)

### Slow Performance on Pi Zero

- Switch to `lucas_kanade` method
- Reduce resolution to 320x240
- Reduce update rate to 30Hz
- Disable web interface (`--no-web`)
