#!/usr/bin/env python3
"""
Test script for PMW3901 optical flow sensor
Verifies sensor connection and displays motion data
"""

import time
import sys
import argparse
from optical_flow_sensor import PMW3901, OpticalFlowTracker

def test_basic_connection():
    """Test basic sensor connection"""
    print("Testing PMW3901 sensor connection...")
    try:
        sensor = PMW3901()
        print("✓ Sensor initialized successfully")
        
        # Read product ID
        product_id = sensor._read_register(sensor.REG_PRODUCT_ID)
        print(f"✓ Product ID: 0x{product_id:02X}")
        
        return sensor
    except Exception as e:
        print(f"✗ Failed to initialize sensor: {e}")
        sys.exit(1)

def test_motion_reading(sensor, duration=5):
    """Test motion reading"""
    print(f"\nReading motion data for {duration} seconds...")
    print("Move the sensor to see motion values\n")
    print("Time(s) | Delta X | Delta Y | Quality")
    print("-" * 45)
    
    start_time = time.time()
    while time.time() - start_time < duration:
        delta_x, delta_y = sensor.get_motion()
        quality = sensor.get_surface_quality()
        elapsed = time.time() - start_time
        
        print(f"{elapsed:6.2f}  | {delta_x:7d} | {delta_y:7d} | {quality:3d}    ", end='\r')
        time.sleep(0.1)
    
    print("\n✓ Motion reading test complete")

def test_position_tracking(duration=10):
    """Test position tracking with integration"""
    print(f"\nTesting position tracking for {duration} seconds...")
    print("Move the sensor to track position\n")
    
    sensor = PMW3901()
    tracker = OpticalFlowTracker(sensor, scale_factor=0.001, height_m=0.5)
    
    print("Time(s) | Pos X(m) | Pos Y(m) | Vel X(m/s) | Vel Y(m/s) | Quality")
    print("-" * 75)
    
    start_time = time.time()
    while time.time() - start_time < duration:
        pos_x, pos_y = tracker.update()
        vel_x, vel_y = tracker.get_velocity()
        quality = tracker.get_surface_quality()
        elapsed = time.time() - start_time
        
        print(
            f"{elapsed:6.2f}  | {pos_x:8.4f} | {pos_y:8.4f} | "
            f"{vel_x:10.4f} | {vel_y:10.4f} | {quality:3d}    ",
            end='\r'
        )
        time.sleep(0.05)
    
    print("\n✓ Position tracking test complete")
    
    # Final position
    print(f"\nFinal position: ({pos_x:.4f}, {pos_y:.4f}) meters")
    
    sensor.shutdown()

def test_surface_quality(sensor, duration=5):
    """Monitor surface quality over time"""
    print(f"\nMonitoring surface quality for {duration} seconds...")
    print("Quality values: 0-50 (poor), 50-150 (good), 150+ (excellent)\n")
    
    qualities = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        quality = sensor.get_surface_quality()
        qualities.append(quality)
        elapsed = time.time() - start_time
        
        print(f"Time: {elapsed:5.2f}s | Quality: {quality:3d} {'█' * (quality // 10)}", end='\r')
        time.sleep(0.1)
    
    print("\n")
    avg_quality = sum(qualities) / len(qualities)
    min_quality = min(qualities)
    max_quality = max(qualities)
    
    print(f"Average quality: {avg_quality:.1f}")
    print(f"Range: {min_quality} - {max_quality}")
    
    if avg_quality < 50:
        print("⚠️  Low quality - improve lighting or surface texture")
    elif avg_quality < 150:
        print("✓ Good quality")
    else:
        print("✓ Excellent quality")

def main():
    parser = argparse.ArgumentParser(description='Test PMW3901 optical flow sensor')
    parser.add_argument(
        '-t', '--test',
        choices=['connection', 'motion', 'tracking', 'quality', 'all'],
        default='all',
        help='Test to run'
    )
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=5,
        help='Test duration in seconds'
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("PMW3901 Optical Flow Sensor Test")
    print("=" * 50)
    print()
    
    try:
        if args.test in ['connection', 'all']:
            sensor = test_basic_connection()
        else:
            sensor = PMW3901()
        
        if args.test in ['motion', 'all']:
            test_motion_reading(sensor, args.duration)
        
        if args.test in ['quality', 'all']:
            test_surface_quality(sensor, args.duration)
        
        if args.test in ['tracking', 'all']:
            if args.test == 'all':
                sensor.shutdown()
            test_position_tracking(args.duration * 2)
        else:
            sensor.shutdown()
        
        print("\n" + "=" * 50)
        print("All tests passed!")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
