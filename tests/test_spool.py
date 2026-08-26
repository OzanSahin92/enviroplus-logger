from pathlib import Path

from enviroplus_logger.spool import TelemetrySpool


def test_spool_persists_messages_across_restarts(tmp_path: Path) -> None:
    path = tmp_path / "spool.db"
    with TelemetrySpool(path) as spool:
        message_id = spool.enqueue("devices/one", '{"value":1}', now_ms=1_000)

    with TelemetrySpool(path) as reopened:
        messages = reopened.due(now_ms=1_000)
        assert len(messages) == 1
        assert messages[0].id == message_id
        assert messages[0].payload == '{"value":1}'


def test_failed_message_uses_exponential_backoff(tmp_path: Path) -> None:
    with TelemetrySpool(tmp_path / "spool.db") as spool:
        spool.enqueue("devices/one", "{}", now_ms=1_000)
        first = spool.due(now_ms=1_000)[0]
        spool.mark_failed(first, RuntimeError("offline"), now_ms=1_000)

        assert spool.due(now_ms=1_999) == []
        second = spool.due(now_ms=2_000)[0]
        assert second.attempts == 1

        spool.mark_failed(second, RuntimeError("still offline"), now_ms=2_000)
        assert spool.due(now_ms=3_999) == []
        assert spool.due(now_ms=4_000)[0].attempts == 2


def test_sent_message_is_removed(tmp_path: Path) -> None:
    with TelemetrySpool(tmp_path / "spool.db") as spool:
        message_id = spool.enqueue("devices/one", "{}", now_ms=1_000)
        spool.mark_sent(message_id)
        assert spool.count() == 0
