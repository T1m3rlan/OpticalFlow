#!/usr/bin/env python3
"""
Joystick/Stick Input Handler
Supports USB joysticks and GPIO-based analog stick inputs
"""

import logging
import os
import struct
from typing import Tuple, Optional
from config import Config

logger = logging.getLogger(__name__)

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("pygame not available. USB joystick support disabled.")

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available. GPIO stick support disabled.")

try:
    import spidev
    SPI_AVAILABLE = True
except ImportError:
    SPI_AVAILABLE = False
    logger.warning("spidev not available. SPI-based analog stick support disabled.")


class JoystickInput:
    """Handle joystick/stick inputs from various sources"""
    
    def __init__(self, config: Config):
        self.config = config
        self.joystick = None
        self.pygame_initialized = False
        self.gpio_initialized = False
        self.spi = None
        
        # Current stick values (-1.0 to 1.0)
        self.stick_x = 0.0
        self.stick_y = 0.0
        
        # Manual input values (from web interface)
        self.manual_x = 0.0
        self.manual_y = 0.0
        
    def initialize(self) -> bool:
        """Initialize joystick input"""
        if self.config.USE_GPIO_STICKS:
            return self._init_gpio_sticks()
        else:
            return self._init_usb_joystick()
    
    def _init_usb_joystick(self) -> bool:
        """Initialize USB joystick"""
        if not PYGAME_AVAILABLE:
            logger.warning("Pygame not available. USB joystick disabled.")
            return False
        
        try:
            pygame.init()
            pygame.joystick.init()
            
            joystick_count = pygame.joystick.get_count()
            if joystick_count == 0:
                logger.warning("No joysticks found")
                return False
            
            # Try to open specified device or first available
            device_path = self.config.JOYSTICK_DEVICE
            if os.path.exists(device_path):
                # Try to match device
                for i in range(joystick_count):
                    joystick = pygame.joystick.Joystick(i)
                    joystick.init()
                    if joystick.get_name():
                        self.joystick = joystick
                        logger.info(f"Initialized joystick: {joystick.get_name()}")
                        self.pygame_initialized = True
                        return True
            else:
                # Use first available joystick
                if joystick_count > 0:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    logger.info(f"Initialized joystick: {self.joystick.get_name()}")
                    self.pygame_initialized = True
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error initializing USB joystick: {e}")
            return False
    
    def _init_gpio_sticks(self) -> bool:
        """Initialize GPIO-based analog stick inputs"""
        if not GPIO_AVAILABLE:
            logger.warning("GPIO not available. GPIO stick support disabled.")
            return False
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup GPIO pins for analog reading
            # Note: This assumes ADC (like MCP3008) connected via SPI
            if SPI_AVAILABLE:
                self.spi = spidev.SpiDev()
                self.spi.open(0, 0)  # SPI bus 0, device 0
                self.spi.max_speed_hz = 1000000
                logger.info("SPI initialized for analog stick reading")
            
            self.gpio_initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing GPIO sticks: {e}")
            return False
    
    def read_stick_values(self) -> Tuple[float, float]:
        """
        Read current stick values
        
        Returns:
            Tuple of (x, y) values in range [-1.0, 1.0]
        """
        if self.pygame_initialized and self.joystick:
            return self._read_pygame_joystick()
        elif self.gpio_initialized:
            return self._read_gpio_sticks()
        else:
            # Return manual input values (from web interface)
            return self.manual_x, self.manual_y
    
    def _read_pygame_joystick(self) -> Tuple[float, float]:
        """Read values from pygame joystick"""
        if not self.joystick:
            return 0.0, 0.0
        
        pygame.event.pump()
        
        # Read axis 0 and 1 (typically left stick X and Y)
        try:
            x = self.joystick.get_axis(0)
            y = self.joystick.get_axis(1)
            
            # Invert Y axis if needed (some joysticks have inverted Y)
            y = -y
            
            self.stick_x = max(-1.0, min(1.0, x))
            self.stick_y = max(-1.0, min(1.0, y))
            
            return self.stick_x, self.stick_y
        except Exception as e:
            logger.debug(f"Error reading joystick: {e}")
            return 0.0, 0.0
    
    def _read_gpio_sticks(self) -> Tuple[float, float]:
        """Read values from GPIO analog sticks"""
        if not self.spi:
            return self.manual_x, self.manual_y
        
        try:
            # Read analog values from ADC
            # Assuming MCP3008 ADC connected via SPI
            def read_adc(channel):
                if channel > 7 or channel < 0:
                    return -1
                adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
                data = ((adc[1] & 3) << 8) + adc[2]
                return data
            
            # Read X and Y axes
            # Adjust channel numbers based on your wiring
            x_raw = read_adc(0)  # Channel 0 for X axis
            y_raw = read_adc(1)  # Channel 1 for Y axis
            
            # Convert to -1.0 to 1.0 range (assuming 10-bit ADC, 0-1023)
            x = ((x_raw / 1023.0) - 0.5) * 2.0
            y = ((y_raw / 1023.0) - 0.5) * 2.0
            
            self.stick_x = max(-1.0, min(1.0, x))
            self.stick_y = max(-1.0, min(1.0, y))
            
            return self.stick_x, self.stick_y
        except Exception as e:
            logger.debug(f"Error reading GPIO sticks: {e}")
            return self.manual_x, self.manual_y
    
    def set_manual_input(self, x: float, y: float) -> None:
        """Set manual input values (from web interface)"""
        self.manual_x = max(-1.0, min(1.0, x))
        self.manual_y = max(-1.0, min(1.0, y))
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if self.pygame_initialized:
            try:
                if self.joystick:
                    self.joystick.quit()
                pygame.joystick.quit()
                pygame.quit()
            except Exception as e:
                logger.error(f"Error cleaning up pygame: {e}")
        
        if self.spi:
            try:
                self.spi.close()
            except Exception as e:
                logger.error(f"Error closing SPI: {e}")
        
        if self.gpio_initialized and GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {e}")
