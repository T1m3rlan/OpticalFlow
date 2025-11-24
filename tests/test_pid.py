from betafly_stabilizer.pid import PIDController, PIDGains


def test_pid_clamps_output_and_integral():
    gains = PIDGains(kp=1.0, ki=1.0, kd=0.0, i_clamp=0.5, output_limit=0.6)
    pid = PIDController(gains)

    # Feed constant error to accumulate integral but ensure clamp applies.
    outputs = []
    for _ in range(10):
        outputs.append(pid.update(1.0, 0.1))

    assert max(outputs) <= gains.output_limit + 1e-6

    # Negative error should drive integral back down.
    for _ in range(10):
        pid.update(-1.0, 0.1)

    assert abs(pid._integral) <= gains.i_clamp + 1e-6
