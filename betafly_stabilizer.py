#!/usr/bin/env python3
"""
Betafly Optical Position Stabilization System
Main control script for Raspberry Pi Zero

This script integrates optical flow sensing with position stabilization
to provide autonomous position hold capabilities for the Betafly drone.
"""

import time
import signal
import sys
import argparse
import logging
from typing import Optional
import json

from optical_flow_sensor import PMW3901, OpticalFlowTracker
from position_stabilizer import (
    StabilizationController, 
    PIDGains
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BetaflyStabilizer:
    """
    Main stabilization system for Betafly
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize Betafly stabilization system
        
        Args:
            config_file: Path to configuration file (JSON)
        """
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize optical flow sensor
        logger.info("Initializing optical flow sensor...")
        self.sensor = PMW3901(
            spi_bus=self.config['sensor']['spi_bus'],
            spi_device=self.config['sensor']['spi_device'],
            rotation=self.config['sensor']['rotation']
        )
        
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
        
        # Control loop settings
        self.update_rate = self.config['control']['update_rate_hz']
        self.update_period = 1.0 / self.update_rate
        
        # State variables
        self.running = False
        self.last_update_time = 0
        
        # Data logging
        self.log_data = self.config['logging']['enabled']
        self.log_file = None
        if self.log_data:
            self.log_file = open(self.config['logging']['file'], 'w')
            self.log_file.write("time,pos_x,pos_y,vel_x,vel_y,pitch_cmd,roll_cmd,mode,squal\n")
        
        # Output interface (placeholder for flight controller communication)
        self.output_interface = None
        
        logger.info("Betafly stabilizer initialized successfully")
    
    def _load_config(self, config_file: Optional[str]) -> dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'sensor': {
                'spi_bus': 0,
                'spi_device': 0,
                'rotation': 0
            },
            'tracker': {
                'scale_factor': 0.001,
                'initial_height': 0.5
            },
            'pid': {
                'position_x': {
                    'kp': 0.5,
                    'ki': 0.1,
                    'kd': 0.2
                },
                'position_y': {
                    'kp': 0.5,
                    'ki': 0.1,
                    'kd': 0.2
                }
            },
            'stabilizer': {
                'velocity_damping': 0.3,
                'max_tilt_angle': 15.0
            },
            'control': {
                'update_rate_hz': 50
            },
            'logging': {
                'enabled': False,
                'file': 'flight_log.csv'
            },
            'output': {
                'interface': 'mavlink',  # 'mavlink', 'msp', or 'pwm'
                'port': '/dev/ttyAMA0',
                'baudrate': 115200
            }
        }
        
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge loaded config with defaults
                default_config.update(loaded_config)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Could not load config file: {e}. Using defaults.")
        
        return default_config
    
    def start(self):
        """Start the stabilization system"""
        logger.info("Starting Betafly stabilization system")
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
        
        # Shutdown sensor
        self.sensor.shutdown()
        
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
            
            # Update position tracking
            pos_x, pos_y = self.tracker.update()
            vel_x, vel_y = self.tracker.get_velocity()
            
            # Update stabilization controller
            pitch_correction, roll_correction = self.stabilizer.update(
                pos_x, pos_y, vel_x, vel_y
            )
            
            # Get surface quality for monitoring
            surface_quality = self.tracker.get_surface_quality()
            
            # Send corrections to flight controller
            self._send_corrections(pitch_correction, roll_correction)
            
            # Log data
            if self.log_data and loop_count % 10 == 0:  # Log every 10th iteration
                self._log_state(
                    time.time() - start_time,
                    pos_x, pos_y, vel_x, vel_y,
                    pitch_correction, roll_correction,
                    self.stabilizer.mode,
                    surface_quality
                )
            
            # Print status periodically
            if loop_count % 50 == 0:  # Every second at 50Hz
                logger.info(
                    f"Pos: ({pos_x:.3f}, {pos_y:.3f})m | "
                    f"Vel: ({vel_x:.3f}, {vel_y:.3f})m/s | "
                    f"Cmd: P:{pitch_correction:.2f}° R:{roll_correction:.2f}° | "
                    f"Quality: {surface_quality} | "
                    f"Mode: {self.stabilizer.mode}"
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
        """
        Send correction commands to flight controller
        
        Args:
            pitch: Pitch correction in degrees
            roll: Roll correction in degrees
        """
        # TODO: Implement flight controller communication
        # This is a placeholder for MAVLink, MSP, or PWM output
        
        # For now, just pass (corrections are printed in status)
        pass
    
    def _log_state(self, t: float, pos_x: float, pos_y: float,
                   vel_x: float, vel_y: float, pitch: float, roll: float,
                   mode: str, squal: int):
        """Log current state to file"""
        if self.log_file:
            self.log_file.write(
                f"{t:.3f},{pos_x:.6f},{pos_y:.6f},{vel_x:.6f},{vel_y:.6f},"
                f"{pitch:.4f},{roll:.4f},{mode},{squal}\n"
            )
    
    def set_mode(self, mode: str):
        """Change stabilization mode"""
        self.stabilizer.set_mode(mode)
    
    def hold_position(self):
        """Enable position hold at current location"""
        pos_x, pos_y = self.tracker.update()
        self.stabilizer.hold_current_position(pos_x, pos_y)
    
    def reset_position(self):
        """Reset position tracking to origin"""
        self.tracker.reset_position()
    
    def set_height(self, height_m: float):
        """Update height above ground for accurate tracking"""
        self.tracker.set_height(height_m)
        logger.info(f"Height updated to {height_m:.2f}m")


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received")
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Betafly Optical Position Stabilization System'
    )
    parser.add_argument(
        '-c', '--config',
        help='Configuration file (JSON)',
        default=None
    )
    parser.add_argument(
        '-m', '--mode',
        choices=['off', 'velocity_damping', 'position_hold'],
        default='velocity_damping',
        help='Initial stabilization mode'
    )
    parser.add_argument(
        '-l', '--log',
        action='store_true',
        help='Enable data logging'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start stabilizer
    try:
        stabilizer = BetaflyStabilizer(config_file=args.config)
        
        # Override logging if specified
        if args.log:
            stabilizer.log_data = True
            stabilizer.log_file = open('flight_log.csv', 'w')
            stabilizer.log_file.write(
                "time,pos_x,pos_y,vel_x,vel_y,pitch_cmd,roll_cmd,mode,squal\n"
            )
        
        # Set initial mode
        stabilizer.set_mode(args.mode)
        
        # Start system
        stabilizer.start()
        
    except Exception as e:
        logger.error(f"Failed to start stabilizer: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
