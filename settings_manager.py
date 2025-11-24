import json
import os
from threading import Lock

class SettingsManager:
    def __init__(self, filepath='settings.json'):
        self.filepath = filepath
        self.settings = {}
        self.lock = Lock()
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, 'r') as f:
                        self.settings = json.load(f)
                except json.JSONDecodeError:
                    print("Error decoding settings.json. Using defaults.")
                    self._set_defaults()
            else:
                self._set_defaults()
                self.save()

    def save(self):
        with self.lock:
            try:
                with open(self.filepath, 'w') as f:
                    json.dump(self.settings, f, indent=4)
            except Exception as e:
                print(f"Error saving settings: {e}")

    def _set_defaults(self):
        # Defaults in case file is missing/corrupt
        self.settings = {
            "serial_port": "/dev/ttyS0",
            "baud_rate": 115200,
            "camera_index": 0,
            "camera_width": 320,
            "camera_height": 240,
            "camera_framerate": 30,
            "max_corners": 100,
            "quality_level": 0.3,
            "min_distance": 7,
            "block_size": 7,
            "p_gain": 0.1,
            "i_gain": 0.0,
            "d_gain": 0.01,
            "vel_scale": 0.1,
            "rc_mid": 1500,
            "rc_deadband": 20
        }

    def get(self, key, default=None):
        with self.lock:
            return self.settings.get(key, default)

    def set(self, key, value):
        with self.lock:
            self.settings[key] = value
        self.save()
        
    def get_all(self):
        with self.lock:
            return self.settings.copy()
            
    def update_from_dict(self, new_settings):
        with self.lock:
            # Convert types if necessary (basic type inference)
            for k, v in new_settings.items():
                if k in self.settings:
                    target_type = type(self.settings[k])
                    try:
                        if target_type == int:
                            self.settings[k] = int(v)
                        elif target_type == float:
                            self.settings[k] = float(v)
                        elif target_type == str:
                            self.settings[k] = str(v)
                        # Add more types if needed
                    except ValueError:
                        pass # Keep old value if conversion fails
            
        self.save()
