import json
import logging
import os
import sys
from typing import TypedDict

_LOGGER = logging.getLogger(__name__)


class DeviceConfig(TypedDict, total=False):
    device_id: str          # required
    uiid: int               # required — Sonoff device UIID (e.g. 190 for POWR3); not broadcast via mDNS
    devicekey: str          # required for encrypted devices; omit for DIY
    device_name: str        # optional display name
    ip: str                 # optional static IP — skip mDNS discovery when set


def parse_config() -> list[DeviceConfig]:
    """Read and validate SONOFF_DEVICES env var.

    Returns a list of DeviceConfig dicts.
    Calls sys.exit(1) with a clear message if the env var is missing or malformed.
    """
    raw = os.environ.get("SONOFF_DEVICES")
    if not raw:
        print(
            "ERROR: SONOFF_DEVICES environment variable is required.\n"
            'Expected JSON array, e.g.: \'[{"device_id":"1000xxxxxx","uiid":190,"devicekey":"abc..."}]\'',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        devices = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: SONOFF_DEVICES is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(devices, list) or len(devices) == 0:
        print(
            "ERROR: SONOFF_DEVICES must be a non-empty JSON array of device objects.",
            file=sys.stderr,
        )
        sys.exit(1)

    validated: list[DeviceConfig] = []
    for i, dev in enumerate(devices):
        if not isinstance(dev, dict) or "device_id" not in dev:
            print(
                f"ERROR: SONOFF_DEVICES[{i}] must be an object with a 'device_id' field.",
                file=sys.stderr,
            )
            sys.exit(1)
        if "uiid" not in dev:
            print(
                f"ERROR: SONOFF_DEVICES[{i}] (device_id={dev.get('device_id', '?')!r}) "
                f"is missing the required 'uiid' field.\n"
                f"  The UIID is the Sonoff device type ID (e.g. 190 for POWR3, 32 for S31).\n"
                f"  Find it in the eWeLink app or from your device's cloud data.",
                file=sys.stderr,
            )
            sys.exit(1)
        validated.append(
            DeviceConfig(
                device_id=dev["device_id"],
                uiid=int(dev["uiid"]),
                devicekey=dev.get("devicekey", ""),
                device_name=dev.get("device_name", dev["device_id"]),
            )
        )
        if "ip" in dev:
            validated[-1]["ip"] = dev["ip"]

    return validated


def parse_influx_config() -> tuple[str, str, str]:
    """Read and validate InfluxDB connection env vars.

    Returns (host, token, database) tuple.
    Calls sys.exit(1) with a clear message if any required var is missing.
    """
    missing = False

    host = os.environ.get("INFLUX_HOST")
    if not host:
        print("ERROR: INFLUX_HOST environment variable is required.", file=sys.stderr)
        missing = True

    token = os.environ.get("INFLUX_TOKEN")
    if not token:
        print("ERROR: INFLUX_TOKEN environment variable is required.", file=sys.stderr)
        missing = True

    database = os.environ.get("INFLUX_DATABASE")
    if not database:
        print(
            "ERROR: INFLUX_DATABASE environment variable is required.", file=sys.stderr
        )
        missing = True

    if missing:
        sys.exit(1)

    return host, token, database  # type: ignore[return-value]  # guarded by missing check


_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def parse_log_level() -> int:
    """Read LOG_LEVEL env var and return the corresponding logging int.

    Valid values (case-insensitive): DEBUG, INFO, WARNING, ERROR, CRITICAL.
    Defaults to INFO if not set. Calls sys.exit(1) on invalid values.
    """
    raw = os.environ.get("LOG_LEVEL", "INFO").upper()
    if raw not in _VALID_LOG_LEVELS:
        print(
            f"ERROR: LOG_LEVEL={raw!r} is not valid.\n"
            f"  Allowed values: {', '.join(sorted(_VALID_LOG_LEVELS))}",
            file=sys.stderr,
        )
        sys.exit(1)
    return getattr(logging, raw)


def parse_poll_interval() -> int:
    """Read SONOFF_POLL_INTERVAL env var and return polling interval in seconds.

    Defaults to 10 if not set. Calls sys.exit(1) on non-integer or non-positive values.
    """
    raw = os.environ.get("SONOFF_POLL_INTERVAL")
    if raw is None:
        return 10
    try:
        value = int(raw)
    except ValueError:
        print(
            f"ERROR: SONOFF_POLL_INTERVAL={raw!r} is not a valid integer.\n"
            f"  Expected a positive integer number of seconds (e.g. 10, 30, 60).",
            file=sys.stderr,
        )
        sys.exit(1)
    if value <= 0:
        print(
            f"ERROR: SONOFF_POLL_INTERVAL={value} must be a positive integer (> 0).",
            file=sys.stderr,
        )
        sys.exit(1)
    return value
