## Calibration & Tuning Guide

Follow these steps before letting the Betafly stabilizer actuate the payload in free space.

### 1. Servo Neutral & Travel
1. Disconnect the gimbal linkages from the payload so the servos can move freely.
2. Run `python -m betafly_stabilizer --simulate-actuators --preview` to verify camera framing.
3. Edit `config/betafly_default.yaml` so that `simulate` is `false` for both actuators.
4. Start `python -m betafly_stabilizer --preview --duration 20`.
5. Use a ruler or angle gauge to record the tilt/pan angle when the servos settle.
6. Adjust `neutral_pulse_us` until the gimbal is level. Record the max/min pulses where the linkage just hits its mechanical limit and set `min_pulse_us` / `max_pulse_us` accordingly.

### 2. ROI Selection
1. Enable preview and press the Betafly target under typical lighting.
2. Update the `tracker.roi` rectangle to cover only high-contrast details (avoid horizons or blades).
3. Keep the ROI smaller than the full frame to reduce CPU load on the Pi Zero.

### 3. PID Gains
1. Start with low values (`kp≈0.05`, `ki=0`, `kd=0`).
2. Increase `kp` until the system corrects disturbances without oscillation, then add a small `kd` to damp overshoot.
3. Introduce `ki` to remove steady-state error (e.g., from servo bias). Keep `integrator_limit` low to avoid wind-up.
4. Observe telemetry logs (`--log tune.csv`) in a spreadsheet. Aim for critically damped responses (single overshoot at most).

### 4. Rate Limiting & Deadband
- If the gimbal vibrates, increase `rate_limit_us` so the servo can't move faster than its mechanics.
- If the tracker noise causes jitter near zero, widen the PID `deadband` until the jitter disappears without hurting tracking accuracy.

### 5. Final Verification
1. Disable preview to save CPU on the Pi Zero.
2. Run the stabilizer for several minutes while applying manual disturbances to the payload.
3. Confirm the telemetry log has no long saturation periods (outputs pegged at ±0.8). If it does, increase servo travel or retune gains.

### Optional: Manual Stick Trim
1. Enable the joystick fusion layer in `manual_input.enabled`.
2. Move each stick to its extremes while watching the telemetry log (`manual_roll`, `manual_pitch`). The values should reach the configured `scale` but return to 0 within the failsafe timeout once released.
3. Increase `manual_input.deadband` if residual noise causes the setpoint to drift when hands off.
