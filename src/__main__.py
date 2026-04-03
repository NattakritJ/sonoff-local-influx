import asyncio
import logging
import signal
import sys

import aiohttp
from zeroconf.asyncio import AsyncZeroconf

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")  # ensure src/ on path if run directly

from config import parse_config
from ewelink import SIGNAL_UPDATE, XRegistryLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
_LOGGER = logging.getLogger("sonoff_daemon")


async def main() -> None:
    devices = parse_config()

    # Build a lookup dict: device_id -> DeviceConfig (for filter + decrypt)
    device_map = {d["device_id"]: d for d in devices}

    _LOGGER.info(
        "SonoffLAN-InfluxDB starting | devices=%d | ids=%s",
        len(devices),
        [d["device_id"] for d in devices],
    )

    shutdown_event = asyncio.Event()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    async with aiohttp.ClientSession() as session:
        registry = XRegistryLocal(session)

        def on_update(msg: dict) -> None:
            """Handle every mDNS update event."""
            deviceid: str = msg.get("deviceid", "")

            # LAN-06: ignore devices not in our configured list
            if deviceid not in device_map:
                return

            cfg = device_map[deviceid]
            name = cfg.get("device_name", deviceid)

            # Determine if payload is encrypted or plain
            if "data" in msg and "iv" in msg:
                # LAN-03 / LAN-05: encrypted payload — decrypt with devicekey
                devicekey = cfg.get("devicekey", "")
                try:
                    params = XRegistryLocal.decrypt_msg(msg, devicekey)
                    _LOGGER.info(
                        "UPDATE (encrypted) | %s (%s) | host=%s | params=%s",
                        deviceid, name, msg.get("host"), params,
                    )
                except Exception as e:
                    _LOGGER.warning(
                        "DECRYPT FAILED | %s (%s) | %s", deviceid, name, e
                    )
            else:
                # LAN-04: plain JSON payload (DIY / older devices)
                params = msg.get("params", {})
                _LOGGER.info(
                    "UPDATE (plain) | %s (%s) | host=%s | params=%s",
                    deviceid, name, msg.get("host"), params,
                )

        registry.dispatcher_connect(SIGNAL_UPDATE, on_update)

        # LAN-01: start mDNS browser
        azc = AsyncZeroconf()
        registry.start(azc.zeroconf)
        _LOGGER.info("mDNS discovery started — listening for _ewelink._tcp.local.")

        # OPS-01: run until signal
        await shutdown_event.wait()

        # OPS-02: graceful shutdown
        _LOGGER.info("Shutdown signal received — stopping...")
        await registry.stop()
        await azc.async_close()
        _LOGGER.info("Daemon stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
