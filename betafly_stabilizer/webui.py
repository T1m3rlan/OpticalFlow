"""Simple Flask-based GUI for editing Betafly configs."""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, redirect, render_template_string, request, url_for, flash

try:
    import yaml
except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required for the Betafly web UI.") from exc

from .config import StabilizerConfig, load_config

FORM_FIELDS = {
    "control_rate_hz": {"type": float, "label": "Control Rate (Hz)", "step": "0.1"},
    "preview": {"type": bool, "label": "Preview Window"},
    "camera.source": {"type": str, "label": "Camera Source (opencv/picamera/analog)"},
    "camera.width": {"type": int, "label": "Camera Width"},
    "camera.height": {"type": int, "label": "Camera Height"},
    "camera.framerate": {"type": int, "label": "Camera FPS"},
    "camera.analog_profile": {"type": str, "label": "Analog Profile"},
    "tracker.max_corners": {"type": int, "label": "Tracker Max Corners"},
    "tracker.quality_level": {"type": float, "label": "Tracker Quality"},
    "pan_pid.kp": {"type": float, "label": "Pan Kp"},
    "pan_pid.ki": {"type": float, "label": "Pan Ki"},
    "pan_pid.kd": {"type": float, "label": "Pan Kd"},
    "tilt_pid.kp": {"type": float, "label": "Tilt Kp"},
    "tilt_pid.ki": {"type": float, "label": "Tilt Ki"},
    "tilt_pid.kd": {"type": float, "label": "Tilt Kd"},
    "manual_input.enabled": {"type": bool, "label": "Manual Input Enabled"},
    "manual_input.scale": {"type": float, "label": "Manual Input Scale"},
}

INDEX_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Betafly Control Panel</title>
    <style>
      body { font-family: sans-serif; margin: 2rem; background: #0f111a; color: #e3e7ff; }
      form { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
      .card { padding: 1rem; border-radius: 0.5rem; background: #1b2033; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
      label { display: flex; flex-direction: column; font-size: 0.9rem; gap: 0.3rem; }
      input, select, textarea { padding: 0.5rem; border-radius: 0.4rem; border: none; background: #262c45; color: #e3e7ff; }
      button { grid-column: 1 / -1; padding: 0.8rem 1.2rem; border: none; border-radius: 0.4rem; background: #4c8bf5; color: white; font-size: 1rem; cursor: pointer; }
      a { color: #4c8bf5; }
      .flash { padding: 0.5rem 1rem; background: #274060; border-radius: 0.4rem; margin-bottom: 1rem; display: inline-block; }
    </style>
  </head>
  <body>
    <h1>Betafly Optical Stabilizer</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="post">
      {% for field, meta in fields.items() %}
        <div class="card">
          <label>
            {{ meta.label }}
            {% if meta.type == bool %}
              <input type="checkbox" name="{{ field }}" value="true" {% if values[field] %}checked{% endif %}>
            {% else %}
              <input type="{{ meta.input_type }}" step="{{ meta.step }}" name="{{ field }}" value="{{ values[field] }}">
            {% endif %}
          </label>
        </div>
      {% endfor %}
      <button type="submit">Save Changes</button>
    </form>
    <p style="margin-top:2rem;">
      <a href="{{ url_for('raw_editor') }}">Open raw YAML editor</a> |
      <a href="{{ url_for('get_config_json') }}">Download JSON snapshot</a>
    </p>
  </body>
</html>
"""

RAW_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Betafly Config Editor</title>
    <style>
      body { font-family: monospace; margin: 1.5rem; background: #0f111a; color: #e3e7ff; }
      textarea { width: 100%; min-height: 70vh; padding: 1rem; background: #1b2033; color: #e3e7ff; border: none; border-radius: 0.5rem; }
      button { margin-top: 1rem; padding: 0.8rem 1.3rem; border: none; border-radius: 0.4rem; background: #4c8bf5; color: #fff; cursor: pointer; }
      a { color: #4c8bf5; }
    </style>
  </head>
  <body>
    <h2>Raw YAML editor</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="post">
      <textarea name="yaml_blob">{{ blob }}</textarea>
      <button type="submit">Save YAML</button>
    </form>
    <p><a href="{{ url_for('index') }}">Back to dashboard</a></p>
  </body>
</html>
"""


def _config_to_dict(config: StabilizerConfig) -> Dict[str, Any]:
    return dataclasses.asdict(config)


def _set_nested(config_dict: Dict[str, Any], dotted_key: str, value: Any) -> None:
    keys = dotted_key.split(".")
    cursor = config_dict
    for key in keys[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[keys[-1]] = value


def _parse_value(raw: str, field_meta: Dict[str, Any], present: bool) -> Any:
    target_type = field_meta["type"]
    if target_type is bool:
        return bool(present and raw in ("on", "true", "1", "yes"))
    if target_type is int:
        return int(raw)
    if target_type is float:
        return float(raw)
    return raw


def _apply_form_updates(form, config_dict: Dict[str, Any]) -> None:
    for field, meta in FORM_FIELDS.items():
        present = field in form
        if meta["type"] is bool:
            raw_val = "true" if present else "false"
            value = _parse_value(raw_val, meta, present)
        else:
            raw_value = form.get(field)
            if raw_value is None:
                continue
            value = _parse_value(raw_value, meta, present)
        _set_nested(config_dict, field, value)


def _save_config_dict(config_path: Path, config_dict: Dict[str, Any]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config_dict, handle, sort_keys=False)


def create_app(config_path: str) -> Flask:
    path = Path(config_path).expanduser()
    app = Flask(__name__)
    app.secret_key = os.environ.get("BETAFLY_WEBUI_SECRET", "betafly-local")

    @app.route("/", methods=["GET", "POST"])
    def index():
        cfg = load_config(path)
        cfg_dict = _config_to_dict(cfg)
        if request.method == "POST":
            try:
                _apply_form_updates(request.form, cfg_dict)
            except ValueError as exc:
                flash(f"Invalid value: {exc}")
            else:
                _save_config_dict(path, cfg_dict)
                flash("Configuration updated successfully.")
                return redirect(url_for("index"))
        values = {}
        for field in FORM_FIELDS:
            keys = field.split(".")
            cursor = cfg_dict
            for key in keys:
                cursor = cursor.get(key, "")
            values[field] = cursor
        for field, meta in FORM_FIELDS.items():
            meta["input_type"] = "text"
            if meta["type"] in (int, float):
                meta["input_type"] = "number"
            meta.setdefault("step", "any")
        return render_template_string(INDEX_TEMPLATE, fields=FORM_FIELDS, values=values)

    @app.route("/config/raw", methods=["GET", "POST"])
    def raw_editor():
        blob = path.read_text(encoding="utf-8") if path.exists() else ""
        if request.method == "POST":
            yaml_blob = request.form.get("yaml_blob", "")
            try:
                yaml.safe_load(yaml_blob)
            except yaml.YAMLError as exc:  # pragma: no cover - formatting errors
                flash(f"YAML error: {exc}")
            else:
                path.write_text(yaml_blob, encoding="utf-8")
                flash("YAML saved.")
                return redirect(url_for("raw_editor"))
        return render_template_string(RAW_TEMPLATE, blob=blob)

    @app.route("/api/config", methods=["GET"])
    def get_config_json():
        cfg = load_config(path)
        return jsonify(_config_to_dict(cfg))

    return app


def run_webui(config_path: str, host: str = "0.0.0.0", port: int = 8080, open_browser: bool = False) -> None:
    app = create_app(config_path)
    if open_browser:
        import webbrowser

        webbrowser.open(f"http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
