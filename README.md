# Betafly Optical Position Stabilizer

Optical-flow-based position hold loop for Betaflight quads using a Raspberry Pi Zero and a downward-facing Pi Camera. The Pi computes lateral drift and injects corrective trims over MSP so the flight controller keeps hovering above the same point indoors or in GPS-denied spaces.

## Highlights
- Sparse Lucas–Kanade optical flow optimized for Pi Zero (160×120 @ 30 Hz).
- Decoupled roll/pitch PID controllers with wind-up protection and RC clamp.
- MSP v1 `MSP_SET_RAW_RC` output—no FC firmware changes required.
- Dry-run mode that uses prerecorded video files for tuning on a laptop.
- CSV telemetry for later plotting plus YAML configuration for every subsystem.

## Hardware & Wiring
- Raspberry Pi Zero 2 W (Zero W works with lower headroom).
- Pi Camera v2/v3 pointed straight down, lens protected from props.
- GPIO UART (pins 8/10) wired to a spare Betaflight UART set to MSP @ 115200 baud.
- Common ground between Pi and FC, 5 V BEC ≥1 A, and a short USB cable or Wi-Fi for shell access.

### Betaflight Checklist
1. Enable MSP on the selected UART in the Ports tab.
2. Confirm channel order (AETR by default) so roll/pitch indexes are correct.
3. Set RC deadband ≤5 and enable RC smoothing for trims to matter.
4. Fly in Angle/Horizon—the Pi simply “moves the sticks”.

## Software Setup
```bash
sudo apt update
sudo apt install python3-pip python3-opencv python3-venv
git clone https://example.com/betafly-optical.git
cd betafly-optical
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Copy and edit the config:
```bash
cp config/default.yaml betafly.yaml
nano betafly.yaml
```

Dry-run on the bench first:
```bash
betafly-stabilizer -c betafly.yaml --dry-run --log-level DEBUG
```

Remove `--dry-run` only after verifying telemetry and MSP wiring.

## Config Primer
See `config/default.yaml` for documented defaults:
- `camera`: resolution/FPS and `video_source` (e.g. `file:/home/pi/logs/run.mp4`).
- `flow`: number of corners, quality level, pixel → meter scale, confidence gate.
- `filter`: median window, EMA alpha, and deadband to suppress jitter.
- `pid`: per-axis gains, integrator clamp, and output limit (fraction of RC trim).
- `msp`: UART path, baud, RC min/mid/max, command rate, and maximum trim in µs.
- `telemetry_path`: path for CSV logs (set `null` to disable).
- `dry_run`: bypass MSP writes (handy for laptop debugging).

Architecture details live in `docs/architecture.md`.

## Calibration & Tuning Workflow
1. **Pixel scale** – Hover manually, walk the quad 0.5 m in each axis while logging, then fit `pixel_to_meter`.
2. **Guard period** – Adjust `flow.guard_frames` so the loop waits ~1 s after arming before sending trims.
3. **PID sweep** – Increase `kp` until mild oscillation, drop 20%, then add `ki` for bias rejection and `kd` for gusts.
4. **Max trim** – Keep `msp.max_trim` below what you are comfortable overriding (60–100 µs for micro quads).
5. **Telemetry** – Plot `vx/vy` vs. `roll_cmd/pitch_cmd` to confirm sign conventions before real flights.

## Safety Notes
- Keep a finger on the arming switch; optical tracking can fail in low light or texture-less floors.
- Enable Betaflight stick overlay in OSD to see injected trims in real time.
- Run on a tether the first time; never rely on the Pi alone for failsafe.

## Repo Layout
- `src/betafly_stabilizer/`: camera, flow, filters, PID, MSP, and CLI modules.
- `config/default.yaml`: reference configuration.
- `docs/architecture.md`: design goals, threading, and safety considerations.
- `tests/`: unit tests for PID and filters.

## License
MIT — use at your own risk. Multirotors can injure people and property.
