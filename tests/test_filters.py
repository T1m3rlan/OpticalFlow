from betafly_stabilizer.config import FilterConfig
from betafly_stabilizer.filters import FlowFilter, apply_deadband


def test_deadband_zeroes_small_values():
    assert apply_deadband(0.001, 0.01) == 0.0
    assert apply_deadband(0.02, 0.01) == 0.02


def test_flow_filter_blends_values():
    filt = FlowFilter(FilterConfig(ema_alpha=0.5, median_window=3, deadband=0.0))
    outputs = []
    for vx in [0.1, 0.2, 0.3, 0.4]:
        outputs.append(filt.push(vx, vx)[0])
    assert outputs[0] == 0.1  # first value passes straight through
    assert outputs[-1] < 0.4  # EMA should lag behind the newest value
