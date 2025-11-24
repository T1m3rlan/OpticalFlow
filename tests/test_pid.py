import math

from betafly_stabilizer.config import PIDConfig
from betafly_stabilizer.controller import PIDController


def test_pid_deadband():
    controller = PIDController(PIDConfig(kp=1.0, deadband=0.5))
    state = controller.update(0.2, 0.01)
    assert math.isclose(state.output, 0.0, abs_tol=1e-6)


def test_pid_integral_clamp():
    config = PIDConfig(kp=0.0, ki=1.0, integrator_limit=0.1)
    controller = PIDController(config)
    for _ in range(10):
        controller.update(1.0, 0.1)
    assert abs(controller._integral) <= config.integrator_limit  # pylint: disable=protected-access
