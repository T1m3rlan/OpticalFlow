#!/usr/bin/env python3
"""
Betafly Advanced Optical Position Stabilization System
Includes web interface, camera support, and manual stick inputs
"""

import time
import signal
import sys
import argparse
import logging
from typing import Optional
import json
from threading import Thread

from optical_flow_sensor import OpticalFlowTracker
from sensor_factory import create_sensor
from position_stabilizer import StabilizationController, PIDGains
from stick_input import StickInput, StickMixer, ModeSwitch
from web_interface import (
    app, system_state, state_lock, start_web_server,
    system_commands, command_lock
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BetaflyStabilizerAdvanced:
    """
    Advanced stabilization system with web interface, multiple camera types,
    and manual stick input support
    """
    
    def __init__(self, config_file: Optional[str] = None, enable_web: bool = True):
        """
        Initialize advanced Betafly stabilization system
        
        Args:
            config_file: Path to configuration file (JSON)
            enable_web: Enable web interface
        """
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize sensor based on type
        self.sensor = create_sensor(self.config)
        camera_type = self.config.get('sensor', {}).get('type', 'pmw3901')
        
        # Initialize optical flow tracker
        self.tracker = OpticalFlowTracker(
            sensor=self.sensor,
            scale_factor=self.config['tracker']['scale_factor'],
            height_m=self.config['tracker']['initial_height']
        )
        
        # Initialize stabilization controller
        position_gains_x = PIDGains(**self.config['pid']['position_x'])
        position_gains_y = PIDGains(**self.config['pid']['position_y'])
        
        self.stabilizer = StabilizationController(
            position_gains_x=position_gains_x,
            position_gains_y=position_gains_y,
            velocity_damping=self.config['stabilizer']['velocity_damping'],
            max_tilt=self.config['stabilizer']['max_tilt_angle']
        )
        
        # Initialize stick input if enabled
        self.stick_input = None
        self.stick_mixer = None
        self.mode_switch = None
        
        if self.config.get('stick_input', {}).get('enabled', False):
            try:
                self.stick_input = StickInput(
                    protocol=self.config['stick_input'].get('protocol', 'mock'),
                    device=self.config['stick_input'].get('device', '/dev/ttyAMA0'),
                    channels=self.config['stick_input'].get('channels', 8)
                )
                self.stick_input.start()
                
                self.stick_mixer = StickMixer(
                    self.stick_input,
                    mix_ratio=self.config['stick_input'].get('mix_ratio', 0.5)
                )
                
                self.mode_switch = ModeSwitch(
                    self.stick_input,
                    mode_channel=self.config['stick_input'].get('mode_channel', 4)
                )
                
                logger.info("Stick input enabled")
            except Exception as e:
                logger.error(f"Failed to initialize stick input: {e}")
                self.stick_input = None
        
        # Control loop settings
        self.update_rate = self.config['control']['update_rate_hz']
        self.update_period = 1.0 / self.update_rate
        
        # State variables
        self.running = False
        self.camera_type = camera_type
        
        # Data logging
        self.log_data = self.config['logging']['enabled']
        self.log_file = None
        if self.log_data:
            self.log_file = open(self.config['logging']['file'], 'w')
            self.log_file.write(
                "time,pos_x,pos_y,vel_x,vel_y,pitch_cmd,roll_cmd,"
                "stick_pitch,stick_roll,stick_throttle,stick_yaw,mode,squal\n"
            )
        
        # Web interface
        self.enable_web = enable_web
        self.web_thread = None
        if enable_web:
            self._start_web_interface()
        
        logger.info("Advanced Betafly stabilizer initialized successfully")
    
    def _load_config(self, config_file: Optional[str]) -> dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'sensor': {
                'type': 'pmw3901',
                'spi_bus': 0,
                'spi_device': 0,
                'rotation': 0
            },
            'tracker': {
                'scale_factor': 0.001,
                'initial_height': 0.5
            },
            'pid': {
                'position_x': {'kp': 0.5, 'ki': 0.1, 'kd': 0.2},
                'position_y': {'kp': 0.5, 'ki': 0.1, 'kd': 0.2}
            },
            'stabilizer': {
                'velocity_damping': 0.3,
                'max_tilt_angle': 15.0
            },
            'control': {
                'update_rate_hz': 50
            },
            'camera': {
                'device': 0,
                'width': 640,
                'height': 480,
                'fps': 30,
                'method': 'farneback',
                'deinterlace': True
            },
            'stick_input': {
                'enabled': False,
                'protocol': 'mock',
                'device': '/dev/ttyAMA0',
                'channels': 8,
                'mix_ratio': 0.5,
                'mode_channel': 4
            },
            'logging': {
                'enabled': False,
                'file': 'flight_log.csv'
            },
            'web_interface': {
                'enabled': True,
                'host': '0.0.0.0',
                'port': 8080
            }
        }
        
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                self._deep_update(default_config, loaded_config)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Could not load config file: {e}. Using defaults.")
        
        return default_config
    
    def _deep_update(self, base_dict, update_dict):
        """Recursively update nested dictionaries"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _start_web_interface(self):
        """Start web interface in separate thread"""
        web_config = self.config.get('web_interface', {})
        host = web_config.get('host', '0.0.0.0')
        port = web_config.get('port', 8080)
        
        self.web_thread = Thread(
            target=start_web_server,
            args=(host, port, False),
            daemon=True
        )
        self.web_thread.start()
        logger.info(f"Web interface started at http://{host}:{port}")
    
    def set_mode(self, mode: str):
        """Change stabilization mode"""
        self.stabilizer.set_mode(mode)
    
    def hold_position(self):
        """Enable position hold at current location"""
        # We need current position, so we do a quick update or use last known
        # Since this is called from control loop, we can use the tracker's state
        # But tracker state is updated in the loop AFTER this command processing
        # So we use tracker's current internal state
        self.stabilizer.hold_current_position(self.tracker.pos_x, self.tracker.pos_y)
    
    def start(self):
        """Start the stabilization system"""
        logger.info("Starting Betafly advanced stabilization system")
        self.running = True
        
        # Start in velocity damping mode by default
        self.stabilizer.set_mode("velocity_damping")
        
        try:
            self._control_loop()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the stabilization system"""
        logger.info("Stopping Betafly stabilization system")
        self.running = False
        
        # Stop sensor
        if hasattr(self.sensor, 'shutdown'):
            self.sensor.shutdown()
        elif hasattr(self.sensor, 'stop'):
            self.sensor.stop()
        
        # Stop stick input
        if self.stick_input:
            self.stick_input.stop()
        
        # Close log file
        if self.log_file:
            self.log_file.close()
        
        logger.info("System stopped")
    
    def _control_loop(self):
        """Main control loop"""
        logger.info(f"Control loop running at {self.update_rate} Hz")
        
        loop_count = 0
        start_time = time.time()
        
        while self.running:
            loop_start = time.time()
            
            # Process web commands
            with command_lock:
                while system_commands:
                    try:
                        cmd, arg = system_commands.pop(0)
                        if cmd == 'set_mode':
                            self.stabilizer.set_mode(arg)
                        elif cmd == 'reset_position':
                            self.tracker.reset_position()
                            self.stabilizer.position_stabilizer.reset()
                        elif cmd == 'set_height':
                            self.tracker.set_height(arg)
                        elif cmd == 'hold_position':
                            self.hold_position()
                        logger.info(f"Executed command: {cmd}")
                    except Exception as e:
                        logger.error(f"Error executing command {cmd}: {e}")

            # Update position tracking
            pos_x, pos_y = self.tracker.update()
            vel_x, vel_y = self.tracker.get_velocity()
            
            # Check for mode switch from RC if enabled
            if self.mode_switch:
                rc_mode = self.mode_switch.get_current_mode()
                if rc_mode != self.stabilizer.mode:
                    self.stabilizer.set_mode(rc_mode)
                    logger.info(f"Mode switched via RC to: {rc_mode}")
            
            # Update stabilization controller
            pitch_correction, roll_correction = self.stabilizer.update(
                pos_x, pos_y, vel_x, vel_y
            )
            
            # Mix with manual stick inputs if enabled
            stick_pitch = 0
            stick_roll = 0
            stick_throttle = 0
            stick_yaw = 0
            
            if self.stick_mixer and not self.stick_input.is_failsafe():
                # Get stick positions
                sticks = self.stick_input.get_stick_positions()
                stick_pitch = int(sticks['pitch'] * 500)
                stick_roll = int(sticks['roll'] * 500)
                stick_throttle = int(sticks['throttle'] * 500)
                stick_yaw = int(sticks['yaw'] * 500)
                
                # Mix corrections with manual input
                pitch_correction, roll_correction = self.stick_mixer.mix_controls(
                    pitch_correction, roll_correction, manual_scale=1.0
                )
            
            # Get surface quality for monitoring
            surface_quality = self.tracker.get_surface_quality()
            
            # Update web interface state
            with state_lock:
                system_state['running'] = True
                system_state['mode'] = self.stabilizer.mode
                system_state['position'] = {'x': pos_x, 'y': pos_y}
                system_state['velocity'] = {'x': vel_x, 'y': vel_y}
                system_state['corrections'] = {'pitch': pitch_correction, 'roll': roll_correction}
                system_state['surface_quality'] = surface_quality
                system_state['height'] = self.tracker.height_m
                system_state['stick_inputs'] = {
                    'pitch': stick_pitch,
                    'roll': stick_roll,
                    'throttle': stick_throttle,
                    'yaw': stick_yaw
                }
                system_state['camera_type'] = self.camera_type
                system_state['last_update'] = time.time()
            
            # Send corrections to flight controller
            self._send_corrections(pitch_correction, roll_correction)
            
            # Log data
            if self.log_data and loop_count % 10 == 0:
                self._log_state(
                    time.time() - start_time,
                    pos_x, pos_y, vel_x, vel_y,
                    pitch_correction, roll_correction,
                    stick_pitch, stick_roll, stick_throttle, stick_yaw,
                    self.stabilizer.mode, surface_quality
                )
            
            # Print status periodically
            if loop_count % 50 == 0:
                stick_str = ""
                if self.stick_input:
                    stick_str = f" | Sticks: P:{stick_pitch} R:{stick_roll} T:{stick_throttle}"
                
                logger.info(
                    f"Pos: ({pos_x:.3f}, {pos_y:.3f})m | "
                    f"Vel: ({vel_x:.3f}, {vel_y:.3f})m/s | "
                    f"Cmd: P:{pitch_correction:.2f}° R:{roll_correction:.2f}°{stick_str} | "
                    f"Quality: {surface_quality} | Mode: {self.stabilizer.mode}"
                )
            
            loop_count += 1
            
            # Sleep to maintain update rate
            loop_time = time.time() - loop_start
            sleep_time = self.update_period - loop_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif loop_count % 100 == 0:
                logger.warning(f"Control loop running slow: {loop_time*1000:.1f}ms")
    
    def _send_corrections(self, pitch: float, roll: float):
        """Send correction commands to flight controller"""
        # TODO: Implement flight controller communication
        pass
    
    def _log_state(self, t, pos_x, pos_y, vel_x, vel_y, pitch, roll,
                   stick_p, stick_r, stick_t, stick_y, mode, squal):
        """Log current state to file"""
        if self.log_file:
            self.log_file.write(
                f"{t:.3f},{pos_x:.6f},{pos_y:.6f},{vel_x:.6f},{vel_y:.6f},"
                f"{pitch:.4f},{roll:.4f},{stick_p},{stick_r},{stick_t},{stick_y},"
                f"{mode},{squal}\n"
            )


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received")
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Betafly Advanced Optical Position Stabilization System'
    )
    parser.add_argument('-c', '--config', help='Configuration file (JSON)', default=None)
    parser.add_argument('-m', '--mode', choices=['off', 'velocity_damping', 'position_hold'],
                        default='velocity_damping', help='Initial stabilization mode')
    parser.add_argument('-l', '--log', action='store_true', help='Enable data logging')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-web', action='store_true', help='Disable web interface')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        stabilizer = BetaflyStabilizerAdvanced(
            config_file=args.config,
            enable_web=not args.no_web
        )
        
        if args.log:
            stabilizer.log_data = True
            stabilizer.log_file = open('flight_log.csv', 'w')
            stabilizer.log_file.write(
                "time,pos_x,pos_y,vel_x,vel_y,pitch_cmd,roll_cmd,"
                "stick_pitch,stick_roll,stick_throttle,stick_yaw,mode,squal\n"
            )
        
        stabilizer.stabilizer.set_mode(args.mode)
        stabilizer.start()
        
    except Exception as e:
        logger.error(f"Failed to start stabilizer: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
