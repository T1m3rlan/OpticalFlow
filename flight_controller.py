import serial
import struct
import config
import time

class FlightController:
    def __init__(self):
        try:
            self.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=0.1)
            # Wait for serial to initialize
            time.sleep(1)
        except serial.SerialException as e:
            print(f"Error opening serial port {config.SERIAL_PORT}: {e}")
            self.ser = None

    def send_msp(self, cmd, payload):
        if self.ser is None:
            return

        # MSP V1
        # Header: $M<
        # Size: byte
        # Type: byte
        # Payload
        # Checksum
        
        size = len(payload)
        checksum = 0
        
        data = bytearray()
        data.extend(b'$M<')
        data.append(size)
        checksum ^= size
        
        data.append(cmd)
        checksum ^= cmd
        
        for b in payload:
            data.append(b)
            checksum ^= b
            
        data.append(checksum)
        
        self.ser.write(data)

    def read_msp(self, cmd):
        if self.ser is None:
            return None
            
        self.send_msp(cmd, [])
        
        # Read header
        # Wait for $M> (response)
        start_time = time.time()
        while self.ser.in_waiting < 3:
            if time.time() - start_time > 0.1:
                return None
                
        header = self.ser.read(3)
        if header != b'$M>':
            # Flush garbage
            self.ser.flushInput()
            return None
            
        try:
            size = ord(self.ser.read(1))
            cmd_returned = ord(self.ser.read(1))
            
            if cmd_returned != cmd:
                return None
                
            data = self.ser.read(size)
            checksum = ord(self.ser.read(1))
            
            # Verify checksum (optional but recommended)
            calc_checksum = size ^ cmd_returned
            for b in data:
                calc_checksum ^= b
                
            if calc_checksum != checksum:
                return None
                
            return data
        except Exception:
            return None

    def get_rc(self):
        # MSP_RC = 105
        data = self.read_msp(105)
        if data and len(data) >= 16:
            # 8 channels, uint16
            channels = struct.unpack('<8H', data[:16])
            return list(channels)
        return None

    def set_rc(self, roll, pitch, throttle, yaw, aux1=1000, aux2=1000, aux3=1000, aux4=1000):
        """
        Sends MSP_SET_RAW_RC (200)
        Channels range: 1000 - 2000
        Center: 1500
        """
        # MSP_SET_RAW_RC = 200
        cmd = 200
        
        # Clamp values
        roll = max(1000, min(2000, int(roll)))
        pitch = max(1000, min(2000, int(pitch)))
        throttle = max(1000, min(2000, int(throttle)))
        yaw = max(1000, min(2000, int(yaw)))
        aux1 = max(1000, min(2000, int(aux1)))
        aux2 = max(1000, min(2000, int(aux2)))
        aux3 = max(1000, min(2000, int(aux3)))
        aux4 = max(1000, min(2000, int(aux4)))

        # 8 channels, 2 bytes each (16 bytes total)
        # Format: 8 unsigned shorts, Little Endian
        payload = struct.pack('<8H', 
                              roll, pitch, throttle, yaw,
                              aux1, aux2, aux3, aux4)
        self.send_msp(cmd, payload)
        
    def close(self):
        if self.ser:
            self.ser.close()
