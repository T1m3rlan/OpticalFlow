# Installation Guide

## Hardware Setup

### 1. Connect PMW3901 Sensor to Raspberry Pi Zero

| PMW3901 Pin | Pi Zero Pin | Pin Number | Function |
|-------------|-------------|------------|----------|
| VCC         | 3.3V        | Pin 1      | Power    |
| GND         | Ground      | Pin 6      | Ground   |
| MOSI        | GPIO 10     | Pin 19     | SPI MOSI |
| MISO        | GPIO 9      | Pin 21     | SPI MISO |
| SCLK        | GPIO 11     | Pin 23     | SPI CLK  |
| CS          | GPIO 8      | Pin 24     | SPI CE0  |

**Mounting**: Sensor should face downward with clear view of ground surface.

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

# 3. Enable SPI
sudo raspi-config
# Interface Options -> SPI -> Enable

# 4. Install Python packages
pip3 install -r requirements.txt

# 5. Make scripts executable
chmod +x betafly_stabilizer.py test_sensor.py setup.sh

# 6. Reboot
sudo reboot
```

## Verification

### 1. Test Sensor Connection

```bash
./test_sensor.py --test connection
```

Expected output:
```
✓ Sensor initialized successfully
✓ Product ID: 0x49
```

### 2. Test Motion Detection

```bash
./test_sensor.py --test motion --duration 5
```

Move the sensor and verify motion values change.

### 3. Test Position Tracking

```bash
./test_sensor.py --test tracking --duration 10
```

Move sensor in a pattern and observe position integration.

## Configuration

### 1. Edit Config File

```bash
nano config.json
```

### 2. Key Settings to Adjust

**Sensor Rotation**: Match physical mounting
```json
"rotation": 0  // 0, 90, 180, or 270 degrees
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

- [ ] Sensor securely mounted and facing down
- [ ] All connections secure and insulated
- [ ] Pi powered from stable BEC (not USB)
- [ ] Manual control mode configured as backup
- [ ] Test area is safe and clear
- [ ] Adequate lighting for optical tracking
- [ ] Textured surface below (not uniform/blank)

### Test Procedure

1. **Ground Test**
   ```bash
   ./betafly_stabilizer.py --mode velocity_damping --log
   ```
   - Move drone manually on ground
   - Verify sensor responds correctly
   - Check logs show reasonable values

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

### SPI Not Working

```bash
# Check SPI is enabled
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1

# Check kernel module loaded
lsmod | grep spi
# Should show: spi_bcm2835

# If not enabled:
sudo raspi-config
# Interface Options -> SPI -> Enable -> Reboot
```

### Sensor Not Responding

```bash
# Test with spidev directly
python3 -c "import spidev; s = spidev.SpiDev(); s.open(0,0); print('OK')"

# Check wiring with multimeter
# VCC should be 3.3V
# GND should be 0V
```

### Poor Tracking

- Ensure good lighting (not direct sun)
- Check surface has visible texture
- Clean sensor lens
- Verify height setting is accurate
- Reduce vibrations (add damping)

### Permission Errors

```bash
# Add user to SPI group
sudo usermod -a -G spi,gpio pi

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
