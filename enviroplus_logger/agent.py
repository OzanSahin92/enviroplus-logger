from __future__ import annotations

from enviroplus_logger.publisher import Publisher, PublisherError
from enviroplus_logger.spool import TelemetrySpool
from enviroplus_logger.telemetry import TelemetryReading


class TelemetryAgent:
    def __init__(self, spool: TelemetrySpool, publisher: Publisher) -> None:
        self._spool = spool
        self._publisher = publisher

    def submit(self, reading: TelemetryReading, now_ms: int | None = None) -> int:
        """Persist before publishing so a crash cannot silently lose a reading."""
        message_id = self._spool.enqueue(reading.topic, reading.to_json(), now_ms)
        self.flush(now_ms)
        return message_id

    def flush(self, now_ms: int | None = None, limit: int = 100) -> int:
        delivered = 0
        messages = self._spool.due(now_ms, limit)
        if not messages:
            return delivered

        try:
            self._publisher.connect()
            for message in messages:
                try:
                    self._publisher.publish(message.topic, message.payload)
                except PublisherError as error:
                    self._spool.mark_failed(message, error, now_ms)
                    break
                self._spool.mark_sent(message.id)
                delivered += 1
        except PublisherError as error:
            self._spool.mark_failed(messages[0], error, now_ms)
        finally:
            try:
                self._publisher.disconnect()
            except PublisherError:
                # Delivery state is already represented by the durable spool.
                return delivered
        return delivered
