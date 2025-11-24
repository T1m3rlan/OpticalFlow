import cv2
import numpy as np
import config

class OpticalFlowSensor:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FRAMERATE)
        
        self.feature_params = dict(maxCorners=config.MAX_CORNERS,
                                   qualityLevel=config.QUALITY_LEVEL,
                                   minDistance=config.MIN_DISTANCE,
                                   blockSize=config.BLOCK_SIZE)
        
        self.lk_params = dict(winSize=(15, 15),
                              maxLevel=2,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        self.old_gray = None
        self.p0 = None
        
        # Initialize first frame
        ret, frame = self.cap.read()
        if ret:
            self.old_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.p0 = cv2.goodFeaturesToTrack(self.old_gray, mask=None, **self.feature_params)

    def read_flow(self):
        """
        Returns the average movement vector (dx, dy) in pixels.
        """
        ret, frame = self.cap.read()
        if not ret:
            return 0, 0
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # If we lost tracking or just starting, find features
        if self.p0 is None or len(self.p0) < 10:
            self.p0 = cv2.goodFeaturesToTrack(self.old_gray, mask=None, **self.feature_params)
            if self.p0 is None:
                 # Update old_gray for next iteration even if no features found
                self.old_gray = frame_gray.copy()
                return 0, 0

        # Calculate optical flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, frame_gray, self.p0, None, **self.lk_params)
        
        dx = 0
        dy = 0
        
        if p1 is not None:
            # Select good points
            good_new = p1[st == 1]
            good_old = self.p0[st == 1]
            
            # Calculate average movement
            if len(good_new) > 0:
                movement = good_new - good_old
                dx = np.mean(movement[:, 0])
                dy = np.mean(movement[:, 1])
            
            # Update the previous frame and previous points
            self.old_gray = frame_gray.copy()
            self.p0 = good_new.reshape(-1, 1, 2)
        else:
            self.old_gray = frame_gray.copy()
            self.p0 = None

        return dx, dy

    def close(self):
        self.cap.release()
