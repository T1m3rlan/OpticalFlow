#!/usr/bin/env python3
"""
Camera optical flow test utility.

Captures motion from CSI/USB/analog cameras using the same processing pipeline
as the Betafly stabilization stack.
"""

import argparse
import sys
import time

from camera_optical_flow import CameraOpticalFlow, AnalogCameraFlow, auto_detect_camera
from motion_tracker import OpticalFlowTracker


def create_sensor(args):
    """Instantiate the requested camera or analog flow source"""
    if args.type == 'analog_usb':
        sensor = AnalogCameraFlow(
            device_path=args.device,
            width=args.width or 720,
            height=args.height or 480,
            deinterlace=not args.no_deinterlace
        )
    else:
        camera_id = args.device
        if camera_id == 'auto':
            detected = auto_detect_camera()
            if detected is None:
                raise RuntimeError("No camera detected. Specify --device explicitly.")
            camera_id = detected
            print(f"✓ Auto-detected camera at index {camera_id}")
        else:
            try:
                camera_id = int(camera_id)
            except ValueError:
                # treat as /dev/video path
                pass
        
        sensor = CameraOpticalFlow(
            camera_id=camera_id,
            width=args.width,
            height=args.height,
            fps=args.fps,
            method=args.method
        )
    
    sensor.start()
    return sensor


def run_motion_test(args):
    """Run position/velocity estimation loop"""
    sensor = create_sensor(args)
    tracker = OpticalFlowTracker(
        sensor,
        scale_factor=args.scale,
        height_m=args.height_m
    )
    
    print("\n" + "=" * 60)
    print("Camera Optical Flow Test")
    print("=" * 60)
    print(f"Camera type : {args.type}")
    print(f"Device      : {args.device}")
    print(f"Resolution  : {args.width}x{args.height} @ {args.fps}fps")
    print(f"Method      : {args.method}")
    print(f"Height (m)  : {args.height_m}")
    print("=" * 60)
    print("Time  |  PosX (m)  PosY (m)  |  VelX (m/s)  VelY (m/s)  | Quality")
    print("-" * 60)
    
    start = time.time()
    try:
        while (time.time() - start) < args.duration:
            pos_x, pos_y = tracker.update()
            vel_x, vel_y = tracker.get_velocity()
            quality = tracker.get_surface_quality()
            elapsed = time.time() - start
            print(
                f"{elapsed:5.1f} | "
                f"{pos_x:8.4f}  {pos_y:8.4f} | "
                f"{vel_x:9.4f}  {vel_y:9.4f} | "
                f"{quality:7d}",
                end='\r'
            )
            time.sleep(1.0 / args.rate)
    finally:
        print()
        if hasattr(sensor, 'stop'):
            sensor.stop()


def parse_args():
    parser = argparse.ArgumentParser(description="Camera optical flow tester")
    parser.add_argument('--type', choices=['csi_camera', 'usb_camera', 'opencv_any', 'analog_usb'],
                        default='csi_camera', help='Camera transport to test')
    parser.add_argument('--device', default='auto',
                        help='Camera index or /dev/video path (use "auto" to auto-detect)')
    parser.add_argument('--width', type=int, default=640, help='Frame width')
    parser.add_argument('--height', type=int, default=480, help='Frame height')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second request')
    parser.add_argument('--method', choices=['farneback', 'lucas_kanade'],
                        default='farneback', help='Optical flow method')
    parser.add_argument('--duration', type=int, default=15, help='Test duration (seconds)')
    parser.add_argument('--rate', type=float, default=10.0, help='Print rate (Hz)')
    parser.add_argument('--scale', type=float, default=0.001,
                        help='Optical flow scale factor (sensor units to meters)')
    parser.add_argument('--height-m', dest='height_m', type=float, default=0.5,
                        help='Assumed height above surface in meters')
    parser.add_argument('--no-deinterlace', action='store_true',
                        help='Disable analog deinterlacing filter')
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_motion_test(args)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as exc:
        print(f"\n✗ Test failed: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    main()
