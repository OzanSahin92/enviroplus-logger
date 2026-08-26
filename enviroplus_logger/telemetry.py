from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class TelemetryReading:
    device_id: str
    temperature_c: float
    pressure_hpa: float
    humidity_pct: float
    illuminance_lux: float
    proximity: float
    oxidising_ohm: float
    reducing_ohm: float
    nh3_ohm: float
    sampled_at_ms: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise ValueError("device_id must not be empty")
        if self.schema_version != 1:
            raise ValueError("unsupported telemetry schema version")
        if not 0 <= self.humidity_pct <= 100:
            raise ValueError("humidity_pct must be between 0 and 100")
        if self.sampled_at_ms <= 0:
            raise ValueError("sampled_at_ms must be a positive Unix timestamp")
        values = (
            self.temperature_c,
            self.pressure_hpa,
            self.illuminance_lux,
            self.proximity,
            self.oxidising_ohm,
            self.reducing_ohm,
            self.nh3_ohm,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("telemetry values must be finite")

    @classmethod
    def sampled_now(cls, **values: object) -> TelemetryReading:
        return cls(sampled_at_ms=int(time.time() * 1000), **values)

    @property
    def topic(self) -> str:
        return f"enviroplus/{self.device_id}/telemetry"

    def to_json(self) -> str:
        payload = asdict(self)
        payload.pop("device_id")
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)
