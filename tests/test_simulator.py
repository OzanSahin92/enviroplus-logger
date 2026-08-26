from enviroplus_logger.simulator import simulated_reading


def test_simulator_is_repeatable_for_fixed_time() -> None:
    first = simulated_reading("sim-one", 4, seed=7, sampled_at_ms=1_700_000_000_000)
    second = simulated_reading("sim-one", 4, seed=7, sampled_at_ms=1_700_000_000_000)

    assert first == second
    assert first.topic == "enviroplus/sim-one/telemetry"
    assert 0 <= first.humidity_pct <= 100
