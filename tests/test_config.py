from betafly_stabilizer.config import load_config, ManualInputConfig
from betafly_stabilizer.manual_input import ManualInputSource


def test_load_config_with_analog_and_manual(tmp_path):
    config_yaml = """
camera:
  source: analog
  analog_profile: pal
  analog_profiles:
    pal:
      device: /dev/video1
      width: 720
      height: 576
      framerate: 25
manual_input:
  enabled: true
  scale: 0.3
"""
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(config_yaml)
    cfg = load_config(cfg_path)
    profile = cfg.camera.active_analog_profile()
    assert profile.device == "/dev/video1"
    assert profile.height == 576
    assert cfg.manual_input.enabled is True
    assert cfg.manual_input.scale == 0.3


def test_manual_input_virtual_mode():
    config = ManualInputConfig(enabled=True, mode="virtual", scale=0.5)
    src = ManualInputSource(config)
    src.inject_virtual(0.4, -0.2)
    roll, pitch = src.get_offsets()
    assert abs(roll - 0.4) < 1e-6
    assert abs(pitch + 0.2) < 1e-6
