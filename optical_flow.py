import cv2
import numpy as np

class OpticalFlowSensor:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.reload_config()
        
        self.lk_params = dict(winSize=(15, 15),
                              maxLevel=2,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        self.old_gray = None
        self.p0 = None
        self.cap = None
        self.init_camera()

    def reload_config(self):
        self.camera_index = self.settings.get("camera_index", 0)
        self.width = self.settings.get("camera_width", 320)
        self.height = self.settings.get("camera_height", 240)
        self.framerate = self.settings.get("camera_framerate", 30)
        
        self.feature_params = dict(maxCorners=self.settings.get("max_corners", 100),
                                   qualityLevel=self.settings.get("quality_level", 0.3),
                                   minDistance=self.settings.get("min_distance", 7),
                                   blockSize=self.settings.get("block_size", 7))

    def init_camera(self):
        if self.cap is not None:
            self.cap.release()
            
        # Try to open camera
        # If camera_index is a string path (e.g., /dev/video2), pass string
        # If it's an int (or string representation of int), pass int
        try:
            idx = int(self.camera_index)
        except ValueError:
            idx = self.camera_index
            
        print(f"Opening camera: {idx}")
        self.cap = cv2.VideoCapture(idx)
        
        if not self.cap.isOpened():
            print(f"Failed to open camera {idx}")
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.framerate)
        
        # Initialize first frame
        ret, frame = self.cap.read()
        if ret:
            self.old_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.p0 = cv2.goodFeaturesToTrack(self.old_gray, mask=None, **self.feature_params)
            return True
        else:
            print("Failed to read first frame")
            return False

    def read_flow(self):
        """
        Returns the average movement vector (dx, dy) in pixels.
        """
        if self.cap is None or not self.cap.isOpened():
            # Try to reconnect occasionally?
            return 0, 0
            
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
        if self.cap:
            self.cap.release()
