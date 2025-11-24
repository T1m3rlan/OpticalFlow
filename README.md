# Betafly Visual Position Stabilization

Camera-only visual odometry and stabilization for the Betafly drone family. The system runs entirely on a Raspberry Pi Zero / Zero 2 and uses Raspberry Pi Camera Modules (IMX219/OV5647) or analog FPV cameras (via USB capture) to hold position without GPS or dedicated optical-flow sensors.

## ✨ Highlights

- **🌐 Web Interface** – Real-time dashboard, charts, and configuration editor (port `8080`)
- **📷 Camera-Only Tracking** – CSI (IMX219/OV5647), USB UVC, and analog FPV cameras supported out of the box
- **🎮 Manual Stick Blending** – SBUS/PPM/PWM input with smooth mixing into stabilization commands
- **🔧 Live Config Editing** – Tune PID, damping, camera, and loop settings from the browser
- **📊 Rich Telemetry** – Position, velocity, surface quality, and control outputs streamed live

## Core Features

- Visual odometry from any camera source (CSI/USB/analog)
- Velocity damping and position-hold modes
- Tunable PID + damping controller with logging
- MAVLink/MSP/PWM output hooks for your flight controller
- Designed for Pi Zero resource constraints (30–60 Hz loops on Zero, 100 Hz on Zero 2)

## Hardware Requirements

### Required

- Raspberry Pi Zero W or Zero 2 W (Zero 2 strongly recommended)
- One supported camera:
  - **CSI Camera Module** – Raspberry Pi Camera v1 (OV5647) or v2 (IMX219)
  - **USB UVC Camera** – Any webcam that works with OpenCV
  - **Analog FPV Camera + USB capture dongle**
- Flight controller (Betaflight, iNav, ArduPilot, PX4, …)
- Stable 5 V BEC for the Pi + camera/capture hardware
- Pi-to-FC UART wiring (see below)

### Optional

- SBUS/PPM receiver connected to Pi for manual stick capture
- External storage for long data-logging sessions

## Camera Wiring

### CSI Camera (IMX219 / OV5647)

1. Power off the Pi.
2. Lift the CSI latch, insert the 15‑pin ribbon with the **blue stiffener facing the Pi’s USB ports**, contacts toward the HDMI connector.
3. Insert the ribbon into the camera module with the **blue stiffener facing away from the lens** and lock the latch.

```
CSI Ribbon Orientation
┌──────────────────────────┐        ┌────────────────────────────┐
│ Raspberry Pi Zero (CSI)  │========│ IMX219 / OV5647 Camera     │
│ Contacts → HDMI connector│  FFC   │ Contacts → Lens PCB        │
└──────────────────────────┘        └────────────────────────────┘
Blue stiffener faces Pi USB ports.
```

Power, I²C, and differential lanes already ride inside the ribbon—no extra wires needed.

### Analog FPV Camera + USB Capture

Use any FPV cam (PAL/NTSC) and a UVC capture dongle (EasyCAP, Elgato, generic UVC). Power the camera from the same 5 V BEC as the Pi and share ground.

```
Analog FPV Cam              USB Capture Dongle             Pi Zero
──────────────              ──────────────────             ───────
Video (yellow) ───────────▶ RCA/Signal input ──USB OTG──▶ USB data port
Ground (black) ───────────▶ Ground ---------------------▶ Any Pi GND pin
5 V (red) ────── BEC 5 V ─▶ Dongle + Camera              ▶ Pi 5 V rail
```

Tips:
- Keep the video lead short to reduce noise.
- Enable deinterlacing in `config.json` when using analog sources (`camera.deinterlace: true`).

## Raspberry Pi Zero ↔ Flight Controller UART Wiring

Use the Pi’s 3.3 V UART (`serial0`) and connect it to any spare flight-controller UART. Disable the serial console (the setup script does this by setting `enable_uart=1`).

```
Pi Zero Header (top view)
┌────────────────────────────────────────────┐
│ 3V3 (1)  SDA (3)  SCL (5)  ...  TXD (8)    │
│ 5V  (2)  5V  (4)  GND (6)  ...  RXD (10)   │
└────────────────────────────────────────────┘
```

Connection table:

| Pi Pin | Signal                | Flight Controller Pad                |
|--------|-----------------------|--------------------------------------|
| Pin 6  | GND                   | Any ground                           |
| Pin 8  | GPIO14 / TXD (3.3 V)  | RX pad of the target UART            |
| Pin 10 | GPIO15 / RXD (3.3 V)  | TX pad of the same UART              |
| Pin 4/2 (optional) | 5 V      | Only if you need to power accessories |

⚠️ Do **not** feed 5 V/5.5 V UART signals into the Pi—logic is 3.3 V only. If you keep the Pi connected while plugging in USB, isolate the FC’s 5 V rail or use a diode/ideal switch so you do not back-feed the flight controller.

## Software Installation

### 1. Prepare the Pi

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo raspi-config # Enable Camera + Serial (Interface Options -> Camera / Serial)
```

Alternatively run the provided script (handles camera + UART toggles automatically):

```bash
cd ~/betafly-stabilization
chmod +x setup.sh
./setup.sh
```

### 2. Clone & Install

```bash
cd ~
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

### 3. Verify the Camera

```bash
# CSI cameras (IMX219 / OV5647)
libcamera-hello --list-cameras

# USB / Analog capture (UVC)
python3 - <<'PY'
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print("Camera OK:", ret, "Resolution:", None if frame is None else frame.shape)
cap.release()
PY
```

## Configuration Overview

`config.json` ships with sensible defaults for CSI cameras:

```json
{
  "sensor": {
    "type": "csi_camera",
    "rotation": 0
  },
  "camera": {
    "device": 0,
    "width": 640,
    "height": 480,
    "fps": 30,
    "method": "farneback",
    "deinterlace": true
  },
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5
  },
  "stabilizer": {
    "max_tilt_angle": 15.0,
    "velocity_damping": 0.3
  }
}
```

> `sensor.type` options: `csi_camera`, `usb_camera`, `analog_usb`, `opencv_any` (auto-detect first camera).

## Usage

### Quick Start (with Web UI)

```bash
./betafly_stabilizer_advanced.py
# open http://raspberrypi.local:8080
```

### CLI Examples

```bash
# Velocity damping only
./betafly_stabilizer.py --mode velocity_damping

# Advanced stack, explicit config and logging
./betafly_stabilizer_advanced.py --config config.json --log --mode position_hold

# Run advanced stack without the web UI
./betafly_stabilizer_advanced.py --no-web
```

### Selecting Camera Types

| Sensor Type    | How to configure                                   | Notes                                      |
|----------------|----------------------------------------------------|--------------------------------------------|
| `csi_camera`   | Default. Set `camera.device` to `0` or `auto`.     | Works with IMX219 / OV5647 using libcamera |
| `usb_camera`   | Set device to `/dev/video0` or index `0`.          | Any UVC webcam                             |
| `analog_usb`   | Device `/dev/video0`, enable `camera.deinterlace`. | FPV cam + USB capture dongle               |
| `opencv_any`   | Set device to `"auto"` or leave blank.             | Automatically grabs the first working cam  |

## Flight Controller Integration

1. Wire Pi TX/RX as described earlier.
2. In Betaflight/iNav: assign an unused UART for MSP or custom protocol; disable “Serial RX”.
3. In `config.json`, set:
   ```json
   "output": {
     "interface": "msp",   // or "mavlink"
     "port": "/dev/serial0",
     "baudrate": 115200
   }
   ```
4. Implement `_send_corrections` (currently a stub) with MST/MAVLink messages suited to your FC.

## Tuning & Calibration

1. **Verify visual flow** – Start with `./betafly_stabilizer_advanced.py --log`, move the drone by hand, and check the web UI chart plus `surface_quality` (>50 indoors, >100 outdoors).
2. **Set height** – Adjust the web slider to match hover altitude so the tracker scales pixel flow correctly.
3. **Tune velocity damping** – Increase `stabilizer.velocity_damping` until drift slows but oscillations stay tame.
4. **Tune PID** – Increment `kp`, then `kd`, then introduce a small `ki`. Use the live chart to avoid overshoot.

Troubleshooting tips:
- CSI cameras: run `libcamera-hello` if no frames arrive.
- USB/Analog cameras: `ls /dev/video*` and ensure the capture dongle enumerates as UVC.
- Surface quality low? Increase lighting, add texture (matte tape) under the drone, or raise height.

## Performance Optimization

- **Pi Zero W** – 30–40 Hz loop, reduce resolution to 320×240, disable logging, overclock to 1 GHz if cooled.
- **Pi Zero 2 W** – 60–100 Hz loop, 640×480 video, simultaneous logging and web UI.
- Use Farneback for analog/camera noise robustness; Lucas–Kanade saves CPU for textured indoor floors.

## Data Logging

Set `"logging.enabled": true` or pass `--log`. CSV columns:

- `time`, `pos_x`, `pos_y`, `vel_x`, `vel_y`
- `pitch_cmd`, `roll_cmd`, `mode`, `surface_quality`
- Stick positions when stick mixing is enabled

Plot with pandas/matplotlib:
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('flight_log.csv')
plt.plot(df['time'], df['pos_x'], label='X position')
plt.plot(df['time'], df['pos_y'], label='Y position')
plt.legend()
plt.xlabel('Time (s)')
plt.ylabel('Position (m)')
plt.show()
```

## Troubleshooting Cheatsheet

- **No camera detected** – check ribbon orientation, `dmesg | grep -i camera`, or `lsusb` for capture dongles.
- **Motion feels mirrored** – set `sensor.rotation` to 90/180/270 matching the physical orientation.
- **Web UI empty** – ensure `betafly_stabilizer_advanced.py` launches with web enabled or run `flask run`.
- **UART spam on boot** – disable console on `/boot/cmdline.txt` (remove `console=serial0,115200`).

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
│  Estimation    │         │   Controller    │
│ (CSI/USB/Anal) │────────▶│ PID + Damping   │
└────────────────┘         └─────────┬───────┘
                                     │
                            ┌────────▼────────┐
                            │ Flight Control  │
                            │   Interface     │
                            │ MAVLink/MSP/PWM │
                            └─────────────────┘
```

## Project Files

- `betafly_stabilizer.py` – lightweight CLI stabilizer
- `betafly_stabilizer_advanced.py` – web-enabled stack
- `camera_optical_flow.py` – CSI/USB/analog motion extraction
- `flow_tracker.py` – integrates motion into position/velocity
- `position_stabilizer.py`, `stick_input.py`, `web_interface.py`
- `templates/`, `static/` – web dashboard assets
- `config.json`, `requirements.txt`, `setup.sh`
- Documentation: `README.md`, `FEATURES.md`, `INSTALL.md`

## Contributing

PRs are welcome! High-impact areas:
- Implementing MAVLink/MSP output inside `_send_corrections`
- Automatic gain/height calibration
- Sensor fusion with barometer/IMU data
- Additional frontend visualizations

## License & Safety

MIT License (see `LICENSE`). This is experimental software:
- Fly in open areas with a manual override ready.
- Start with low gains and keep props off for bench testing.
- Share ground between every board you connect.

## Credits

- Raspberry Pi Camera Module IMX219/OV5647 hardware team
- OpenCV community for the optical-flow algorithms
- Betaflight/iNav/PX4 developers for open flight stacks
- Everyone in the Betafly community testing visual stabilization

---

**Happy flying! 🚁**
