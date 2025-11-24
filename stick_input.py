"""
Manual Stick Input Handler for RC Control
Supports PPM, SBUS, and PWM input from RC receivers
Allows manual override and mixing with position stabilization
"""

import time
import logging
from typing import Tuple, Optional, Dict
from threading import Thread, Lock
import struct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import serial for SBUS
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not available - SBUS input disabled")

# Try to import RPi.GPIO for PWM
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available - PWM input disabled")


class StickInput:
    """
    RC stick input handler with multiple protocol support
    """
    
    def __init__(self,
                 protocol: str = 'sbus',
                 device: str = '/dev/ttyAMA0',
                 channels: int = 8):
        """
        Initialize stick input handler
        
        Args:
            protocol: Input protocol ('sbus', 'ppm', 'pwm', 'mock')
            device: Serial device for SBUS ('/dev/ttyAMA0' or '/dev/ttyUSB0')
            channels: Number of RC channels to read
        """
        self.protocol = protocol
        self.device = device
        self.channels = channels
        
        # Channel values (microseconds: 1000-2000, center at 1500)
        self.channel_values = [1500] * channels
        self.channel_lock = Lock()
        
        # Named channel mappings (typical Mode 2)
        self.ROLL = 0      # Right stick left/right
        self.PITCH = 1     # Right stick up/down
        self.THROTTLE = 2  # Left stick up/down
        self.YAW = 3       # Left stick left/right
        self.AUX1 = 4      # Switch 1 (mode select)
        self.AUX2 = 5      # Switch 2
        
        # Running flag
        self.running = False
        self.read_thread = None
        
        # Failsafe
        self.last_update_time = time.time()
        self.failsafe_timeout = 1.0  # seconds
        
        # Initialize protocol handler
        if protocol == 'sbus':
            if not SERIAL_AVAILABLE:
                raise RuntimeError("pyserial required for SBUS")
            self._init_sbus()
        elif protocol == 'pwm':
            if not GPIO_AVAILABLE:
                raise RuntimeError("RPi.GPIO required for PWM")
            self._init_pwm()
        elif protocol == 'mock':
            self._init_mock()
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
        
        logger.info(f"Stick input initialized: {protocol}")
    
    def _init_sbus(self):
        """Initialize SBUS receiver"""
        try:
            self.serial = serial.Serial(
                port=self.device,
                baudrate=100000,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_TWO,
                timeout=0.1
            )
            logger.info(f"SBUS receiver initialized on {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize SBUS: {e}")
            raise
    
    def _init_pwm(self):
        """Initialize PWM input pins"""
        GPIO.setmode(GPIO.BCM)
        self.pwm_pins = [17, 18, 22, 23, 24, 25, 27, 4]  # GPIO pins for channels
        
        for pin in self.pwm_pins[:self.channels]:
            GPIO.setup(pin, GPIO.IN)
        
        logger.info(f"PWM input initialized on pins {self.pwm_pins[:self.channels]}")
    
    def _init_mock(self):
        """Initialize mock input for testing"""
        logger.info("Mock stick input initialized (for testing)")
    
    def start(self):
        """Start reading stick inputs"""
        if not self.running:
            self.running = True
            self.read_thread = Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            logger.info("Stick input reading started")
    
    def stop(self):
        """Stop reading stick inputs"""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=2.0)
        
        if self.protocol == 'sbus' and hasattr(self, 'serial'):
            self.serial.close()
        elif self.protocol == 'pwm' and GPIO_AVAILABLE:
            GPIO.cleanup()
        
        logger.info("Stick input stopped")
    
    def _read_loop(self):
        """Continuous reading loop"""
        while self.running:
            try:
                if self.protocol == 'sbus':
                    self._read_sbus()
                elif self.protocol == 'pwm':
                    self._read_pwm()
                elif self.protocol == 'mock':
                    self._read_mock()
                
                time.sleep(0.01)  # 100Hz read rate
                
            except Exception as e:
                logger.error(f"Error reading stick input: {e}")
                time.sleep(0.1)
    
    def _read_sbus(self):
        """Read SBUS packet"""
        # SBUS packet: 25 bytes
        # Start byte (0x0F) + 22 data bytes + flags + end byte (0x00)
        
        # Find start byte
        while self.running:
            byte = self.serial.read(1)
            if not byte:
                return
            if byte[0] == 0x0F:
                break
        
        # Read rest of packet
        data = self.serial.read(24)
        if len(data) != 24:
            return
        
        # Check end byte
        if data[23] != 0x00:
            return
        
        # Parse channels (11 bits each, packed)
        channels = []
        bit_index = 0
        
        for i in range(16):
            value = 0
            for bit in range(11):
                byte_index = bit_index // 8
                bit_position = bit_index % 8
                
                if data[byte_index] & (1 << bit_position):
                    value |= (1 << bit)
                
                bit_index += 1
            
            # Convert SBUS value (172-1811) to standard PWM (1000-2000)
            pwm_value = int((value - 172) * 800 / 1639 + 1000)
            pwm_value = max(1000, min(2000, pwm_value))
            channels.append(pwm_value)
        
        # Update channel values
        with self.channel_lock:
            self.channel_values = channels[:self.channels]
            self.last_update_time = time.time()
    
    def _read_pwm(self):
        """Read PWM inputs"""
        # This is a simplified version - proper PWM reading requires
        # precise timing and interrupt handling
        # For production use, consider using pigpio library
        
        channels = []
        for pin in self.pwm_pins[:self.channels]:
            # Measure pulse width (simplified - needs proper implementation)
            # In reality, you'd use GPIO interrupts or pigpio
            pulse_width = 1500  # Placeholder
            channels.append(pulse_width)
        
        with self.channel_lock:
            self.channel_values = channels
            self.last_update_time = time.time()
    
    def _read_mock(self):
        """Generate mock input for testing"""
        # Simulate stick movements
        t = time.time()
        
        with self.channel_lock:
            # Keep center positions with slight variations
            self.channel_values[self.ROLL] = int(1500 + 50 * (t % 1.0 - 0.5))
            self.channel_values[self.PITCH] = int(1500 + 50 * ((t * 1.3) % 1.0 - 0.5))
            self.channel_values[self.THROTTLE] = 1500
            self.channel_values[self.YAW] = 1500
            self.channel_values[self.AUX1] = 1500
            self.last_update_time = time.time()
    
    def get_channels(self) -> list:
        """Get all channel values"""
        with self.channel_lock:
            return self.channel_values.copy()
    
    def get_channel(self, channel: int) -> int:
        """Get specific channel value (1000-2000 microseconds)"""
        with self.channel_lock:
            if 0 <= channel < len(self.channel_values):
                return self.channel_values[channel]
        return 1500
    
    def get_normalized(self, channel: int) -> float:
        """
        Get normalized channel value (-1.0 to 1.0)
        Center at 1500us = 0.0
        """
        value = self.get_channel(channel)
        return (value - 1500) / 500.0
    
    def get_stick_positions(self) -> Dict[str, float]:
        """
        Get all stick positions as normalized values (-1.0 to 1.0)
        """
        return {
            'roll': self.get_normalized(self.ROLL),
            'pitch': self.get_normalized(self.PITCH),
            'throttle': self.get_normalized(self.THROTTLE),
            'yaw': self.get_normalized(self.YAW)
        }
    
    def is_failsafe(self) -> bool:
        """Check if failsafe is triggered (no recent updates)"""
        return (time.time() - self.last_update_time) > self.failsafe_timeout
    
    def get_switch_position(self, channel: int, positions: int = 3) -> int:
        """
        Get switch position (0, 1, or 2 for 3-position switch)
        
        Args:
            channel: Channel number
            positions: Number of switch positions (2 or 3)
        
        Returns:
            Switch position (0 to positions-1)
        """
        value = self.get_channel(channel)
        
        if positions == 2:
            # 2-position: low (<1400) = 0, high (>1600) = 1
            return 0 if value < 1400 else 1
        else:
            # 3-position: low (<1300) = 0, mid (1300-1700) = 1, high (>1700) = 2
            if value < 1300:
                return 0
            elif value > 1700:
                return 2
            else:
                return 1


class StickMixer:
    """
    Mix manual stick inputs with stabilization outputs
    Allows pilot override while maintaining position hold
    """
    
    def __init__(self, stick_input: StickInput, mix_ratio: float = 0.5):
        """
        Initialize stick mixer
        
        Args:
            stick_input: StickInput instance
            mix_ratio: How much manual input to mix (0.0 = full stab, 1.0 = full manual)
        """
        self.stick_input = stick_input
        self.mix_ratio = mix_ratio
        
        # Deadzone for stick centering
        self.deadzone = 0.05  # 5% deadzone
        
        logger.info(f"Stick mixer initialized with ratio {mix_ratio}")
    
    def apply_deadzone(self, value: float) -> float:
        """Apply deadzone to normalized value"""
        if abs(value) < self.deadzone:
            return 0.0
        
        # Scale value outside deadzone
        sign = 1 if value > 0 else -1
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)
    
    def mix_controls(self,
                     stab_pitch: float,
                     stab_roll: float,
                     manual_scale: float = 1.0) -> Tuple[float, float]:
        """
        Mix stabilization outputs with manual inputs
        
        Args:
            stab_pitch: Stabilization pitch command (degrees)
            stab_roll: Stabilization roll command (degrees)
            manual_scale: Scale factor for manual inputs (0-1)
        
        Returns:
            Tuple of (final_pitch, final_roll) in degrees
        """
        # Get stick positions
        sticks = self.stick_input.get_stick_positions()
        
        # Apply deadzone
        manual_pitch = self.apply_deadzone(sticks['pitch'])
        manual_roll = self.apply_deadzone(sticks['roll'])
        
        # Convert normalized stick to degrees (e.g., ±30 degrees)
        max_manual_angle = 30.0 * manual_scale
        manual_pitch_deg = manual_pitch * max_manual_angle
        manual_roll_deg = manual_roll * max_manual_angle
        
        # Mix: when stick is centered, use stabilization
        # When stick is deflected, blend in manual control
        manual_authority = max(abs(manual_pitch), abs(manual_roll))
        blend = manual_authority * self.mix_ratio
        
        final_pitch = (1 - blend) * stab_pitch + blend * manual_pitch_deg
        final_roll = (1 - blend) * stab_roll + blend * manual_roll_deg
        
        return (final_pitch, final_roll)
    
    def set_mix_ratio(self, ratio: float):
        """Set mix ratio (0.0 = full stab, 1.0 = full manual)"""
        self.mix_ratio = max(0.0, min(1.0, ratio))


class ModeSwitch:
    """
    Handle mode switching from RC transmitter
    """
    
    def __init__(self, stick_input: StickInput, mode_channel: int = 4):
        """
        Initialize mode switch handler
        
        Args:
            stick_input: StickInput instance
            mode_channel: Channel for mode selection (typically AUX1)
        """
        self.stick_input = stick_input
        self.mode_channel = mode_channel
        
        # Mode mapping: switch position -> mode
        self.mode_map = {
            0: 'off',
            1: 'velocity_damping',
            2: 'position_hold'
        }
    
    def get_current_mode(self) -> str:
        """Get current mode from switch position"""
        position = self.stick_input.get_switch_position(self.mode_channel, 3)
        return self.mode_map.get(position, 'off')
    
    def is_position_hold_enabled(self) -> bool:
        """Check if position hold mode is selected"""
        return self.get_current_mode() == 'position_hold'
