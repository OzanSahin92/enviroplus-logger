from pathlib import Path

from enviroplus_logger.agent import TelemetryAgent
from enviroplus_logger.publisher import PublisherError
from enviroplus_logger.spool import TelemetrySpool
from enviroplus_logger.telemetry import TelemetryReading


class FakePublisher:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.connected = False
        self.disconnected = False
        self.messages: list[tuple[str, str]] = []

    def connect(self) -> None:
        self.connected = True

    def publish(self, topic: str, payload: str) -> None:
        if self.failure:
            raise self.failure
        self.messages.append((topic, payload))

    def disconnect(self) -> None:
        self.disconnected = True


def reading() -> TelemetryReading:
    return TelemetryReading(
        device_id="lab-one",
        temperature_c=20,
        pressure_hpa=1013,
        humidity_pct=50,
        illuminance_lux=100,
        proximity=0,
        oxidising_ohm=100,
        reducing_ohm=200,
        nh3_ohm=300,
        sampled_at_ms=1_700_000_000_000,
    )


def test_agent_removes_message_only_after_success(tmp_path: Path) -> None:
    publisher = FakePublisher()
    with TelemetrySpool(tmp_path / "spool.db") as spool:
        agent = TelemetryAgent(spool, publisher)
        agent.submit(reading(), now_ms=1_000)

        assert spool.count() == 0
        assert publisher.messages[0][0] == "enviroplus/lab-one/telemetry"
        assert publisher.connected and publisher.disconnected


def test_agent_retains_message_after_publish_failure(tmp_path: Path) -> None:
    publisher = FakePublisher(PublisherError("network unavailable"))
    with TelemetrySpool(tmp_path / "spool.db") as spool:
        agent = TelemetryAgent(spool, publisher)
        agent.submit(reading(), now_ms=1_000)

        assert spool.count() == 1
        assert spool.due(now_ms=1_999) == []
        assert spool.due(now_ms=2_000)[0].attempts == 1
