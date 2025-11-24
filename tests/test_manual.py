from betafly_stabilizer.manual import ManualOverrideState


def test_manual_override_respects_enable_and_reset():
    state = ManualOverrideState()
    # Disabled by default
    state.update(0.5, -0.3)
    assert state.get_target() == (0.0, 0.0)

    state.set_enabled(True)
    state.update(0.25, -0.1)
    assert state.get_target() == (0.25, -0.1)

    state.reset()
    assert state.get_target() == (0.0, 0.0)

    state.update(-0.2, 0.4)
    assert state.get_target() == (-0.2, 0.4)

    state.set_enabled(False)
    assert state.get_target() == (0.0, 0.0)
