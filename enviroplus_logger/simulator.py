from __future__ import annotations

import math
import random
import time

from enviroplus_logger.telemetry import TelemetryReading


def simulated_reading(
    device_id: str, sequence: int, *, seed: int = 42, sampled_at_ms: int | None = None
) -> TelemetryReading:
    """Return a repeatable, plausible sensor sample for offline development."""
    generator = random.Random(seed + sequence)
    phase = sequence / 12
    return TelemetryReading(
        device_id=device_id,
        temperature_c=round(21 + 2 * math.sin(phase) + generator.uniform(-0.2, 0.2), 2),
        pressure_hpa=round(1013 + generator.uniform(-2, 2), 2),
        humidity_pct=round(48 + 5 * math.sin(phase / 2) + generator.uniform(-1, 1), 2),
        illuminance_lux=round(
            max(0, 250 * math.sin(phase) + generator.uniform(0, 15)), 2
        ),
        proximity=round(generator.uniform(0, 10), 2),
        oxidising_ohm=round(generator.uniform(90_000, 120_000), 2),
        reducing_ohm=round(generator.uniform(70_000, 100_000), 2),
        nh3_ohm=round(generator.uniform(80_000, 110_000), 2),
        sampled_at_ms=sampled_at_ms or int(time.time() * 1000),
    )
