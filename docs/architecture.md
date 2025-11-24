## Architecture Overview

The Betafly stabilizer is split into four cooperating subsystems that exchange small, well-defined data structures to keep the Raspberry Pi Zero workload predictable and debuggable.

### 1. Capture Subsystem (`camera.CameraStream`)
- Handles the physical camera interface (USB UVC or CSI via `picamera`).
- Converts frames to grayscale `numpy` arrays and enforces a fixed resolution/framerate for deterministic latency.
- Maintains rolling timestamps so the control loop can compute velocities if needed.
- Exposes `read()` to return the latest frame and capture metadata; optionally writes frames to a ring buffer for preview mode.

### 2. Vision Tracker (`tracker.OpticalFlowTracker`)
- Initializes with up to N good features (Shi-Tomasi corners) inside a region-of-interest mask.
- Uses pyramidal Lucas–Kanade optical flow to track feature motion frame-to-frame without re-detecting on every iteration.
- Rejects features with low tracking confidence or that leave the ROI, and triggers re-seeding when too many points are lost.
- Outputs the median pixel translation `(dx, dy)` plus quality metrics so the controller can adapt gains or drop updates when the scene is unreliable.

### 3. Control Loop (`controller.PositionController`)
- Wraps two `PIDController` instances (pan and tilt) that operate on the tracker’s error.
- Adds deadband, integral wind-up clamping, derivative filtering, and actuator saturation awareness.
- Produces normalized servo demand values in the range `[-1.0, 1.0]`, which map directly onto pulse widths through the actuator layer.

### 4. Actuator Layer (`actuators.ServoActuator` & `GimbalActuator`)
- Uses `RPi.GPIO` or `pigpio` to generate PWM pulses on configurable pins.
- Supports per-axis neutral pulse, min/max bounds, and rate limiting to protect fragile linkages.
- Can be swapped for simulated actuators during desktop testing so the rest of the stack can run without hardware.

### Execution Model (`stabilizer.OpticalPositionStabilizer`)
1. Camera delivers a frame.
2. Tracker produces drift estimates and confidence scores.
3. Controller updates PID states and asks the actuator layer to move.
4. Optional debug overlay is generated and displayed/logged.
5. Loop sleeps just enough to respect the configured control frequency.

Telemetry (timestamp, dx/dy, PID terms, servo outputs, quality) is streamed via CSV logging for offline analysis. The CLI can also emit a ZeroMQ stream for remote dashboards if needed.

### Calibration & Tuning Flow
1. Run `python -m betafly_stabilizer --preview --log calibration.csv`.
2. Physically lock the Betafly payload and capture baseline servo neutral offsets.
3. Tune PID gains starting with low proportional values until the system can correct small disturbances without oscillation.
4. Adjust feature count/ROI to focus on high-contrast sections of the target.

Future work may add IMU fusion, GPU-accelerated feature detection (e.g., ORB on Pi Zero 2 W), or a TinyML detector for marker-based tracking. The modular package layout ensures these upgrades only require swapping the relevant subsystem.
