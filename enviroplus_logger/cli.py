from __future__ import annotations

import argparse
import itertools
import time
from pathlib import Path

from enviroplus_logger.agent import TelemetryAgent
from enviroplus_logger.publisher import AwsIotPublisher
from enviroplus_logger.simulator import simulated_reading
from enviroplus_logger.spool import TelemetrySpool


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Enviro+ AWS IoT device agent")
    command.add_argument("--endpoint", required=True)
    command.add_argument("--device-id", required=True)
    command.add_argument("--certificate", type=Path, required=True)
    command.add_argument("--private-key", type=Path, required=True)
    command.add_argument("--root-ca", type=Path, required=True)
    command.add_argument("--spool", type=Path, default=Path("telemetry-spool.db"))
    command.add_argument(
        "--count", type=int, default=0, help="samples to send; 0 runs continuously"
    )
    command.add_argument("--interval", type=float, default=5)
    return command


def main() -> None:
    args = parser().parse_args()
    if args.count < 0:
        parser().error("--count must be zero or positive")
    if args.interval < 0:
        parser().error("--interval must be zero or positive")
    publisher = AwsIotPublisher(
        endpoint=args.endpoint,
        client_id=args.device_id,
        certificate=args.certificate,
        private_key=args.private_key,
        root_ca=args.root_ca,
    )
    with TelemetrySpool(args.spool) as spool:
        agent = TelemetryAgent(spool, publisher)
        sequences = itertools.count() if args.count == 0 else range(args.count)
        for sequence in sequences:
            agent.submit(simulated_reading(args.device_id, sequence))
            if args.count == 0 or sequence + 1 < args.count:
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
