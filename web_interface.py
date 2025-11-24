#!/usr/bin/env python3
"""
Web Interface for Betafly Stabilization System
Provides GUI for configuration and real-time monitoring
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import threading
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global state
system_state = {
    'running': False,
    'mode': 'off',
    'position': {'x': 0.0, 'y': 0.0},
    'velocity': {'x': 0.0, 'y': 0.0},
    'corrections': {'pitch': 0.0, 'roll': 0.0},
    'surface_quality': 0,
    'height': 0.5,
    'stick_inputs': {'pitch': 0, 'roll': 0, 'throttle': 0, 'yaw': 0},
    'camera_type': 'pmw3901',
    'last_update': time.time()
}

config_lock = threading.Lock()
state_lock = threading.Lock()

CONFIG_FILE = 'config.json'


@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        with config_lock:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        new_config = request.json
        
        # Validate config
        if not validate_config(new_config):
            return jsonify({'success': False, 'error': 'Invalid configuration'}), 400
        
        # Save to file
        with config_lock:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(new_config, f, indent=2)
        
        logger.info("Configuration updated via web interface")
        return jsonify({'success': True, 'message': 'Configuration saved'})
    
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current system state"""
    with state_lock:
        return jsonify({
            'success': True,
            'state': system_state.copy()
        })


@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to system"""
    try:
        cmd = request.json.get('command')
        params = request.json.get('params', {})
        
        if cmd == 'set_mode':
            mode = params.get('mode')
            if mode in ['off', 'velocity_damping', 'position_hold']:
                with state_lock:
                    system_state['mode'] = mode
                return jsonify({'success': True, 'message': f'Mode set to {mode}'})
            else:
                return jsonify({'success': False, 'error': 'Invalid mode'}), 400
        
        elif cmd == 'reset_position':
            with state_lock:
                system_state['position'] = {'x': 0.0, 'y': 0.0}
            return jsonify({'success': True, 'message': 'Position reset'})
        
        elif cmd == 'set_height':
            height = float(params.get('height', 0.5))
            if 0.1 <= height <= 5.0:
                with state_lock:
                    system_state['height'] = height
                return jsonify({'success': True, 'message': f'Height set to {height}m'})
            else:
                return jsonify({'success': False, 'error': 'Height out of range'}), 400
        
        elif cmd == 'hold_position':
            with state_lock:
                system_state['mode'] = 'position_hold'
            return jsonify({'success': True, 'message': 'Position hold activated'})
        
        else:
            return jsonify({'success': False, 'error': 'Unknown command'}), 400
    
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/camera_types', methods=['GET'])
def get_camera_types():
    """Get available camera types"""
    camera_types = [
        {'id': 'pmw3901', 'name': 'PMW3901 Optical Flow Sensor (SPI)'},
        {'id': 'caddx_infra256', 'name': 'Caddx Infra 256 (I2C)'},
        {'id': 'usb_camera', 'name': 'USB Camera (OpenCV)'},
        {'id': 'csi_camera', 'name': 'Raspberry Pi Camera (CSI)'},
        {'id': 'analog_usb', 'name': 'Analog Camera via USB Capture'},
        {'id': 'opencv_any', 'name': 'Any OpenCV Compatible Camera'}
    ]
    return jsonify({'success': True, 'cameras': camera_types})


def validate_config(config):
    """Validate configuration structure"""
    required_keys = ['sensor', 'tracker', 'pid', 'stabilizer', 'control']
    return all(key in config for key in required_keys)


def update_system_state(stabilizer_instance):
    """Update system state from stabilizer instance (called by main system)"""
    global system_state
    # This function will be called by the main stabilizer to update state
    pass


def start_web_server(host='0.0.0.0', port=8080, debug=False):
    """Start the web server"""
    logger.info(f"Starting web interface on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_web_server(debug=True)
