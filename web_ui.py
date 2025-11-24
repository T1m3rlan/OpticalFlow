from flask import Flask, render_template, request, jsonify
from settings_manager import SettingsManager
import threading

app = Flask(__name__)
settings_manager = SettingsManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(settings_manager.get_all())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    new_settings = request.json
    settings_manager.update_from_dict(new_settings)
    return jsonify({"status": "success", "settings": settings_manager.get_all()})

def start_web_server(port=5000):
    # Disable Flask banner to keep console clean
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    start_web_server()
