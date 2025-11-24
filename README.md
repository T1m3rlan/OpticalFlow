# Betafly Optical Stabilization with Raspberry Pi Zero

This project implements optical flow-based position stabilization for a drone (Betafly/Betaflight) using a Raspberry Pi Zero and a camera.

## Features
- **Optical Flow Stabilization**: Uses Lucas-Kanade optical flow to detect drift and correct it.
- **Web Interface**: Adjust PID gains, camera settings, and view status via a mobile-friendly web UI.
- **Multi-Camera Support**: Supports USB webcams and Raspberry Pi cameras via index or device path.
- **Fly PosHold**: Allows manual stick input while maintaining stabilization (drifts are fought, pilot input is respected).

## Hardware Requirements
- Raspberry Pi Zero (or similar)
- Camera (CSI Pi Camera or USB Webcam)
- Flight Controller (Betaflight compatible)
- Connection between Pi UART and FC UART

## Software Requirements
- Python 3
- OpenCV
- NumPy
- PySerial
- Flask

## Installation
```bash
pip install -r requirements.txt
```

## Usage
Run the stabilization script (which also starts the web server):
```bash
python3 stabilize.py
```

## Web Interface
Open a browser and navigate to:
`http://<PI_IP_ADDRESS>:5000`

Here you can:
- Change **Serial Port** and **Baud Rate**.
- Select **Camera Index** (0, 1, etc) or path (`/dev/video0`).
- Tune **PID Gains** live.
- Adjust **Velocity Scale** (how much pilot input overrides stabilization).

## Configuration
Settings are saved to `settings.json`.
- **Stabilization Activation**: Enable AUX1 (> 1700) on your transmitter.
- **Manual Control**: Moving sticks away from center will override the hold, allowing you to fly around. Centering sticks will re-engage position hold (velocity damping).

## Troubleshooting
- **Camera Error**: Ensure legacy camera support is enabled if using a Pi Camera (`raspi-config`).
- **Web UI Not Loading**: Check if port 5000 is open and you are using the correct IP.
