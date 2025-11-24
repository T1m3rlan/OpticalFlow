// Betafly Web Interface
let config = {};
let updateInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    startStatusUpdates();
});

function getNumberInput(id, fallback = 0) {
    const value = parseFloat(document.getElementById(id).value);
    return isNaN(value) ? fallback : value;
}

function getIntInput(id, fallback = 0) {
    const value = parseInt(document.getElementById(id).value, 10);
    return isNaN(value) ? fallback : value;
}

// API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`/api/${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        updateConnectionStatus(false);
        return { success: false, error: error.message };
    }
}

// Update connection status
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-status');
    const text = document.getElementById('connection-text');
    
    if (connected) {
        indicator.classList.add('connected');
        indicator.classList.remove('disconnected');
        text.textContent = 'Connected';
    } else {
        indicator.classList.remove('connected');
        indicator.classList.add('disconnected');
        text.textContent = 'Disconnected';
    }
}

// Load configuration
async function loadConfig() {
    const result = await apiCall('config');
    if (result.success) {
        config = result.config;
        updateConfigUI();
        console.log('Configuration loaded');
    }
}

// Update UI with config values
function updateConfigUI() {
    const sensorConfig = config.sensor || {};
    const trackerConfig = config.tracker || {};
    const pidConfig = config.pid || {};
    const stabilizerConfig = config.stabilizer || {};
    const controlConfig = config.control || {};
    const cameraConfig = config.camera || {};

    // Sensor tab
    document.getElementById('sensor-rotation').value = sensorConfig.rotation ?? 0;
    document.getElementById('scale-factor').value = trackerConfig.scale_factor ?? 0.001;

    const cameraTypeSelect = document.getElementById('camera-type-select');
    const cameraType = sensorConfig.type || 'pmw3901';
    cameraTypeSelect.value = cameraType;
    document.getElementById('i2c-address').value = sensorConfig.i2c_address ?? 41;
    updateCameraType();

    const heightValue = trackerConfig.initial_height ?? 0.5;
    document.getElementById('height-input').value = heightValue;
    document.getElementById('height-slider').value = heightValue;
    
    // PID tab
    document.getElementById('pid-x-kp').value = pidConfig.position_x?.kp ?? 0.5;
    document.getElementById('pid-x-ki').value = pidConfig.position_x?.ki ?? 0.1;
    document.getElementById('pid-x-kd').value = pidConfig.position_x?.kd ?? 0.2;
    document.getElementById('pid-y-kp').value = pidConfig.position_y?.kp ?? 0.5;
    document.getElementById('pid-y-ki').value = pidConfig.position_y?.ki ?? 0.1;
    document.getElementById('pid-y-kd').value = pidConfig.position_y?.kd ?? 0.2;
    
    // Control tab
    document.getElementById('update-rate').value = controlConfig.update_rate_hz ?? 50;
    document.getElementById('max-tilt').value = stabilizerConfig.max_tilt_angle ?? 15;
    document.getElementById('velocity-damping').value = stabilizerConfig.velocity_damping ?? 0.3;
    
    // Camera tab
    document.getElementById('camera-device').value = cameraConfig.device ?? '/dev/video0';
    document.getElementById('camera-width').value = cameraConfig.width ?? 640;
    document.getElementById('camera-height').value = cameraConfig.height ?? 480;
    document.getElementById('camera-fps').value = cameraConfig.fps ?? 30;
}

// Save configuration
async function saveConfig() {
    const sensorConfig = config.sensor || {};
    const trackerConfig = config.tracker || {};
    const cameraConfig = config.camera || {};

    // Build config object from UI
    const newConfig = {
        sensor: {
            spi_bus: sensorConfig.spi_bus ?? 0,
            spi_device: sensorConfig.spi_device ?? 0,
            rotation: getIntInput('sensor-rotation', sensorConfig.rotation ?? 0),
            type: document.getElementById('camera-type-select').value,
            i2c_bus: sensorConfig.i2c_bus ?? 1,
            i2c_address: getIntInput('i2c-address', sensorConfig.i2c_address ?? 41)
        },
        tracker: {
            scale_factor: getNumberInput('scale-factor', trackerConfig.scale_factor ?? 0.001),
            initial_height: getNumberInput('height-input', trackerConfig.initial_height ?? 0.5)
        },
        pid: {
            position_x: {
                kp: getNumberInput('pid-x-kp', 0.5),
                ki: getNumberInput('pid-x-ki', 0.1),
                kd: getNumberInput('pid-x-kd', 0.2)
            },
            position_y: {
                kp: getNumberInput('pid-y-kp', 0.5),
                ki: getNumberInput('pid-y-ki', 0.1),
                kd: getNumberInput('pid-y-kd', 0.2)
            }
        },
        stabilizer: {
            velocity_damping: getNumberInput('velocity-damping', config.stabilizer?.velocity_damping ?? 0.3),
            max_tilt_angle: getNumberInput('max-tilt', config.stabilizer?.max_tilt_angle ?? 15)
        },
        control: {
            update_rate_hz: getIntInput('update-rate', config.control?.update_rate_hz ?? 50)
        },
        camera: {
            device: document.getElementById('camera-device').value || cameraConfig.device || 0,
            width: getIntInput('camera-width', cameraConfig.width ?? 640),
            height: getIntInput('camera-height', cameraConfig.height ?? 480),
            fps: getIntInput('camera-fps', cameraConfig.fps ?? 30),
            method: cameraConfig.method || 'farneback',
            deinterlace: cameraConfig.deinterlace ?? true
        },
        logging: config.logging || { enabled: false, file: 'flight_log.csv' },
        output: config.output || { interface: 'mavlink', port: '/dev/ttyAMA0', baudrate: 115200 },
        stick_input: config.stick_input || {
            enabled: false,
            protocol: 'mock',
            device: '/dev/ttyAMA0',
            channels: 8,
            mix_ratio: 0.5,
            mode_channel: 4
        },
        web_interface: config.web_interface || {
            enabled: true,
            host: '0.0.0.0',
            port: 8080
        }
    };
    
    const result = await apiCall('config', 'POST', newConfig);
    if (result.success) {
        alert('Configuration saved successfully!');
        config = newConfig;
    } else {
        alert('Failed to save configuration: ' + result.error);
    }
}

// Start status updates
function startStatusUpdates() {
    updateInterval = setInterval(updateStatus, 100); // 10Hz updates
}

// Update system status
async function updateStatus() {
    const result = await apiCall('state');
    if (result.success) {
        updateConnectionStatus(true);
        const state = result.state;
        
        // Update mode badge
        const modeBadge = document.getElementById('mode-badge');
        modeBadge.textContent = state.mode.toUpperCase().replace('_', ' ');
        modeBadge.className = 'mode-badge ' + state.mode;
        
        // Update camera type
        document.getElementById('camera-type').textContent = state.camera_type.toUpperCase();
        
        // Update surface quality
        const quality = state.surface_quality;
        document.getElementById('quality-fill').style.width = (quality / 255 * 100) + '%';
        document.getElementById('quality-value').textContent = quality;
        
        // Update height
        document.getElementById('height-display').textContent = state.height.toFixed(2) + ' m';
        
        // Update position display
        updatePositionDisplay(state.position.x, state.position.y);
        document.getElementById('pos-x').textContent = state.position.x.toFixed(3) + ' m';
        document.getElementById('pos-y').textContent = state.position.y.toFixed(3) + ' m';
        
        // Update velocity
        document.getElementById('vel-x').textContent = state.velocity.x.toFixed(3) + ' m/s';
        document.getElementById('vel-y').textContent = state.velocity.y.toFixed(3) + ' m/s';
        
        // Update corrections
        updateCorrectionBar('pitch', state.corrections.pitch);
        updateCorrectionBar('roll', state.corrections.roll);
        document.getElementById('pitch-value').textContent = state.corrections.pitch.toFixed(1) + '°';
        document.getElementById('roll-value').textContent = state.corrections.roll.toFixed(1) + '°';
        
        // Update stick inputs
        updateStickBar('pitch', state.stick_inputs.pitch);
        updateStickBar('roll', state.stick_inputs.roll);
        updateStickBar('throttle', state.stick_inputs.throttle);
        updateStickBar('yaw', state.stick_inputs.yaw);
        document.getElementById('stick-pitch-value').textContent = state.stick_inputs.pitch;
        document.getElementById('stick-roll-value').textContent = state.stick_inputs.roll;
        document.getElementById('stick-throttle-value').textContent = state.stick_inputs.throttle;
        document.getElementById('stick-yaw-value').textContent = state.stick_inputs.yaw;
    }
}

// Update position 2D display
function updatePositionDisplay(x, y) {
    const indicator = document.getElementById('drone-position');
    const container = document.querySelector('.position-2d');
    
    // Scale position to pixels (1 meter = 80 pixels)
    const scale = 80;
    const maxOffset = 100; // pixels
    
    const offsetX = Math.max(-maxOffset, Math.min(maxOffset, x * scale));
    const offsetY = Math.max(-maxOffset, Math.min(maxOffset, -y * scale)); // Negative because Y is inverted
    
    indicator.style.transform = `translate(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px))`;
}

// Update correction bar
function updateCorrectionBar(type, value) {
    const bar = document.getElementById(type + '-bar');
    const maxAngle = 15; // degrees
    
    // Convert angle to percentage (0-100%)
    const percentage = Math.abs(value) / maxAngle * 50; // 50% = max deflection
    
    if (value >= 0) {
        bar.style.left = '50%';
        bar.style.width = percentage + '%';
    } else {
        bar.style.left = (50 - percentage) + '%';
        bar.style.width = percentage + '%';
    }
}

// Update stick bar
function updateStickBar(channel, value) {
    const bar = document.getElementById('stick-' + channel);
    
    // Assuming value range is -500 to 500 (typical RC range centered at 1500)
    const percentage = Math.abs(value) / 500 * 50; // 50% = max deflection
    
    if (value >= 0) {
        bar.style.left = '50%';
        bar.style.width = percentage + '%';
    } else {
        bar.style.left = (50 - percentage) + '%';
        bar.style.width = percentage + '%';
    }
}

// Control commands
async function setMode(mode) {
    const result = await apiCall('command', 'POST', {
        command: 'set_mode',
        params: { mode: mode }
    });
    
    if (result.success) {
        console.log('Mode set to:', mode);
    } else {
        alert('Failed to set mode: ' + result.error);
    }
}

async function resetPosition() {
    const result = await apiCall('command', 'POST', {
        command: 'reset_position'
    });
    
    if (result.success) {
        console.log('Position reset');
    }
}

function updateHeightSlider(value) {
    document.getElementById('height-input').value = value;
}

async function setHeight(value) {
    const height = parseFloat(value);
    document.getElementById('height-slider').value = height;
    
    const result = await apiCall('command', 'POST', {
        command: 'set_height',
        params: { height: height }
    });
    
    if (!result.success) {
        alert('Failed to set height: ' + result.error);
    }
}

// Tab management
function showTab(event, tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Mark button as active
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

// Camera type update
function updateCameraType() {
    const cameraType = document.getElementById('camera-type-select').value;
    console.log('Camera type changed to:', cameraType);
    
    // Show/hide I2C address field for Caddx
    const i2cGroup = document.getElementById('i2c-address-group');
    if (cameraType === 'caddx_infra256') {
        i2cGroup.style.display = 'block';
    } else {
        i2cGroup.style.display = 'none';
    }
    
    // Show/hide camera settings based on type
    const cameraTab = document.getElementById('camera-tab');
    if (cameraType === 'pmw3901' || cameraType === 'caddx_infra256') {
        cameraTab.style.display = 'none';
    } else {
        cameraTab.style.display = 'block';
    }
}
