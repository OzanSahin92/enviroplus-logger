from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Publisher(Protocol):
    def connect(self) -> None: ...

    def publish(self, topic: str, payload: str) -> None: ...

    def disconnect(self) -> None: ...


class PublisherError(RuntimeError):
    """A recoverable connection or delivery failure."""


class AwsIotPublisher:
    """QoS 1 MQTT publisher authenticated by an on-device X.509 identity."""

    def __init__(
        self,
        *,
        endpoint: str,
        client_id: str,
        certificate: str | Path,
        private_key: str | Path,
        root_ca: str | Path,
    ) -> None:
        from awsiot import mqtt_connection_builder

        self._connection = mqtt_connection_builder.mtls_from_path(
            endpoint=endpoint,
            client_id=client_id,
            cert_filepath=str(certificate),
            pri_key_filepath=str(private_key),
            ca_filepath=str(root_ca),
            clean_session=False,
            keep_alive_secs=30,
        )

    def connect(self) -> None:
        try:
            self._connection.connect().result()
        except Exception as error:  # AWS CRT exposes several runtime exception types
            raise PublisherError("could not connect to AWS IoT Core") from error

    def publish(self, topic: str, payload: str) -> None:
        from awscrt import mqtt

        try:
            future, _ = self._connection.publish(
                topic=topic,
                payload=payload,
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )
            future.result()
        except Exception as error:  # AWS CRT exposes several runtime exception types
            raise PublisherError("MQTT publish was not acknowledged") from error

    def disconnect(self) -> None:
        try:
            self._connection.disconnect().result()
        except Exception as error:  # AWS CRT exposes several runtime exception types
            raise PublisherError("could not disconnect cleanly") from error
