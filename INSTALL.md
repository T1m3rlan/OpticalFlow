# Installation Guide

## Hardware Setup

### 1. Connect Your Camera

#### CSI Cameras (IMX219 / OV5647)
- Insert the ribbon cable into the Pi Zero’s **CAM0** connector with the silver contacts facing the HDMI port.
- Secure the latch evenly so the ribbon cannot wiggle loose.
- Mount the camera firmly so it points straight down; use double-sided tape with foam or a small 3D-printed bracket for vibration damping.

#### Analog FPV Cameras
```
Analog Camera -> UVC Capture Stick -> Pi Zero (USB OTG cable)
```
- Power the FPV camera from a 5 V BEC (same one that powers the Pi).
- Tie the camera ground, Pi ground, and flight controller ground together.
- Plug the capture stick into the Pi via a micro-USB OTG cable and note the `/dev/video*` path.

#### USB Webcams
- Plug the webcam directly into a powered USB hub or OTG cable.
- Confirm it shows up under `/dev/video*` after boot.

### 2. Wire Pi Zero UART to the Flight Controller

| Pi Zero Pin | Signal | Connects To | Notes |
|-------------|--------|-------------|-------|
| Pin 8 (GPIO14) | TXD0 (3.3 V) | Flight controller **RX** | Sends stabilization corrections (MAVLink/MSP/PWM proxy). |
| Pin 10 (GPIO15) | RXD0 (3.3 V) | Flight controller **TX** | Optional—receives telemetry or ACKs. |
| Pin 6 | GND | Flight controller GND | Shared ground is required for UART to work. |

Tips:
1. Disable the Linux serial console so `/dev/ttyAMA0` is free (`sudo raspi-config` → Interface Options → Serial → Disable login shell, enable hardware UART).
2. Keep TX/RX wires short and twisted to reduce noise.
3. Most flight controllers run 3.3 V UARTs, so no level shifter is needed. Do **not** connect to 5 V-only serial ports.

### 3. Power & Ground

- Feed the Pi Zero from a stable 5 V regulator/BEC capable of at least 1 A continuous.
- Add a 220–470 µF electrolytic capacitor close to the Pi to absorb battery dips.
- Share ground between the Pi, flight controller, camera, and receiver.

## Software Installation

### Quick Install (Recommended)

```bash
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization

# Run the helper (installs Python deps and enables the camera interface)
./setup.sh

# Reboot if prompted so the camera overlay takes effect
sudo reboot
```

### Manual Install

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install toolchain
sudo apt-get install -y python3 python3-pip python3-dev git

# 3. Enable camera + UART (raspi-config GUI)
sudo raspi-config
# Interface Options -> Camera -> Enable
# Interface Options -> Serial -> Disable login shell, enable hardware serial

# 4. Install Python packages
pip3 install -r requirements.txt

# 5. Make helper scripts executable
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py test_sensor.py setup.sh
```

## Verification

### 1. Check the Camera Feed

```bash
# CSI cameras
libcamera-hello -t 3000

# USB / analog capture devices
v4l2-ctl --list-devices
```

You should see the preview window (CSI) or at least one `/dev/video*` entry (USB/analog).

### 2. Run the Optical Flow Test

```bash
# Auto-detect CSI/USB camera
python3 test_sensor.py --type csi_camera --device auto --duration 10

# Analog example
python3 test_sensor.py --type analog_usb --device /dev/video0 --duration 10
```

Watch the console for live position/velocity estimates and surface quality.

## Configuration

Edit `config.json`:

```bash
nano config.json
```

Key sections:

- **Camera block** – choose the transport and device path:
  ```json
  "camera": {
    "type": "csi_camera",
    "device": "auto",
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback",
    "deinterlace": true
  }
  ```
- **Tracker** – set the expected hover height:
  ```json
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5
  }
  ```
- **Output** – pick how corrections are sent:
  ```json
  "output": {
    "interface": "mavlink",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200
  }
  ```

## Running the System

```bash
# Basic loop (headless)
./betafly_stabilizer.py --mode velocity_damping --config config.json

# Full stack with web UI (recommended)
./betafly_stabilizer_advanced.py --config config.json --mode position_hold

# Enable CSV logging
./betafly_stabilizer_advanced.py --log --config config.json
```

### Optional: systemd service

```bash
sudo cp betafly-stabilizer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable betafly-stabilizer.service
sudo systemctl start betafly-stabilizer.service
```

## Flight Controller Integration

### Serial (MAVLink / MSP)
1. Wire TX/RX as described in the hardware section.
2. Set the desired protocol in `config.json` (`"interface": "mavlink"` or `"msp"`).
3. Implement the protocol inside `_send_corrections()` (see `betafly_stabilizer*.py` placeholder).

### PWM Override
1. Use a pigpio-capable GPIO breakout if you need PWM outputs.
2. Set `"interface": "pwm"` under `output`.
3. Generate servo pulses that nudge roll/pitch channels.

## Initial Flight Test

1. **Ground test** – Run in velocity damping mode, pick up the frame, and verify the live position readout responds.
2. **Hover test** – Take off manually, enable velocity damping, and confirm drift reduction.
3. **Position hold** – Switch to `position_hold`, release sticks, and watch for a stable hover before flying higher.

Checklist:
- [ ] Camera ribbon secure or USB capture recognized
- [ ] Pi + flight controller share ground
- [ ] Surface below has texture / good lighting
- [ ] Manual override ready
- [ ] UART baud rates match

## Troubleshooting

### Camera Not Detected
```bash
libcamera-hello -t 1000          # CSI sanity check
v4l2-ctl --list-devices          # USB/analog devices
ls -l /dev/video*                # Should show at least one node
```
- Reseat the CSI ribbon (contacts toward HDMI).
- Ensure the `pi` user is in the `video` group (`sudo usermod -aG video pi`).
- Some cheap capture sticks draw a lot; try a powered hub.

### UART Not Working
```bash
sudo raspi-config                # Disable serial console, enable hardware UART
ls -l /dev/ttyAMA0
sudo cat /dev/ttyAMA0            # Should show random bytes when FC is chatty
```
- Double-check TX↔RX polarity.
- Match baud rate with the flight controller CLI.

### Blurry / Noisy Optical Flow
- Add more light or place a textured mat below the hover zone.
- Clean the camera lens and refocus (CSI modules are adjustable).
- Lower the resolution/fps for Pi Zero and switch to `lucas_kanade`.

### High CPU Usage
- Reduce camera resolution to 320×240.
- Drop control update rate to 30 Hz.
- Disable web logging during flights.

## Performance Tips

| Device | Suggested Camera Settings | Control Rate |
|--------|---------------------------|--------------|
| Pi Zero | 320×240 @ 30 fps, Lucas-Kanade | 30–40 Hz |
| Pi Zero 2 W | 640×480 @ 30 fps, Farneback | 50 Hz |
| Pi 4 | 640×480 @ 60 fps, Farneback | 100 Hz |

Optional overclock for Pi Zero (`/boot/config.txt`):
```
arm_freq=1000
over_voltage=2
```

## Support & Next Steps

1. Verify the camera feed and `test_sensor.py`.
2. Tune PID gains and `tracker.initial_height`.
3. Implement your flight controller protocol in `_send_corrections()`.
4. Fly in a safe area with a manual override ready.

- Main guide: [README.md](README.md)
- Feature deep dive: [FEATURES.md](FEATURES.md)
- Issues / questions: open a GitHub issue with logs.

⚠️ **Safety**: Never fly over people, and always keep the ability to disarm manually. 
