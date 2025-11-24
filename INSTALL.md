# Installation Guide

This guide walks through connecting Raspberry Pi camera hardware (IMX219/OV5647 or analog FPV) to a Pi Zero, wiring the Pi to your flight controller, and installing the Betafly visual stabilization stack.

---

## 1. Hardware Setup

### 1.1 Camera Connection

**CSI Camera (IMX219 / OV5647)**
1. Power off the Pi Zero.
2. Lift the CSI connector latch, insert the ribbon cable with the blue stiffener facing the USB ports (contacts toward the HDMI connector).
3. Insert the other end into the camera board with the blue stiffener away from the lens and lock it.
4. Avoid sharp bends in the ribbon; secure it with tape or a 3D-printed clamp.

**Analog FPV Camera + USB Capture**
1. Power the FPV camera from the same 5 V BEC as the Pi (2 A minimum). Share ground.
2. Connect the camera’s video line (yellow) to the capture dongle’s RCA/three-pin video input.
3. Plug the capture dongle into the Pi’s USB OTG port (micro‑USB OTG adapter required on a Pi Zero W).
4. Set `camera.deinterlace` to `true` in `config.json`.

### 1.2 Pi Zero ↔ Flight Controller UART

| Pi Pin | Signal (3.3 V) | Connect To                    |
|--------|----------------|-------------------------------|
| Pin 6  | GND            | Flight controller ground      |
| Pin 8  | GPIO14 / TXD   | Flight controller UART **RX** |
| Pin 10 | GPIO15 / RXD   | Flight controller UART **TX** |

Tips:
- Disable the Linux serial console (`raspi-config` → Interface Options → Serial → “Login shell? No”, “Serial hardware? Yes”).
- Use twisted-pair wiring for TX/RX to reject noise.
- If the FC runs at 5 V logic, add a level shifter for its TX line.

### 1.3 Power

- Provide a stable 5 V / 2 A BEC for the Pi, capture dongle, and camera.
- Add a 220–470 µF capacitor near the Pi to absorb current spikes.
- Keep Pi USB powered **only** for development; in flight power it from the BEC, not from the FC USB port.

---

## 2. Software Installation

### 2.1 Quick Install (Recommended)

```bash
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization
chmod +x setup.sh
./setup.sh    # Enables camera + UART, installs dependencies
sudo reboot   # Applies camera/UART config
```

### 2.2 Manual Install

```bash
# Base system
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-dev git

# Enable camera + UART
sudo raspi-config    # Interface Options -> Camera (Enable)
sudo raspi-config    # Interface Options -> Serial (login shell = No, hardware = Yes)

# Repository
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization
pip3 install --upgrade pip
pip3 install -r requirements.txt
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py
```

---

## 3. Verification

### 3.1 Camera Check

```bash
# CSI cameras (IMX219 / OV5647)
libcamera-hello --list-cameras

# USB / analog capture
python3 - <<'PY'
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print("Camera OK:", ret, "Shape:", None if frame is None else frame.shape)
cap.release()
PY
```

### 3.2 Python Modules

```bash
python3 -c "import camera_optical_flow, flow_tracker; print('Imports OK')"
```

### 3.3 Dry Run

```bash
./betafly_stabilizer_advanced.py --config config.json --no-web --mode off
# Press Ctrl+C after a few seconds; ensure there are no camera errors in the log.
```

---

## 4. Configuration Basics

Edit `config.json`:

```bash
nano config.json
```

Key fields:

| Field | Purpose |
|-------|---------|
| `sensor.type` | `csi_camera`, `usb_camera`, `analog_usb`, or `opencv_any` |
| `camera.device` | `0`, `/dev/video0`, or `"auto"` |
| `camera.deinterlace` | Set `true` for analog capture dongles |
| `tracker.initial_height` | Hover height in meters for scale |
| `stabilizer.velocity_damping` | 0–1 dampening factor |
| `output` | Interface describing how to talk to the flight controller |

Example for a CSI camera with MAVLink output:

```json
{
  "sensor": { "type": "csi_camera", "rotation": 0 },
  "camera": { "device": 0, "width": 640, "height": 480, "fps": 30 },
  "output": { "interface": "mavlink", "port": "/dev/serial0", "baudrate": 115200 }
}
```

---

## 5. Running the System

### 5.1 Manual Launch

```bash
# Web-enabled advanced controller
./betafly_stabilizer_advanced.py --mode velocity_damping

# CLI-only basic controller
./betafly_stabilizer.py --mode position_hold --log

# Custom config file
./betafly_stabilizer_advanced.py --config my_config.json --mode position_hold
```

Web UI: browse to `http://raspberrypi.local:8080`.

### 5.2 Auto-start (systemd)

```bash
sudo cp betafly-stabilizer.service /etc/systemd/system/
sudo nano /etc/systemd/system/betafly-stabilizer.service  # update ExecStart paths if needed
sudo systemctl daemon-reload
sudo systemctl enable betafly-stabilizer.service
sudo systemctl start betafly-stabilizer.service
sudo systemctl status betafly-stabilizer.service
sudo journalctl -u betafly-stabilizer.service -f
```

---

## 6. Flight Controller Integration

### 6.1 Serial (MAVLink / MSP)

1. Wire Pi TX/RX as described in Section 1.2.
2. Configure UART in Betaflight/iNav/PX4 (disable “serial RX”, set the correct baud rate).
3. Update `config.json`:
   ```json
   "output": {
     "interface": "msp",        // or "mavlink"
     "port": "/dev/serial0",
     "baudrate": 115200
   }
   ```
4. Fill in `_send_corrections` in `betafly_stabilizer(_advanced).py` with the packets your FC expects.

### 6.2 PWM Override (advanced users)

If you prefer PWM injection, set `"interface": "pwm"` and implement the GPIO output logic with `pigpio`. This method requires buffering and is recommended only for testing.

---

## 7. Initial Testing

1. **Bench Test (props off)**  
   ```bash
   ./betafly_stabilizer_advanced.py --mode velocity_damping --log
   ```  
   Move the airframe by hand and confirm the web UI shows motion and increasing surface quality.

2. **Hover in Manual**  
   Take off in manual mode, hover ~0.5 m above textured ground, then enable velocity damping. Verify drift slows down.

3. **Position Hold**  
   Switch to `position_hold`. Release sticks slowly and observe the controller correcting drift. Abort immediately if oscillations appear.

Checklist before flight:
- [ ] Camera stream stable, no dropped frames
- [ ] Surface below has texture (mat, carpet, asphalt)
- [ ] Pi temperature <70 °C
- [ ] Manual override switch configured

---

## 8. Troubleshooting

| Issue | Fix |
|-------|-----|
| Camera not detected | Re-seat CSI ribbon, run `libcamera-hello`, check `/boot/config.txt` for `start_x=1`, verify USB capture shows up via `lsusb`. |
| No UART data | Ensure `console=serial0,115200` is removed from `/boot/cmdline.txt`, confirm wiring (TX→RX, RX→TX), match baud rate. |
| Analog video noisy | Shorten video lead, enable `camera.deinterlace`, power camera from clean 5 V, ground the shield. |
| Low surface quality | Improve lighting, add textured landing pad, raise hover height, clean camera lens. |
| Loop too slow | Reduce `camera.width`/`height`, lower `control.update_rate_hz`, disable logging, or upgrade to Pi Zero 2 W. |

---

## 9. Performance Tips

**Pi Zero W**
- 30–40 Hz loop, 320×240 camera resolution, Farneback method.
- Disable logging once tuning is done.
- Consider `arm_freq=1000`, `over_voltage=2` in `/boot/config.txt` (cooling recommended).

**Pi Zero 2 W**
- 60–100 Hz loop possible at 640×480.
- Can run web UI, logging, and stick mixing simultaneously.

---

## 10. Next Steps

1. ✅ Camera + UART wired
2. ✅ `setup.sh` completed without errors
3. ✅ Camera verified via `libcamera-hello` / OpenCV script
4. ✅ Stabilizer runs on bench
5. 🔜 Tune PID and velocity damping (see README)
6. 🔜 Finish `_send_corrections` for your flight controller
7. 🔜 Conduct tethered/low-altitude flight tests

---

## Support & Safety

- Refer to [README.md](README.md) for architecture, tuning, and wiring diagrams.
- File GitHub issues with logs, config, and a short description of your camera/FC setup.
- Always fly in a safe environment with a manual override ready and props removed during bench tests.
