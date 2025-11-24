import time

class PIDController:
    def __init__(self, kp, ki, kd, setpoint=0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        
        self._prev_error = 0
        self._integral = 0
        self._last_time = time.time()

    def update(self, measurement):
        current_time = time.time()
        dt = current_time - self._last_time
        if dt <= 0:
            dt = 1e-6 # Avoid division by zero
            
        error = self.setpoint - measurement
        
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt
        
        output = (self.kp * error) + (self.ki * self._integral) + (self.kd * derivative)
        
        self._prev_error = error
        self._last_time = current_time
        
        return output

    def reset(self):
        self._prev_error = 0
        self._integral = 0
        self._last_time = time.time()
