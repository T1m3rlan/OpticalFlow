#!/usr/bin/env python3
"""
Test script to verify camera and optical flow detection
"""

import cv2
import numpy as np
import sys
from config import Config

def test_camera():
    """Test camera initialization and basic capture"""
    config = Config()
    
    print("Testing camera...")
    camera = cv2.VideoCapture(config.CAMERA_INDEX)
    
    if not camera.isOpened():
        print(f"ERROR: Failed to open camera {config.CAMERA_INDEX}")
        return False
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    camera.set(cv2.CAMERA_HEIGHT, config.CAMERA_HEIGHT)
    
    print("Camera opened successfully!")
    print(f"Resolution: {config.CAMERA_WIDTH}x{config.CAMERA_HEIGHT}")
    
    # Capture a few frames
    print("\nCapturing frames (press 'q' to quit)...")
    frame_count = 0
    
    while frame_count < 10:
        ret, frame = camera.read()
        if not ret:
            print("ERROR: Failed to read frame")
            break
        
        frame_count += 1
        print(f"Frame {frame_count} captured")
        
        # Display frame
        cv2.imshow('Camera Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    camera.release()
    cv2.destroyAllWindows()
    
    print(f"\nSuccessfully captured {frame_count} frames")
    return True


def test_optical_flow():
    """Test optical flow detection"""
    config = Config()
    
    print("\nTesting optical flow detection...")
    camera = cv2.VideoCapture(config.CAMERA_INDEX)
    
    if not camera.isOpened():
        print(f"ERROR: Failed to open camera {config.CAMERA_INDEX}")
        return False
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    camera.set(cv2.CAMERA_HEIGHT, config.CAMERA_HEIGHT)
    
    # Feature detection parameters
    feature_params = dict(
        maxCorners=100,
        qualityLevel=0.3,
        minDistance=7,
        blockSize=7
    )
    
    lk_params = dict(
        winSize=(15, 15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
    )
    
    ret, old_frame = camera.read()
    if not ret:
        print("ERROR: Failed to read initial frame")
        camera.release()
        return False
    
    old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
    p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
    
    if p0 is None or len(p0) == 0:
        print("ERROR: No features detected")
        camera.release()
        return False
    
    print(f"Detected {len(p0)} features to track")
    
    frame_count = 0
    while frame_count < 30:
        ret, frame = camera.read()
        if not ret:
            break
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)
        
        # Select good points
        good_new = p1[st == 1]
        good_old = p0[st == 1]
        
        if len(good_new) > 0:
            # Draw tracks
            for i, (new, old) in enumerate(zip(good_new, good_old)):
                a, b = new.ravel()
                c, d = old.ravel()
                frame = cv2.line(frame, (int(a), int(b)), (int(c), int(d)), (0, 255, 0), 2)
                frame = cv2.circle(frame, (int(a), int(b)), 5, (0, 0, 255), -1)
            
            displacement = np.mean(good_new - good_old, axis=0)
            print(f"Frame {frame_count}: Displacement = ({displacement[0]:.2f}, {displacement[1]:.2f}), "
                  f"Tracking {len(good_new)} points")
        
        cv2.imshow('Optical Flow Test', frame)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
        
        # Update for next iteration
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2) if len(good_new) > 0 else cv2.goodFeaturesToTrack(
            frame_gray, mask=None, **feature_params
        )
        
        frame_count += 1
    
    camera.release()
    cv2.destroyAllWindows()
    
    print(f"\nOptical flow test completed ({frame_count} frames)")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("BetaFly Camera and Optical Flow Test")
    print("=" * 50)
    
    if not test_camera():
        print("\nCamera test failed!")
        sys.exit(1)
    
    if not test_optical_flow():
        print("\nOptical flow test failed!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)
