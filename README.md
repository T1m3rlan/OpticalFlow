# Optical Position Stabilization for BetaFly - Raspberry Pi Zero

This project implements an optical position stabilization system for BetaFly using a Raspberry Pi Zero. The system uses computer vision (OpenCV) to detect position changes through optical flow and applies PID control to stabilize the position using servos or motors.

## Features

- **Optical Flow Detection**: Uses Lucas-Kanade optical flow algorithm to track position changes
- **PID Control**: Dual-axis PID controllers for precise stabilization
- **Hardware Support**: Supports both servo and motor control
- **Simulation Mode**: Can run without hardware for testing
- **Configurable**: Easy-to-modify configuration parameters

## Hardware Requirements

- Raspberry Pi Zero (or Zero W/WH)
- Camera module (compatible with OpenCV)
- 2x Servos (for pitch/roll control) OR 2x Motors with motor drivers
- Power supply for servos/motors
- Jumper wires

## Software Requirements

- Raspberry Pi OS (or compatible Linux distribution)
- Python 3.7+
- OpenCV with camera support
- GPIO libraries (RPi.GPIO and/or gpiozero)

## Installation

1. **Clone or download this repository**

2. **Install system dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-opencv python3-numpy
   ```

3. **Install Python packages**:
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Enable camera interface** (if not already enabled):
   ```bash
   sudo raspi-config
   # Navigate to Interface Options > Camera > Enable
   ```

5. **Configure GPIO permissions** (if needed):
   ```bash
   sudo usermod -a -G gpio $USER
   # Log out and log back in for changes to take effect
   ```

## Configuration

Edit `config.py` to adjust parameters:

### Camera Settings
- `CAMERA_WIDTH`, `CAMERA_HEIGHT`: Camera resolution
- `CAMERA_FPS`: Frame rate
- `CAMERA_CENTER_X`, `CAMERA_CENTER_Y`: Target stabilization point

### PID Tuning
- `PID_KP_X/Y`: Proportional gain (start with 0.5)
- `PID_KI_X/Y`: Integral gain (start with 0.01)
- `PID_KD_X/Y`: Derivative gain (start with 0.1)

### Hardware Configuration
- `USE_SERVOS`: Set to `True` for servos, `False` for motors
- `SERVO_X_PIN`, `SERVO_Y_PIN`: GPIO pins for servos (use PWM-capable pins: 12, 13, 18, 19)
- `MOTOR_X/Y_FORWARD_PIN`, `MOTOR_X/Y_BACKWARD_PIN`: GPIO pins for motors

## Wiring

### Servo Configuration
- Servo X: Signal → GPIO 18, Power → 5V, Ground → GND
- Servo Y: Signal → GPIO 19, Power → 5V, Ground → GND

**Note**: Servos may require external power supply if drawing too much current.

### Motor Configuration
- Motor X: Forward → GPIO 17, Backward → GPIO 27
- Motor Y: Forward → GPIO 22, Backward → GPIO 23
- Connect motors through appropriate motor drivers (e.g., L298N)

## Usage

1. **Basic usage**:
   ```bash
   python3 stabilization_controller.py
   ```

2. **With custom configuration** (using environment variables):
   ```bash
   PID_KP_X=0.8 PID_KI_X=0.02 python3 stabilization_controller.py
   ```

3. **Stop the controller**: Press `Ctrl+C`

## How It Works

1. **Image Capture**: The camera captures frames at the configured frame rate
2. **Feature Detection**: Good features to track are detected in each frame
3. **Optical Flow**: Lucas-Kanade optical flow calculates displacement between frames
4. **Position Update**: Current position is updated based on detected displacement
5. **PID Control**: PID controllers compute correction outputs for X and Y axes
6. **Hardware Control**: Control signals are sent to servos/motors to stabilize position

## Tuning Guide

### Initial Setup
1. Start with default PID values
2. Run in simulation mode first to verify optical flow detection
3. Gradually increase control output limits

### PID Tuning
- **Too much oscillation**: Reduce `KP`, increase `KD`
- **Slow response**: Increase `KP`
- **Steady-state error**: Increase `KI`
- **Overshoot**: Reduce `KP`, increase `KD`

### Performance Optimization
- Reduce camera resolution for higher frame rates
- Adjust `MIN_TRACKING_POINTS` based on environment
- Tune `DISPLACEMENT_SCALE_X/Y` to match your setup

## Troubleshooting

### Camera Issues
- Verify camera is detected: `lsusb` or `v4l2-ctl --list-devices`
- Check camera permissions
- Try different `CAMERA_INDEX` values (0, 1, etc.)

### GPIO Issues
- Verify GPIO pins are not in use by other processes
- Check wiring connections
- Ensure proper power supply for servos/motors

### Performance Issues
- Reduce camera resolution
- Lower frame rate
- Optimize feature detection parameters

## Simulation Mode

The system automatically runs in simulation mode if GPIO libraries are not available. This is useful for:
- Testing on non-Raspberry Pi systems
- Development and debugging
- Algorithm validation

## License

This project is provided as-is for educational and research purposes.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Acknowledgments

- OpenCV for computer vision capabilities
- Raspberry Pi Foundation for hardware platform
- BetaFly community for inspiration
