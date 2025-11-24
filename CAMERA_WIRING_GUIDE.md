# Camera & Flight Controller Wiring Guide

This note collects the practical wiring tips for running Betafly with Raspberry Pi cameras (IMX219/OV5647) or analog FPV cameras, plus the serial link between the Pi Zero and your flight controller.

---

## 1. Raspberry Pi CSI Cameras (IMX219 / OV5647)

```
IMX219 / OV5647  === FFC Ribbon ===  Raspberry Pi Zero (CAM0)
┌──────────────┐                      ┌────────────────────┐
│  Camera PCB  │=====================>│  CAM0 connector     │
└──────────────┘                      └────────────────────┘
```

1. Open the CAM0 latch on the Pi Zero, insert the ribbon with the **exposed contacts facing the HDMI connector**, then push the latch back down evenly.
2. Keep the cable slack-free but not under tension. Add a small piece of Kapton or tape to lock it in place for vibrations.
3. Angle the module so the lens points straight down. Soft foam tape or a TPU mount helps absorb vibrations.

| Pin | Signal | Notes |
|-----|--------|-------|
| Pin 1 | GND | Some third-party boards break this out; official modules draw ground through the ribbon. |
| Pin 17 | 3V3 | Only needed for DIY camera boards; official CSI modules pull power via the ribbon. |
| All others | Data / clock | Not user-accessible—handled internally by the ribbon. |

**Quick checks**
- `libcamera-hello -t 3000` should show a preview.
- If you see a black screen, re-seat the ribbon (contacts flipped is the #1 culprit).

---

## 2. Analog FPV Cameras via USB Capture

```
Analog Cam (+5V/GND/Video) -> UVC Capture Stick -> Pi Zero (USB OTG)
```

| Analog Wire | Connect To | Notes |
|-------------|------------|-------|
| +5 V (red)  | 5 V BEC output | Use the same regulator that powers the Pi for fewer ground loops. |
| GND (black) | Pi GND / BEC GND | Tie all grounds together (Pi, camera, FC). |
| Video (yellow) | UVC capture stick input | Mini‑JST or RCA depending on the dongle. |

Recommended capture sticks: EasyCAP DC60 (UVC variant), Elgato CamLink, or any `uvcvideo`-compatible dongle.

Testing:
```bash
ls /dev/video*
v4l2-ctl --list-devices
python3 test_sensor.py --type analog_usb --device /dev/video0
```

Leave `camera.deinterlace` enabled inside `config.json` to clean up interlaced NTSC/PAL frames.

---

## 3. USB Webcams

Simply plug the webcam into the Pi (or a powered hub) and set:

```json
"camera": {
  "type": "usb_camera",
  "device": 0,
  "width": 640,
  "height": 480,
  "fps": 30
}
```

Use `v4l2-ctl --list-devices` to find the correct `/dev/video` index.

---

## 4. Raspberry Pi Zero ↔ Flight Controller UART

Betafly expects to push roll/pitch corrections over the Pi’s primary UART (`/dev/ttyAMA0`). Wire it like this:

```
Pi Zero (Top View)                         Flight Controller UART
┌──────────────────────────────┐          ┌──────────────────────┐
│ Pin 8  (GPIO14 / TXD0)  ----┼─────────▶│ RX (UART n)           │
│ Pin 10 (GPIO15 / RXD0)  ◀---┼──────────│ TX (UART n)           │
│ Pin 6  (GND)             ----┴─────────│ GND                   │
└──────────────────────────────┘          └──────────────────────┘
```

| Pi Pin | Signal | Connects To | Purpose |
|--------|--------|-------------|---------|
| Pin 8  | TX (3.3 V) | Flight controller **RX** | Carries Betafly’s correction commands (MAVLink, MSP, etc.). |
| Pin 10 | RX (3.3 V) | Flight controller **TX** | Optional telemetry or ACKs. |
| Pin 6  | GND        | Flight controller GND     | Required reference. |

**Serial prep**
1. `sudo raspi-config` → Interface Options → Serial → **No** login shell, **Yes** hardware serial.
2. Set `"output": {"interface": "mavlink", "port": "/dev/ttyAMA0", "baudrate": 115200}` (or `"msp"`).
3. Match the baudrate on the FC side (Betaflight CLI: `set serialrx_baudrate = 115200` / `save`).

---

## 5. Power & Ground Best Practices
- Feed the Pi from a 5 V BEC capable of ≥1 A continuous.
- Share ground between the Pi, capture stick, flight controller, receiver, and camera.
- Add a bulk capacitor (220–470 µF) close to the Pi to smooth battery sag during punches.
- If you power the Pi from USB for bench tests, keep the FC unplugged or power it via USB as well to avoid floating grounds.

---

Keep this sheet handy while building—the combination of the CSI ribbon orientation, analog capture wiring, and UART routing covers 95% of “why isn’t it working?” moments.
