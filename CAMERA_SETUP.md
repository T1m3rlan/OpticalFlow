# Camera Setup & Wiring Guide

This guide covers how to set up cameras for the Betafly Optical Stabilization System and how to connect the Raspberry Pi Zero to your Flight Controller.

## 1. Camera Options

The system supports multiple camera types for optical flow calculation:

### A. Raspberry Pi Camera (CSI) - Recommended
Compatible sensors: **IMX219**, **OV5647** (Pi Camera V2, V1, or compatible ZeroCam modules).

**Wiring:**
1. Locate the CSI camera connector on the Raspberry Pi Zero (the smaller one on the side).
2. **Important:** You need a specific camera cable for the Pi Zero (the one with a smaller end). Standard Pi camera cables won't fit.
3. Insert the cable with the metal contacts facing **towards the board** (away from the edge connector clip).
4. Connect the other end to the camera module.

### B. USB Camera
Any standard UVC-compatible USB webcam.
- Plug directly into the Pi Zero via USB OTG adapter.

### C. Analog Camera (via USB Capture)
Use an existing FPV analog camera with a USB capture card (EasyCAP or similar UVC digitizer).

**Wiring:**
1. Connect the Analog Camera's Video Signal wire (usually yellow) to the Video Input of the USB Capture Card.
2. Connect Ground to Ground.
3. Plug the USB Capture Card into the Pi Zero via USB OTG adapter.

## 2. Flight Controller Wiring

To send position corrections to the Flight Controller (FC), you need to connect the Raspberry Pi Zero's UART (Serial) port to a spare UART on the FC.

### Pinout (Raspberry Pi Zero)

| Pin # | GPIO | Function | Connect to FC |
|-------|------|----------|---------------|
| 4     | -    | 5V       | 5V (Power)    |
| 6     | -    | GND      | GND           |
| 8     | 14   | TXD0     | **RX**        |
| 10    | 15   | RXD0     | **TX**        |

### Wiring Diagram

```
[Raspberry Pi Zero]                   [Flight Controller]
      Pin 4 (5V)   --------------------   5V
      Pin 6 (GND)  --------------------   GND
      Pin 8 (TX)   --------------------   RX (e.g., UART2 RX)
      Pin 10 (RX)  --------------------   TX (e.g., UART2 TX)
```

**Notes:**
- **Power:** You can power the Pi Zero from the FC's 5V BEC if it provides enough current (at least 1-1.5A recommended).
- **Cross-over:** Remember to connect TX to RX and RX to TX.
- **Logic Level:** Pi Zero uses 3.3V logic. Most modern FCs (STM32) are 3.3V tolerant or use 3.3V logic, but check your FC manual.

## 3. Software Configuration

### Enable Camera
Run `sudo raspi-config`, navigate to **Interface Options**, and enable **Legacy Camera** (for Bullseye) or **Camera** (for Bookworm).
Or add `start_x=1` and `gpu_mem=128` to `/boot/config.txt`.

### Flight Controller Setup (Betaflight/INAV)
1. Open Betaflight Configurator.
2. Go to **Ports** tab.
3. Find the UART connected to the Pi (e.g., UART2).
4. Enable **MSP** (if using MSP protocol) or select **MAVLink** in the Peripherals column (if using MAVLink).
5. Set Baud Rate to **115200** (must match `config.json`).
6. Save and Reboot.

### Verification
Run the advanced stabilizer script to check if the camera is detected:
```bash
./betafly_stabilizer_advanced.py --verbose
```
Watch the logs for "Camera initialized" messages.
