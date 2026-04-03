import json
import logging
import os
import sys
from typing import TypedDict

_LOGGER = logging.getLogger(__name__)


class DeviceConfig(TypedDict, total=False):
    device_id: str          # required
    devicekey: str          # required for encrypted devices; omit for DIY
    device_name: str        # optional display name


def parse_config() -> list[DeviceConfig]:
    """Read and validate SONOFF_DEVICES env var.

    Returns a list of DeviceConfig dicts.
    Calls sys.exit(1) with a clear message if the env var is missing or malformed.
    """
    raw = os.environ.get("SONOFF_DEVICES")
    if not raw:
        print(
            "ERROR: SONOFF_DEVICES environment variable is required.\n"
            'Expected JSON array, e.g.: \'[{"device_id":"1000xxxxxx","devicekey":"abc..."}]\'',
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
        validated.append(
            DeviceConfig(
                device_id=dev["device_id"],
                devicekey=dev.get("devicekey", ""),
                device_name=dev.get("device_name", dev["device_id"]),
            )
        )

    return validated
