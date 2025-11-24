#!/usr/bin/env python3
"""
Hardware Interface for Raspberry Pi Zero
Handles servo/motor control for stabilization
"""

import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available. Running in simulation mode.")

try:
    from gpiozero import Servo, Motor
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False
    logger.warning("gpiozero not available. Running in simulation mode.")


class HardwareInterface:
    """Hardware interface for servo and motor control"""
    
    def __init__(self, config: Config):
        self.config = config
        self.initialized = False
        
        # Servo objects for pitch/roll control
        self.servo_x: Optional[object] = None
        self.servo_y: Optional[object] = None
        
        # Motor objects (if using motors instead of servos)
        self.motor_x: Optional[object] = None
        self.motor_y: Optional[object] = None
        
        # Simulation mode flag
        self.simulation_mode = not (GPIO_AVAILABLE or GPIOZERO_AVAILABLE)
        
    def initialize(self) -> bool:
        """Initialize hardware interfaces"""
        if self.simulation_mode:
            logger.info("Running in simulation mode (no hardware)")
            self.initialized = True
            return True
        
        try:
            if GPIOZERO_AVAILABLE:
                # Initialize servos using gpiozero
                if self.config.USE_SERVOS:
                    self.servo_x = Servo(
                        self.config.SERVO_X_PIN,
                        min_pulse_width=self.config.SERVO_MIN_PULSE,
                        max_pulse_width=self.config.SERVO_MAX_PULSE
                    )
                    self.servo_y = Servo(
                        self.config.SERVO_Y_PIN,
                        min_pulse_width=self.config.SERVO_MIN_PULSE,
                        max_pulse_width=self.config.SERVO_MAX_PULSE
                    )
                    logger.info("Servos initialized")
                else:
                    # Initialize motors
                    self.motor_x = Motor(
                        forward=self.config.MOTOR_X_FORWARD_PIN,
                        backward=self.config.MOTOR_X_BACKWARD_PIN
                    )
                    self.motor_y = Motor(
                        forward=self.config.MOTOR_Y_FORWARD_PIN,
                        backward=self.config.MOTOR_Y_BACKWARD_PIN
                    )
                    logger.info("Motors initialized")
            
            elif GPIO_AVAILABLE:
                # Initialize GPIO pins manually
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                if self.config.USE_SERVOS:
                    # Setup servo pins
                    GPIO.setup(self.config.SERVO_X_PIN, GPIO.OUT)
                    GPIO.setup(self.config.SERVO_Y_PIN, GPIO.OUT)
                    
                    # Create PWM objects
                    self.servo_x = GPIO.PWM(self.config.SERVO_X_PIN, 50)  # 50Hz
                    self.servo_y = GPIO.PWM(self.config.SERVO_Y_PIN, 50)
                    
                    self.servo_x.start(0)
                    self.servo_y.start(0)
                    logger.info("Servos initialized (GPIO mode)")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
            self.simulation_mode = True
            self.initialized = True
            return True  # Continue in simulation mode
    
    def apply_control(self, output_x: float, output_y: float) -> None:
        """
        Apply control outputs to hardware
        
        Args:
            output_x: Control output for X axis (normalized -1 to 1)
            output_y: Control output for Y axis (normalized -1 to 1)
        """
        if not self.initialized:
            return
        
        # Normalize outputs to [-1, 1] range
        output_x = max(-1.0, min(1.0, output_x / self.config.MAX_CONTROL_OUTPUT))
        output_y = max(-1.0, min(1.0, output_y / self.config.MAX_CONTROL_OUTPUT))
        
        if self.simulation_mode:
            logger.debug(f"Simulation: X={output_x:.3f}, Y={output_y:.3f}")
            return
        
        try:
            if self.config.USE_SERVOS:
                self._apply_servo_control(output_x, output_y)
            else:
                self._apply_motor_control(output_x, output_y)
        except Exception as e:
            logger.error(f"Error applying control: {e}")
    
    def _apply_servo_control(self, output_x: float, output_y: float) -> None:
        """Apply control to servos"""
        if GPIOZERO_AVAILABLE and self.servo_x and self.servo_y:
            # gpiozero servo expects -1 to 1
            self.servo_x.value = output_x
            self.servo_y.value = output_y
        
        elif GPIO_AVAILABLE:
            # Manual PWM control
            # Convert -1 to 1 range to duty cycle (typically 2.5% to 12.5%)
            duty_x = 7.5 + (output_x * 5.0)  # Center at 7.5%, ±5% range
            duty_y = 7.5 + (output_y * 5.0)
            
            if self.servo_x and self.servo_y:
                self.servo_x.ChangeDutyCycle(duty_x)
                self.servo_y.ChangeDutyCycle(duty_y)
    
    def _apply_motor_control(self, output_x: float, output_y: float) -> None:
        """Apply control to motors"""
        if GPIOZERO_AVAILABLE and self.motor_x and self.motor_y:
            # gpiozero motor expects -1 to 1
            self.motor_x.value = output_x
            self.motor_y.value = output_y
    
    def cleanup(self) -> None:
        """Clean up hardware resources"""
        try:
            if self.servo_x:
                if GPIOZERO_AVAILABLE:
                    self.servo_x.value = 0
                elif GPIO_AVAILABLE:
                    self.servo_x.stop()
            
            if self.servo_y:
                if GPIOZERO_AVAILABLE:
                    self.servo_y.value = 0
                elif GPIO_AVAILABLE:
                    self.servo_y.stop()
            
            if self.motor_x:
                if GPIOZERO_AVAILABLE:
                    self.motor_x.stop()
            
            if self.motor_y:
                if GPIOZERO_AVAILABLE:
                    self.motor_y.stop()
            
            if GPIO_AVAILABLE:
                GPIO.cleanup()
            
            logger.info("Hardware cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
