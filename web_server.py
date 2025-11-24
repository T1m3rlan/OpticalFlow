#!/usr/bin/env python3
"""
Web Server for BetaFly Stabilization System
Provides GUI for configuration and monitoring
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import logging
from threading import Lock
from config import Config, ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'betafly-stabilization-secret-key'

# Global config manager
config_manager = ConfigManager()
config_lock = Lock()

# Controller instance (will be set by main application)
controller_instance = None


@app.route('/')
def index():
    """Serve main GUI page"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    with config_lock:
        config_dict = config_manager.to_dict()
    return jsonify(config_dict)


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        
        with config_lock:
            config_manager.update_from_dict(data)
            config_manager.save()
            
            # Update controller if running
            if controller_instance:
                controller_instance.update_config(config_manager.config)
        
        return jsonify({'status': 'success', 'message': 'Configuration updated'})
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset configuration to defaults"""
    try:
        with config_lock:
            config_manager.reset_to_defaults()
            config_manager.save()
            
            if controller_instance:
                controller_instance.update_config(config_manager.config)
        
        return jsonify({'status': 'success', 'message': 'Configuration reset to defaults'})
    except Exception as e:
        logger.error(f"Error resetting config: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get controller status"""
    if controller_instance:
        status = {
            'running': controller_instance.running,
            'mode': controller_instance.control_mode,
            'position': {
                'x': float(controller_instance.current_position[0]),
                'y': float(controller_instance.current_position[1])
            },
            'target': {
                'x': float(controller_instance.target_position[0]),
                'y': float(controller_instance.target_position[1])
            },
            'manual_input': {
                'x': float(controller_instance.manual_input_x) if hasattr(controller_instance, 'manual_input_x') else 0.0,
                'y': float(controller_instance.manual_input_y) if hasattr(controller_instance, 'manual_input_y') else 0.0
            },
            'fps': controller_instance.get_fps() if hasattr(controller_instance, 'get_fps') else 0.0
        }
    else:
        status = {
            'running': False,
            'mode': 'stopped',
            'position': {'x': 0, 'y': 0},
            'target': {'x': 0, 'y': 0},
            'manual_input': {'x': 0, 'y': 0},
            'fps': 0.0
        }
    
    return jsonify(status)


@app.route('/api/control/start', methods=['POST'])
def start_controller():
    """Start the controller"""
    try:
        if controller_instance and not controller_instance.running:
            # Start in background thread
            import threading
            thread = threading.Thread(target=controller_instance.run, daemon=True)
            thread.start()
            return jsonify({'status': 'success', 'message': 'Controller started'})
        else:
            return jsonify({'status': 'error', 'message': 'Controller already running or not initialized'}), 400
    except Exception as e:
        logger.error(f"Error starting controller: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/control/stop', methods=['POST'])
def stop_controller():
    """Stop the controller"""
    try:
        if controller_instance:
            controller_instance.running = False
            return jsonify({'status': 'success', 'message': 'Controller stopped'})
        else:
            return jsonify({'status': 'error', 'message': 'Controller not initialized'}), 400
    except Exception as e:
        logger.error(f"Error stopping controller: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/control/mode', methods=['POST'])
def set_control_mode():
    """Set control mode (auto/manual)"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'auto')
        
        if controller_instance:
            controller_instance.set_control_mode(mode)
            return jsonify({'status': 'success', 'message': f'Control mode set to {mode}'})
        else:
            return jsonify({'status': 'error', 'message': 'Controller not initialized'}), 400
    except Exception as e:
        logger.error(f"Error setting control mode: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/cameras', methods=['GET'])
def list_cameras():
    """List available cameras"""
    import cv2
    cameras = []
    
    # Try to detect cameras
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append({
                'index': i,
                'name': f'Camera {i}',
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            })
            cap.release()
    
    return jsonify({'cameras': cameras})


@app.route('/api/control/manual', methods=['POST'])
def set_manual_input():
    """Set manual input from web interface"""
    try:
        data = request.get_json()
        x = float(data.get('x', 0.0))
        y = float(data.get('y', 0.0))
        
        if controller_instance:
            controller_instance.set_manual_input(x, y)
            return jsonify({'status': 'success', 'message': 'Manual input set'})
        else:
            return jsonify({'status': 'error', 'message': 'Controller not initialized'}), 400
    except Exception as e:
        logger.error(f"Error setting manual input: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


def set_controller_instance(controller):
    """Set the controller instance for API access"""
    global controller_instance
    controller_instance = controller


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run the web server"""
    app.run(host=host, port=port, debug=debug, threaded=True)
