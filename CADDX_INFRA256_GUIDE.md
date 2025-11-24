# Caddx Infra 256 Setup Guide

## Overview

The Caddx Infra 256 is an infrared optical flow sensor designed specifically for drones. It provides GPS-free position tracking using I2C communication.

### Advantages over PMW3901
- **Infrared Technology**: Better performance in various lighting conditions
- **I2C Communication**: Simpler wiring (only 2 data lines)
- **Low Power**: Optimized for battery-powered applications
- **Compact Design**: Smaller footprint for micro drones

### Specifications
- **Interface**: I2C (address 0x29 / 41 decimal)
- **Resolution**: 256 x 256 pixels
- **Frame Rate**: Up to 100 Hz
- **Operating Voltage**: 3.3V
- **Current**: ~15mA
- **Field of View**: ~42° diagonal
- **Optimal Height**: 0.3m - 3.0m above ground

## Hardware Setup

### Wiring Diagram

```
Caddx Infra 256 -> Raspberry Pi Zero
-----------------------------------------
VCC (3.3V)      -> Pin 1 (3.3V Power)
GND             -> Pin 6 (Ground)
SDA             -> Pin 3 (GPIO 2 / I2C SDA)
SCL             -> Pin 5 (GPIO 3 / I2C SCL)
```

### Pin Reference

| Caddx Pin | Pi Pin | GPIO | Function |
|-----------|--------|------|----------|
| VCC       | 1      | -    | 3.3V     |
| GND       | 6/9/14 | -    | Ground   |
| SDA       | 3      | 2    | I2C Data |
| SCL       | 5      | 3    | I2C Clock|

### Mounting
- Mount sensor facing **downward** with clear view of ground
- Ensure sensor is parallel to ground (level)
- Avoid mounting near bright LEDs or heat sources
- Keep lens clean and unobstructed

## Software Installation

### 1. Enable I2C Interface

```bash
# Enable I2C using raspi-config
sudo raspi-config

# Navigate to:
# Interface Options -> I2C -> Enable

# Reboot to apply
sudo reboot
```

### 2. Install I2C Tools

```bash
# Install i2c-tools for debugging
sudo apt-get install -y i2c-tools python3-smbus

# Alternative: use smbus2 (already in requirements.txt)
pip3 install smbus2
```

### 3. Verify I2C Connection

```bash
# Check I2C devices
sudo i2cdetect -y 1

# You should see device at address 0x29 (row 20, column 9)
# Output example:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 20: -- -- -- -- -- -- -- -- -- 29 -- -- -- -- -- -- 
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
```

### 4. Test Sensor

```bash
# Run standalone test
python3 caddx_infra256.py

# Output should show:
# - Sensor detected at address 0x29
# - Product ID and diagnostics
# - Motion readings when sensor is moved
```

## Configuration

### Basic Configuration

Edit `config.json`:

```json
{
  "sensor": {
    "type": "caddx_infra256",
    "i2c_bus": 1,
    "i2c_address": 41,
    "rotation": 0
  },
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5
  }
}
```

### Configuration Parameters

#### `i2c_bus`
- Default: `1` (Raspberry Pi standard I2C bus)
- Pi Zero/3/4: Use bus 1
- Older Pi models: May use bus 0

#### `i2c_address`
- Default: `41` (decimal) = `0x29` (hex)
- If multiple I2C devices conflict, address may be different
- Use `i2cdetect` to find actual address

#### `rotation`
- `0`: Sensor forward (default)
- `90`: Sensor rotated 90° clockwise
- `180`: Sensor rotated 180°
- `270`: Sensor rotated 270° clockwise

### Scale Factor Tuning

The scale factor converts sensor units to meters. Default is `0.001`, but you may need to adjust based on:

**For Lower Altitudes (0.3-0.5m):**
```json
"scale_factor": 0.0008
```

**For Higher Altitudes (1.0-2.0m):**
```json
"scale_factor": 0.0012
```

**Tuning Method:**
1. Hover drone at known height
2. Move exactly 1 meter in one direction
3. Check logged position
4. Adjust scale_factor: `new_scale = old_scale * (actual_distance / measured_distance)`

## Usage

### Start with Caddx Infra 256

```bash
# Basic usage
./betafly_stabilizer_advanced.py --config config.json

# With web interface (recommended)
./betafly_stabilizer_advanced.py

# Then access http://raspberrypi.local:8080
# Select "Caddx Infra 256" from sensor dropdown
```

### Via Web Interface

1. Open web browser to `http://raspberrypi.local:8080`
2. Go to **Configuration** -> **Sensor** tab
3. Select **"Caddx Infra 256 (I2C)"** from dropdown
4. Set I2C address if different from default (41)
5. Set rotation based on mounting
6. Click **"Save Configuration"**
7. Restart system

## Troubleshooting

### Sensor Not Detected

**Check I2C is Enabled:**
```bash
# Should list I2C devices
ls /dev/i2c*
# Expected: /dev/i2c-1

# If missing, enable I2C:
sudo raspi-config
# Interface Options -> I2C -> Enable -> Reboot
```

**Check Wiring:**
```bash
# Scan I2C bus
sudo i2cdetect -y 1

# If sensor not showing at 0x29:
# - Check power (3.3V, not 5V!)
# - Check SDA/SCL connections
# - Check ground connection
# - Try different I2C address (some sensors vary)
```

**Check Permissions:**
```bash
# Add user to i2c group
sudo usermod -a -G i2c pi
sudo reboot
```

### Poor Tracking Quality

**Low Surface Quality Reading (<50):**
- Improve lighting (sensor needs some light)
- Ensure surface below has visible texture
- Avoid uniform/blank surfaces (carpet works better than bare floor)
- Clean sensor lens

**Erratic Motion Readings:**
- Check sensor is firmly mounted (no vibration)
- Verify sensor is level (parallel to ground)
- Ensure height setting matches actual height
- Check for reflective surfaces below

**Position Drift:**
- Calibrate scale_factor at your flying height
- Verify rotation setting matches physical mounting
- Check sensor lens is clean
- Ensure stable lighting conditions

### I2C Communication Errors

**"OSError: [Errno 121] Remote I/O error":**
- Sensor not responding or wrong address
- Check wiring and power
- Try scanning with `i2cdetect`

**"No module named 'smbus2'":**
```bash
pip3 install smbus2
```

**Intermittent Communication:**
- Add pull-up resistors (4.7kΩ) on SDA and SCL lines
- Shorten I2C wires (keep under 20cm if possible)
- Reduce I2C clock speed (add to `/boot/config.txt`):
  ```
  dtparam=i2c_arm_baudrate=50000
  ```

## Performance Comparison

| Feature | Caddx Infra 256 | PMW3901 |
|---------|-----------------|---------|
| Interface | I2C | SPI |
| Wiring | 4 wires | 6 wires |
| Max Update Rate | 100 Hz | 120 Hz |
| Power | ~15mA | ~20mA |
| Lighting | Infrared (better) | Visible light |
| Cost | $$ | $ |
| Best For | Production drones | Prototyping |

## Advanced Features

### Reading Diagnostics

```python
from caddx_infra256 import CaddxInfra256

sensor = CaddxInfra256()
diag = sensor.get_diagnostics()

print(f"Product ID: {diag['product_id']}")
print(f"Surface Quality: {diag['surface_quality']}")
print(f"Shutter: {diag['shutter']}")
print(f"Pixel Avg: {diag['pixel_avg']}")
```

### Resolution Modes

The sensor supports high and low resolution modes:

```python
sensor.set_resolution(high_res=True)  # High resolution (default)
sensor.set_resolution(high_res=False)  # Low res, faster updates
```

### Power Modes

For battery-powered applications:

```python
sensor.set_power_mode(low_power=True)  # Reduce power consumption
```

## Best Practices

### Mounting Position
- **Height**: 0.5m - 1.5m for best accuracy
- **Angle**: Keep sensor perpendicular to ground
- **Vibration**: Use soft mounting or dampers

### Surface Requirements
- **Texture**: Moderate texture works best
- **Lighting**: Some ambient light required (infrared helps in low light)
- **Avoid**: Glass, mirrors, water surfaces, uniform colors

### Flight Conditions
- **Indoor**: Excellent (best use case)
- **Outdoor Day**: Good (infrared less affected by sun)
- **Outdoor Night**: Good with ground lighting
- **Rain**: Not recommended (water on lens)

### Calibration Tips
1. **Ground Test**: Always test on ground before flying
2. **Height Check**: Verify position tracking at actual flight height
3. **Surface Test**: Test over your intended flying surface
4. **Scale Tuning**: Adjust scale_factor for your specific height

## Example Flight Configuration

### Indoor Flight (0.5m height)
```json
{
  "sensor": {
    "type": "caddx_infra256",
    "i2c_address": 41,
    "rotation": 0
  },
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5
  },
  "pid": {
    "position_x": {"kp": 0.6, "ki": 0.1, "kd": 0.25},
    "position_y": {"kp": 0.6, "ki": 0.1, "kd": 0.25}
  },
  "control": {
    "update_rate_hz": 50
  }
}
```

### Outdoor Flight (1.0m height)
```json
{
  "sensor": {
    "type": "caddx_infra256",
    "i2c_address": 41,
    "rotation": 0
  },
  "tracker": {
    "scale_factor": 0.0012,
    "initial_height": 1.0
  },
  "pid": {
    "position_x": {"kp": 0.5, "ki": 0.05, "kd": 0.3},
    "position_y": {"kp": 0.5, "ki": 0.05, "kd": 0.3}
  },
  "control": {
    "update_rate_hz": 50
  }
}
```

## Support & Resources

### Official Resources
- Caddx Website: [www.caddxfpv.com](https://www.caddxfpv.com)
- Product Manual: Check manufacturer's website
- Datasheet: Available from distributor

### Community Support
- RC Groups Forum: FPV Equipment section
- Reddit: /r/Multicopter
- GitHub Issues: This repository

### Additional Help
For Betafly-specific issues:
1. Check system logs: `sudo journalctl -u betafly-stabilizer.service -f`
2. Run sensor test: `python3 caddx_infra256.py`
3. Enable verbose logging: `./betafly_stabilizer_advanced.py -v`
4. Check web interface diagnostics at http://raspberrypi.local:8080

---

**Note**: The Caddx Infra 256 driver is based on common optical flow sensor protocols. Some register addresses may need adjustment for specific firmware versions. If you experience issues, please report them with diagnostic output.
