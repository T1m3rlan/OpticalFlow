# Betafly Optical Stabilization with Raspberry Pi Zero

This project implements optical flow-based position stabilization for a drone (Betafly/Betaflight) using a Raspberry Pi Zero and a camera.

## Hardware Requirements
- Raspberry Pi Zero (or similar)
- Raspberry Pi Camera Module
- Flight Controller (Betaflight compatible)
- Connection between Pi UART (TX/RX) and FC UART (RX/TX)

## Software Requirements
- Python 3
- OpenCV
- NumPy
- PySerial

## Installation
1. Install system dependencies (if needed):
   ```bash
   sudo apt-get update
   sudo apt-get install python3-opencv libopencv-dev python3-numpy python3-serial
   ```
   *Note: Installing via apt is often faster/easier on Pi than pip for OpenCV.*

2. Or install via pip:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
1. **Raspberry Pi Config**:
   - Enable Camera (Legacy interface might be required for OpenCV `VideoCapture(0)`).
   - Enable Serial Port (Hardware UART), disable Serial Console.
     - `sudo raspi-config` -> Interface Options -> Serial Port -> Login Shell: No -> Hardware: Yes.

2. **Flight Controller Config (Betaflight)**:
   - Enable MSP on the UART port connected to the Pi.
   - Ensure Receiver Mode is correct. This script uses `MSP_SET_RAW_RC` which overrides receiver channels.
   - Configure AUX1 switch on your transmitter.
     - Channel 5 (AUX1) > 1700 enables stabilization.
     - Ensure you can toggle this safely.

3. **Project Config**:
   - Edit `config.py` to adjust:
     - `SERIAL_PORT`: Default `/dev/ttyS0` (Pi Zero UART).
     - `P_GAIN`, `I_GAIN`, `D_GAIN`: PID tuning.
     - Camera settings.

## Usage
Run the stabilization script:
```bash
python3 stabilize.py
```

1. Power on drone and RC.
2. Start the script.
3. Take off and establish a stable hover manually.
4. Flip AUX1 to enable stabilization.
   - The drone should resist drifting.
   - You can still nudge it with sticks (Pilot input is added).
5. Flip AUX1 off to regain full manual control.

## Troubleshooting
- **Camera Error**: Check `cv2.VideoCapture(0)`. Ensure camera is connected and legacy mode is enabled if using Bullseye/Bookworm (`sudo raspi-config` -> Interface Options -> Legacy Camera).
- **No Serial**: Check wiring (TX->RX, RX->TX) and Baud Rate (default 115200).
- **Drift**: Adjust PID gains in `config.py`. Ensure camera orientation is correct (X/Y axes matching Roll/Pitch).
