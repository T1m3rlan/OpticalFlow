import cv2
import time
import config
from optical_flow import OpticalFlowSensor
from flight_controller import FlightController
from pid_controller import PIDController

def main():
    print("Initializing Optical Flow Sensor...")
    flow_sensor = OpticalFlowSensor()
    
    print("Initializing Flight Controller Connection...")
    fc = FlightController()
    
    # PID Controllers for Velocity
    # We try to keep flow (velocity) at 0
    pid_roll = PIDController(config.P_GAIN, config.I_GAIN, config.D_GAIN, setpoint=0)
    pid_pitch = PIDController(config.P_GAIN, config.I_GAIN, config.D_GAIN, setpoint=0)
    
    print("Starting stabilization loop. Enable AUX1 to activate.")
    
    try:
        while True:
            loop_start = time.time()
            
            # 1. Read Flow
            dx, dy = flow_sensor.read_flow()
            
            # 2. Read current RC from FC
            rc_channels = fc.get_rc()
            
            if rc_channels:
                # rc_channels: [Roll, Pitch, Throttle, Yaw, Aux1, Aux2, ...]
                # Map channels based on standard Betaflight map (AETR1234 or TAER1234)
                # Assuming standard order from MSP: Roll, Pitch, Throttle, Yaw, Aux1...
                current_roll = rc_channels[0]
                current_pitch = rc_channels[1]
                throttle = rc_channels[2]
                yaw = rc_channels[3]
                aux1 = rc_channels[4]
                aux2 = rc_channels[5]
                aux3 = rc_channels[6] if len(rc_channels) > 6 else 1000
                aux4 = rc_channels[7] if len(rc_channels) > 7 else 1000

                # 3. Check if stabilization enabled (Assume AUX1 High > 1700)
                if aux1 > 1700:
                    # Calculate PID outputs based on flow
                    # Flow is in pixels per frame. 
                    
                    roll_output = pid_roll.update(dx)
                    pitch_output = pid_pitch.update(dy)
                    
                    # logic:
                    # dx < 0 (Image moves Left) => Drone moved Right.
                    # Correction: Roll Left (< 1500).
                    # pid_roll.update(dx) => Error = 0 - (-val) = +val. Output > 0.
                    # We want result < 1500. So: 1500 - Output.
                    
                    # dy > 0 (Image moves Down) => Drone moved Forward.
                    # Correction: Pitch Back (< 1500).
                    # pid_pitch.update(dy) => Error = 0 - (+val) = -val. Output < 0.
                    # We want result < 1500. So: 1500 + Output.
                    
                    # Apply correction to center (1500)
                    # We could also apply it to current_roll/pitch if we want "Assist" mode
                    # But for "Stabilization", we usually want it to hold hover when stick is centered.
                    # Let's assume Pilot wants to hover when AUX1 is ON.
                    # We can add stick input to this if we want pilot to be able to move it.
                    # new_roll = 1500 + (current_roll - 1500) - roll_output
                    
                    pilot_roll_input = current_roll - 1500
                    pilot_pitch_input = current_pitch - 1500
                    
                    # If pilot is giving input, maybe we reduce stabilization or just add it.
                    # Simple addition:
                    new_roll = 1500 + pilot_roll_input - roll_output
                    new_pitch = 1500 + pilot_pitch_input + pitch_output
                    
                    # Send new RC
                    fc.set_rc(new_roll, new_pitch, throttle, yaw, aux1, aux2, aux3, aux4)
                    
                    # print(f"Flow: ({dx:.1f}, {dy:.1f}) -> Out: ({roll_output:.1f}, {pitch_output:.1f}) -> RC: {int(new_roll)}, {int(new_pitch)}")
                    
                else:
                    # If not enabled, we do NOT send RC commands, letting the RX control the drone directly.
                    # However, if we were sending commands, we should stop or send "released" commands.
                    # MSP_SET_RAW_RC times out after a short period (e.g. 1s) if not refreshed.
                    # So doing nothing here is fine, the FC will revert to RX.
                    
                    # Reset PIDs to avoid integrator windup while disabled
                    pid_roll.reset()
                    pid_pitch.reset()
                    pass

            # Control loop rate
            elapsed = time.time() - loop_start
            if elapsed < 0.01: # Cap at ~100Hz
                time.sleep(0.01 - elapsed)
            
    except KeyboardInterrupt:
        print("Stopping...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        flow_sensor.close()
        fc.close()

if __name__ == "__main__":
    main()
