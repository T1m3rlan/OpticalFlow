"""Local FastAPI server exposing config editor and manual stick UI."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

from .config import StabilizerConfig, apply_overrides, config_to_dict
from .manual import ManualOverrideState


class ManualPayload(BaseModel):
    vx: float = Field(..., ge=-1.0, le=1.0)
    vy: float = Field(..., ge=-1.0, le=1.0)


class WebConfigServer:
    def __init__(
        self,
        config: StabilizerConfig,
        manual_state: ManualOverrideState,
        config_path: Optional[Path] = None,
    ):
        self._config = config
        self._manual_state = manual_state
        self._config_path = config_path
        self._lock = threading.Lock()
        self._app = FastAPI()
        self._configure_routes()
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    def _configure_routes(self) -> None:
        @self._app.get("/", response_class=HTMLResponse)
        async def index() -> HTMLResponse:
            return HTMLResponse(_INDEX_HTML)

        @self._app.get("/api/config")
        async def get_config() -> Mapping[str, Any]:
            with self._lock:
                return config_to_dict(self._config)

        @self._app.post("/api/config")
        async def post_config(payload: Mapping[str, Any]) -> Mapping[str, Any]:
            if not isinstance(payload, Mapping):
                raise HTTPException(status_code=400, detail="Config payload must be an object")
            with self._lock:
                apply_overrides(self._config, payload)
                self._manual_state.set_enabled(self._config.manual_input.enabled)
                self._persist_locked()
                return config_to_dict(self._config)

        @self._app.post("/api/manual")
        async def post_manual(payload: ManualPayload) -> Mapping[str, float]:
            max_vel = self._config.manual_input.max_velocity
            self._manual_state.update(payload.vx * max_vel, payload.vy * max_vel)
            return {"vx": payload.vx, "vy": payload.vy}

        @self._app.post("/api/manual/reset")
        async def reset_manual() -> Mapping[str, float]:
            self._manual_state.reset()
            return {"vx": 0.0, "vy": 0.0}

    def _persist_locked(self) -> None:
        if not self._config_path:
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = config_to_dict(self._config)
        with self._config_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(json.loads(json.dumps(data)), handle, sort_keys=False)

    def start(self, host: str, port: int) -> None:
        config = uvicorn.Config(self._app, host=host, port=port, log_level="info")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server and self._server.started:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=1.0)


_INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Betafly Stabilizer</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }
    textarea { width: 100%; height: 320px; background: #1e293b; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px; padding: 1rem; }
    button { padding: 0.5rem 1rem; margin-top: 0.5rem; background: #38bdf8; border: none; border-radius: 4px; cursor: pointer; }
    button:disabled { background: #475569; cursor: not-allowed; }
    .panel { margin-bottom: 2rem; background: #111827; padding: 1.5rem; border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.35); }
    input[type=range] { width: 100%; }
    label { display: block; margin-top: 1rem; }
    #status { margin-top: 0.5rem; min-height: 1.5rem; }
  </style>
</head>
<body>
  <h1>Betafly Optical Position Stabilizer</h1>
  <div class="panel">
    <h2>Configuration</h2>
    <p>Edit the JSON below and click save. Restart the stabilizer to apply camera/PID changes.</p>
    <textarea id="configField"></textarea>
    <div>
      <button id="saveBtn">Save Config</button>
      <span id="status"></span>
    </div>
  </div>
  <div class="panel">
    <h2>Manual Stick Override</h2>
    <p>Requires <code>manual_input.enabled</code> to be true. Move sliders to command planar velocity.</p>
    <label>Forward / Back (vx)
      <input type="range" id="vx" min="-1" max="1" step="0.05" value="0" />
    </label>
    <label>Right / Left (vy)
      <input type="range" id="vy" min="-1" max="1" step="0.05" value="0" />
    </label>
    <button id="resetManual">Reset Stick</button>
  </div>
  <script>
    async function loadConfig() {
      const res = await fetch('/api/config');
      const cfg = await res.json();
      document.getElementById('configField').value = JSON.stringify(cfg, null, 2);
    }
    async function saveConfig() {
      try {
        const text = document.getElementById('configField').value;
        const payload = JSON.parse(text);
        const res = await fetch('/api/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        document.getElementById('status').innerText = 'Saved ✔';
      } catch (err) {
        document.getElementById('status').innerText = 'Error: ' + err;
      }
    }
    async function sendManual() {
      const vx = Number(document.getElementById('vx').value);
      const vy = Number(document.getElementById('vy').value);
      await fetch('/api/manual', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({vx, vy})
      });
    }
    async function resetManual() {
      document.getElementById('vx').value = 0;
      document.getElementById('vy').value = 0;
      await fetch('/api/manual/reset', {method: 'POST'});
    }
    document.getElementById('saveBtn').addEventListener('click', saveConfig);
    document.getElementById('vx').addEventListener('input', sendManual);
    document.getElementById('vy').addEventListener('input', sendManual);
    document.getElementById('resetManual').addEventListener('click', resetManual);
    loadConfig();
  </script>
</body>
</html>
"""


__all__ = ["WebConfigServer"]
