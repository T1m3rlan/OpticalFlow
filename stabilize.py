import cv2
import time
import threading
from optical_flow import OpticalFlowSensor
from flight_controller import FlightController
from pid_controller import PIDController
from settings_manager import SettingsManager
from web_ui import start_web_server

def main():
    # 1. Initialize Settings
    settings_manager = SettingsManager()
    
    # 2. Start Web UI in a separate thread
    print("Starting Web UI on port 5000...")
    web_thread = threading.Thread(target=start_web_server, args=(5000,), daemon=True)
    web_thread.start()

    print("Initializing Optical Flow Sensor...")
    # Pass settings manager to sensor so it can reload/use correct camera
    flow_sensor = OpticalFlowSensor(settings_manager)
    
    print("Initializing Flight Controller Connection...")
    # Note: FlightController currently uses config.py constants. 
    # Ideally, refactor FlightController to use SettingsManager too, 
    # or just rely on restart for Serial changes since they are rare.
    fc = FlightController()
    
    # PID Controllers for Velocity
    # Initialize with values from settings
    p_gain = settings_manager.get("p_gain", 0.1)
    i_gain = settings_manager.get("i_gain", 0.0)
    d_gain = settings_manager.get("d_gain", 0.01)
    
    pid_roll = PIDController(p_gain, i_gain, d_gain, setpoint=0)
    pid_pitch = PIDController(p_gain, i_gain, d_gain, setpoint=0)
    
    print("Starting stabilization loop. Enable AUX1 to activate.")
    
    last_settings_check = time.time()
    
    try:
        while True:
            loop_start = time.time()
            
            # Periodic settings reload (e.g., every 1s) to update PID gains live
            if time.time() - last_settings_check > 1.0:
                pid_roll.kp = settings_manager.get("p_gain", 0.1)
                pid_roll.ki = settings_manager.get("i_gain", 0.0)
                pid_roll.kd = settings_manager.get("d_gain", 0.01)
                
                pid_pitch.kp = settings_manager.get("p_gain", 0.1)
                pid_pitch.ki = settings_manager.get("i_gain", 0.0)
                pid_pitch.kd = settings_manager.get("d_gain", 0.01)
                
                # Check if camera settings changed significantly? 
                # Re-init camera is heavy, maybe require restart for that.
                last_settings_check = time.time()
            
            # 1. Read Flow
            dx, dy = flow_sensor.read_flow()
            
            # 2. Read current RC from FC
            rc_channels = fc.get_rc()
            
            if rc_channels:
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
                    roll_output = pid_roll.update(dx)
                    pitch_output = pid_pitch.update(dy)
                    
                    # Manual Stick Logic ("Fly PosHold")
                    # If pilot moves stick, we shift the setpoint (effectively) or add to output.
                    # Here we translate stick input into a "velocity request" if we were doing cascaded PID.
                    # But since we are doing simple Velocity Dampening:
                    # Stick Input tells the drone to tilt, which creates velocity.
                    # Flow Sensor sees velocity and tries to fight it.
                    # So we must Feed-Forward the stick input OR subtract stick from flow Error.
                    
                    # Simple approach: Additive Control (Fight the drift, but allow pilot override)
                    rc_mid = settings_manager.get("rc_mid", 1500)
                    deadband = settings_manager.get("rc_deadband", 20)
                    vel_scale = settings_manager.get("vel_scale", 0.1) # How much stick overrides stabilization

                    pilot_roll_input = current_roll - rc_mid
                    pilot_pitch_input = current_pitch - rc_mid
                    
                    # Deadband
                    if abs(pilot_roll_input) < deadband: pilot_roll_input = 0
                    if abs(pilot_pitch_input) < deadband: pilot_pitch_input = 0
                    
                    # We want the PID to fight EXTERNAL movement (Wind), not PILOT movement.
                    # If pilot wants to move, they tilt drone => Camera sees flow. PID fights it.
                    # So we must REDUCE the error seen by PID by the expected flow from pilot input?
                    # OR simply add pilot input on top of PID output.
                    
                    # "Fly PosHold" usually means: Stick Center = Hold Position. Stick moved = Move at velocity.
                    # If we just add them:
                    # new_roll = 1500 + pilot_input - pid_correction
                    # If pilot inputs +100 (Roll Right). Drone Rolls Right.
                    # Camera sees Flow Left (dx < 0).
                    # PID Output (based on dx) tries to Roll Left to stop it.
                    # So PID fights Pilot. This feels "heavy" but stable.
                    
                    # To make it feel nicer, we can scale pilot input.
                    
                    new_roll = rc_mid + pilot_roll_input - roll_output
                    new_pitch = rc_mid + pilot_pitch_input + pitch_output
                    
                    # Send new RC
                    fc.set_rc(new_roll, new_pitch, throttle, yaw, aux1, aux2, aux3, aux4)
                    
                else:
                    # Reset PIDs
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
        import traceback
        traceback.print_exc()
    finally:
        flow_sensor.close()
        fc.close()

if __name__ == "__main__":
    main()
