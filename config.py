#!/usr/bin/env python3
"""
Configuration file for optical position stabilization system
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration parameters"""
    
    # Camera settings
    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    CAMERA_FPS: int = 30
    CAMERA_CENTER_X: float = 320.0
    CAMERA_CENTER_Y: float = 240.0
    
    # Optical flow settings
    MIN_TRACKING_POINTS: int = 10
    DISPLACEMENT_SCALE_X: float = 1.0
    DISPLACEMENT_SCALE_Y: float = 1.0
    
    # PID Controller settings - X axis
    PID_KP_X: float = 0.5
    PID_KI_X: float = 0.01
    PID_KD_X: float = 0.1
    
    # PID Controller settings - Y axis
    PID_KP_Y: float = 0.5
    PID_KI_Y: float = 0.01
    PID_KD_Y: float = 0.1
    
    # Control settings
    CONTROL_FREQUENCY: float = 30.0  # Hz
    MAX_CONTROL_OUTPUT: float = 100.0
    
    # Hardware settings
    USE_SERVOS: bool = True  # Set to False for motor control
    
    # Servo pins (BCM numbering)
    SERVO_X_PIN: int = 18  # GPIO 18 (PWM capable)
    SERVO_Y_PIN: int = 19  # GPIO 19 (PWM capable)
    SERVO_MIN_PULSE: float = 0.0005  # 0.5ms
    SERVO_MAX_PULSE: float = 0.0025  # 2.5ms
    
    # Motor pins (if not using servos)
    MOTOR_X_FORWARD_PIN: int = 17
    MOTOR_X_BACKWARD_PIN: int = 27
    MOTOR_Y_FORWARD_PIN: int = 22
    MOTOR_Y_BACKWARD_PIN: int = 23
    
    # Logging
    LOG_INTERVAL: int = 30  # Log every N frames
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables"""
        config = cls()
        
        # Override with environment variables if present
        if os.getenv('CAMERA_INDEX'):
            config.CAMERA_INDEX = int(os.getenv('CAMERA_INDEX'))
        if os.getenv('CAMERA_WIDTH'):
            config.CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH'))
        if os.getenv('CAMERA_HEIGHT'):
            config.CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT'))
        
        if os.getenv('PID_KP_X'):
            config.PID_KP_X = float(os.getenv('PID_KP_X'))
        if os.getenv('PID_KI_X'):
            config.PID_KI_X = float(os.getenv('PID_KI_X'))
        if os.getenv('PID_KD_X'):
            config.PID_KD_X = float(os.getenv('PID_KD_X'))
        
        if os.getenv('PID_KP_Y'):
            config.PID_KP_Y = float(os.getenv('PID_KP_Y'))
        if os.getenv('PID_KI_Y'):
            config.PID_KI_Y = float(os.getenv('PID_KI_Y'))
        if os.getenv('PID_KD_Y'):
            config.PID_KD_Y = float(os.getenv('PID_KD_Y'))
        
        if os.getenv('USE_SERVOS'):
            config.USE_SERVOS = os.getenv('USE_SERVOS').lower() == 'true'
        
        return config
