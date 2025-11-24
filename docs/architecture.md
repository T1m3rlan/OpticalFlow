## Optical Position Stabilizer — Architecture

### Goals
- Hold a hover position for a Betaflight-based vehicle by closing a slow optical loop on a Raspberry Pi Zero.
- Run on the Pi Zero without GPU; prefer integer math and small frames.
- Keep Betaflight unaware of the loop: corrections are injected as RC commands via MSP.

### Main Components
1. **Sensor Stage (`camera.py`)**
   - Wraps `picamera`/`libcamera` capture at 160×120 or 320×240.
   - Provides grayscale frames with a steady cadence (~30 Hz) and exposes a `FrameGenerator`.

2. **Perception Stage (`optical_flow.py`)**
   - Uses pyramidal Lucas–Kanade on `N` strongest Shi–Tomasi corners.
   - Rejects tracks with large residuals and produces a planar velocity vector in m/s via configurable scaling.

3. **Filter Stage (`filters.py`)**
   - Exponentially weighted moving average plus deadband to suppress noise.
   - Optional median window before PID to fight outliers.

4. **Control Stage (`pid.py`, `stabilizer.py`)**
   - Separable PID per axis (X/Y) with integral windup clamping.
   - Timing derived from frame timestamps to keep gains hardware-agnostic.

5. **Actuation Stage (`msp.py`)**
   - Minimal MSP v2 client that can send `MSP_SET_RAW_RC` over UART.
   - Applies trim offsets on roll/pitch channels while respecting RC min/max.

6. **CLI / Service (`cli.py`)**
   - Loads YAML config, spawns camera + stabilizer runner, publishes telemetry (stdout or UDP).
   - Supports dry-run mode for on-host testing with prerecorded video.

### Data Flow
```
Camera → Optical Flow → Filters → PID Controller → MSP RC Overrides
```

### Threading Model
- Camera and optical flow run in the main async loop using `asyncio` tasks.
- MSP writes are coalesced to ≤50 Hz to avoid overwhelming the FCU.
- Clean shutdown via signals; each stage exposes `start()/stop()` hooks.

### Configuration
- YAML file defines:
  - Camera settings (resolution, FPS, exposure).
  - Optical flow parameters (features, quality, pixel-to-meter scale).
  - PID gains / integrator clamps.
  - MSP port/baud and RC channel mapping.
  - Safety constraints (max correction, arming guard).

### Telemetry & Logging
- Rolling CSV or JSON lines with:
  - Timestamp, flow vector, filtered vector, PID outputs, RC commands.
- Optional UDP publisher to ground station for tuning.

### Safety Considerations
- Automatic decay to zero corrections when flow confidence < threshold.
- Guard-n-frames before enabling corrections during takeoff.
- Failsafe if UART/MPS errors exceed limit or frame rate drops.

### Extensibility
- Swappable perception backends (e.g., ArUco markers) via strategy pattern.
- Room to feed IMU data later for sensor fusion without API changes.

### Resource Budget (Pi Zero)
- CPU: target ≤70% single-core.
- Memory: <120 MB RSS.
- Latency: <80 ms from frame capture to RC command.
