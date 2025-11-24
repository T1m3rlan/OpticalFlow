## Betafly Optical Position Stabilizer

The Betafly optical stabilizer is a lightweight vision-and-control stack designed to keep a payload (camera, laser, or sensor) centered on a visual target while running on a Raspberry Pi Zero. It combines an OpenCV-based optical flow tracker with a tunable PID control loop that drives a two-axis servo gimbal.

### Key Capabilities
- Runs on Raspberry Pi Zero (Bullseye/Bookworm) with CSI or USB cameras.
- Uses feature-based optical flow to estimate horizontal and vertical drift in real time.
- Provides PID-based servo commands with optional deadband and output limiting for fragile gimbals.
- Exposes a CLI to load YAML configs, visualize debug overlays, and log telemetry for offline tuning.
- Includes modular abstractions for camera capture, feature tracking, controllers, and actuators, making it easy to extend to other payloads or sensors.

### Repository Layout
- `betafly_stabilizer/`: Python package with the runtime components.
- `config/`: Example YAML configuration (camera, tracker, controllers, hardware pins).
- `docs/`: Additional documentation (architecture, calibration, tuning notes).
- `tests/`: Lightweight unit tests for control primitives.

### Hardware Requirements
- Raspberry Pi Zero / Zero 2 W (Bullseye or newer) with Python 3.9+.
- Camera (Raspberry Pi Camera Module v2 or UVC USB webcam).
- Two-axis micro servo gimbal (e.g., SG90 pair) or Betafly platform-specific actuators.
- Optional: IMU for future fusion, active cooling fan to keep Pi Zero stable.

### Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m betafly_stabilizer run --config config/betafly_default.yaml --preview
```

Add `--log telemetry.csv` to export raw drift/error samples for later tuning. Use `--camera-source analog --analog-profile pal_longbow` to switch between composite inputs on the fly.

### Local Web UI
- Launch the settings GUI: `python -m betafly_stabilizer webui --config config/betafly_default.yaml --host 0.0.0.0 --port 8080`.
- The dashboard provides quick sliders for camera resolution, PID gains, manual-input scaling, and preview toggles.
- Use the “Raw YAML editor” link to edit the full configuration without leaving the browser.
- All edits are validated with PyYAML before being saved back to disk.

### Deployment Notes
- Enable camera support on the Pi via `raspi-config` and ensure the GPU memory split is at least 128 MB.
- When using the CSI camera, set `use_picamera: true` in the config for lower capture latency.
- On Pi Zero, keep the resolution at or below 640×480@30 fps unless hardware acceleration is available.
- Calibrate servos so that `neutral_pulse_us` keeps the Betafly payload level. Update `config/betafly_default.yaml` with the calibration results.

### Wiring Overview
- GPIO 18 → Pan servo signal (with 5 V supply shared ground).
- GPIO 19 → Tilt servo signal.
- Power the servos from a dedicated 5 V BEC; never from the Pi’s 5 V rail.
- Tie all grounds together (Pi, servo BEC, any IMUs) to avoid control jitter.
- Optional debug LED on GPIO 26 to show lock state (add via future actuator hook).

### Analog Camera Profiles
- `camera.source` controls which backend runs (`opencv`, `picamera`, or `analog`).
- Define multiple composite capture profiles under `camera.analog_profiles` to switch between PAL/NTSC digitizers or inputs.
- Select a profile at runtime with `--analog-profile profile_name` or through the web UI.
- Horizontal/vertical flips are available for upside-down wiring harnesses.

### Manual Stick PosHold
- Enable the joystick/RC fusion layer with `manual_input.enabled: true` (or `--manual-input` CLI flag).
- Defaults expect an HID gamepad exposed as `/dev/input/js0`; override with `manual_input.device`.
- Stick offsets are normalized, filtered with a deadband, and subtracted from the optical error so you can “nudge” the Betafly while it maintains position hold.
- Telemetry logs now include `manual_roll`/`manual_pitch` columns for backtesting stick authority.

See `docs/architecture.md` for a deeper dive into the modules and data flow, and `docs/calibration.md` for step-by-step tuning guidance.
