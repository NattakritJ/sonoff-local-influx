import asyncio
import logging
import os
import signal
import sys

import aiohttp
from zeroconf.asyncio import AsyncZeroconf

from config import parse_config, parse_influx_config, parse_log_level
from ewelink import SIGNAL_UPDATE, XRegistryLocal
from extractor import EnergyReading, extract_energy, extract_energy_multi
from writer import InfluxWriter
from config import DeviceConfig

_LOGGER = logging.getLogger("sonoff_daemon")

# UIIDs with multiple channels — use extract_energy_multi() for these
_MULTI_CHANNEL_UIIDS = frozenset({126, 130})


class SonoffDaemon:
    def __init__(self, devices: list[DeviceConfig], writer: InfluxWriter) -> None:
        self._devices = {d["device_id"]: d for d in devices}
        self._writer = writer
        self._write_count = 0
        self._shutdown = asyncio.Event()

    async def run(self) -> None:
        """Set up all components and run until shutdown signal."""
        # Register signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown.set)

        async with aiohttp.ClientSession() as session:
            registry = XRegistryLocal(session)
            registry.dispatcher_connect(SIGNAL_UPDATE, self._on_update)

            azc = AsyncZeroconf()
            registry.start(azc.zeroconf)

            _LOGGER.info(
                "SonoffLAN-InfluxDB ready | devices=%d | influx=%s | ids=%s",
                len(self._devices),
                self._writer._host if hasattr(self._writer, "_host") else "configured",
                list(self._devices.keys()),
            )

            # Start heartbeat background task
            heartbeat_task = asyncio.ensure_future(self._heartbeat())

            # Wait for shutdown signal
            await self._shutdown.wait()

            # Cancel heartbeat
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

            # Clean shutdown
            await registry.stop()
            await azc.async_close()
            self._writer.close()
            _LOGGER.info("Daemon stopped cleanly.")

    def _on_update(self, msg: dict) -> None:
        """Handle every mDNS update event; extract energy and schedule writes."""
        deviceid: str = msg.get("deviceid", "")

        # Ignore devices not in our configured list
        if deviceid not in self._devices:
            return

        cfg = self._devices[deviceid]

        # Determine params: decrypt if encrypted, else use plain params
        if "data" in msg and "iv" in msg:
            devicekey = cfg.get("devicekey", "")
            try:
                params = XRegistryLocal.decrypt_msg(msg, devicekey)
            except Exception as e:
                _LOGGER.warning("DECRYPT FAILED | %s | %s", deviceid, e)
                return
        else:
            params = msg.get("params", {})

        if not params:
            return

        uiid = cfg.get("uiid", 0)

        _LOGGER.debug(
            "UPDATE | %s (%s) | uiid=%d | params=%s",
            deviceid,
            cfg.get("device_name", deviceid),
            uiid,
            params,
        )

        # Extract energy readings — multi-channel or single-channel
        if uiid in _MULTI_CHANNEL_UIIDS:
            readings = extract_energy_multi(deviceid, uiid, params)
        else:
            reading = extract_energy(deviceid, uiid, params)
            readings = [reading] if reading is not None else []

        for r in readings:
            asyncio.ensure_future(self._write_reading(r, cfg))

    async def _write_reading(self, reading: EnergyReading, cfg: DeviceConfig) -> None:
        """Write one energy reading to InfluxDB and log the result."""
        device_name = cfg.get("device_name", reading.device_id)
        await self._writer.write(reading, device_name=device_name)
        # writer.write() never raises — log success after calling write
        self._write_count += 1
        _LOGGER.info(
            "WRITE | %s (%s) | ch=%s | power=%s W | voltage=%s V | current=%s A",
            reading.device_id,
            device_name,
            reading.channel if reading.channel is not None else "-",
            reading.power,
            reading.voltage,
            reading.current,
        )

    async def _heartbeat(self) -> None:
        """Log write counter every 60 seconds."""
        while True:
            await asyncio.sleep(60)
            _LOGGER.info("HEARTBEAT | writes=%d", self._write_count)


def _load_dotenv() -> None:
    """Load .env file from the project root into os.environ (no-op if absent).

    Parses KEY=VALUE lines; ignores comments and blanks; does NOT override
    vars already set in the environment (so Docker env vars always win).
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


async def main() -> None:
    # Load .env file if present (for local dev — Docker passes vars directly)
    _load_dotenv()
    log_level = parse_log_level()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    devices = parse_config()
    host, token, database = parse_influx_config()
    writer = InfluxWriter(host, token, database)
    try:
        await writer.check_connectivity()
        _LOGGER.info(
            "InfluxDB connected | host=%s | database=%s", host, database
        )
    except RuntimeError as e:
        _LOGGER.error("Startup failed: %s", e)
        sys.exit(1)

    daemon = SonoffDaemon(devices, writer)
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
