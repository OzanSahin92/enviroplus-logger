import json

import pytest

from enviroplus_logger.telemetry import TelemetryReading


def reading(**overrides) -> TelemetryReading:
    values = {
        "device_id": "living-room",
        "temperature_c": 21.5,
        "pressure_hpa": 1012.4,
        "humidity_pct": 48.0,
        "illuminance_lux": 120.0,
        "proximity": 0.0,
        "oxidising_ohm": 100.0,
        "reducing_ohm": 200.0,
        "nh3_ohm": 300.0,
        "sampled_at_ms": 1_725_000_000_000,
    }
    values.update(overrides)
    return TelemetryReading(**values)


def test_serialises_versioned_payload_without_repeating_device_id():
    sample = reading()
    payload = json.loads(sample.to_json())
    assert sample.topic == "enviroplus/living-room/telemetry"
    assert payload["schema_version"] == 1
    assert payload["temperature_c"] == 21.5
    assert "device_id" not in payload


@pytest.mark.parametrize("humidity", [-0.1, 100.1])
def test_rejects_invalid_humidity(humidity):
    with pytest.raises(ValueError, match="humidity_pct"):
        reading(humidity_pct=humidity)


def test_rejects_non_finite_measurements():
    with pytest.raises(ValueError, match="finite"):
        reading(temperature_c=float("nan"))
