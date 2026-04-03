"""
writer.py — Async-safe InfluxDB 3 Core write layer for SonoffLAN-InfluxDB.

Converts EnergyReading objects into InfluxDB Points and writes them
via asyncio.to_thread() to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
import logging

from influxdb_client_3 import InfluxDBClient3, Point
from influxdb_client_3 import InfluxDBError

from extractor import EnergyReading

_LOGGER = logging.getLogger(__name__)


class InfluxWriter:
    """Writes EnergyReading objects to InfluxDB 3 Core.

    Constructor: InfluxWriter(host, token, database)
      - host: Full URL e.g. "http://localhost:8086"
      - token: InfluxDB auth token
      - database: Target database/bucket name
    """

    def __init__(self, host: str, token: str, database: str) -> None:
        self._database = database
        self._client = InfluxDBClient3(
            host=host,
            token=token,
            database=database,
        )

    async def write(self, reading: EnergyReading, device_name: str | None = None) -> None:
        """Write one EnergyReading to InfluxDB.

        - measurement = reading.device_id (per D-01: one measurement per device)
        - tags: device_id, device_name (per D-02)
        - fields: power, voltage, current, energy_today — None values omitted (per D-03)
        - Uses asyncio.to_thread() to avoid blocking the event loop (per D-08, INF-05)
        - On any write failure: logs ERROR, returns None — does not raise (per D-10, INF-06)
        """
        # Build fields dict — omit None values entirely (per D-03)
        fields: dict[str, float] = {}
        if reading.power is not None:
            fields["power"] = reading.power
        if reading.voltage is not None:
            fields["voltage"] = reading.voltage
        if reading.current is not None:
            fields["current"] = reading.current
        if reading.energy_today is not None:
            fields["energy_today"] = reading.energy_today

        # Nothing to write — skip (avoids writing empty points)
        if not fields:
            return

        # Build Point (per D-01, D-02, D-03)
        name = device_name if device_name is not None else reading.device_id
        point = (
            Point(reading.device_id)          # measurement name = device_id (D-01)
            .tag("device_id", reading.device_id)
            .tag("device_name", name)
        )
        for field_name, value in fields.items():
            point = point.field(field_name, value)

        # Write via asyncio.to_thread() — never blocks the event loop (INF-05)
        try:
            await asyncio.to_thread(self._client.write, record=point)
        except Exception as e:
            _LOGGER.error(
                "InfluxDB write failed | device=%s | %s",
                reading.device_id,
                e,
                exc_info=e,
            )

    async def check_connectivity(self) -> None:
        """Perform a non-destructive connectivity check against InfluxDB.

        Calls get_server_version() (hits /ping endpoint) via asyncio.to_thread().
        Raises RuntimeError with a clear message if unreachable (per D-13).
        """
        try:
            await asyncio.to_thread(self._client.get_server_version)
        except Exception as e:
            raise RuntimeError(
                f"InfluxDB unreachable at startup: {e}"
            ) from e

    def close(self) -> None:
        """Close the underlying InfluxDBClient3 and release resources."""
        self._client.close()
