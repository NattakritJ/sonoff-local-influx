"""
extractor.py — Pure energy parameter extraction for Sonoff LAN devices.

Converts raw Sonoff LAN ``params`` dicts into typed ``EnergyReading`` values
that can be written directly to InfluxDB.  No I/O, no logging, no HA imports.

Supported single-channel UIIDs and their scaling:

  ×1 (pass-through):
    - 32   (POWR2):           power, current, voltage
    - 182  (S40):             power, current, voltage
    - 226  (CK-BL602):        phase_0_p → power, phase_0_c → current, phase_0_v → voltage

  ×0.01:
    - 190  (POWR3 / S60):     power, current, voltage; dayKwh → energy_today
    - 262  (CK-BL602-SWP1):   power, current, voltage
    - 276  (S61STPF):         power, current, voltage; dayKwh → energy_today
    - 277  (XMiniDim):        power, current, voltage
    - 7032 (S60ZBTPF):        power, current, voltage; dayKwh → energy_today

Multi-channel UIIDs (DualR3=126, SPM-4Relay=130) are handled in plan 02-02.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnergyReading:
    """Typed energy snapshot for a single Sonoff device (or channel)."""

    device_id: str
    uiid: int
    power: float | None
    voltage: float | None
    current: float | None
    energy_today: float | None  # derived from dayKwh × 0.01
    channel: int | None  # None for single-channel; 1-based for multi-channel


# UIIDs whose raw values are already in final units (×1 pass-through)
_SCALE_1: frozenset[int] = frozenset({32, 182, 226})

# UIIDs whose raw values must be divided by 100 (×0.01)
_SCALE_001: frozenset[int] = frozenset({190, 262, 276, 277, 7032})

# All supported UIIDs
_SUPPORTED: frozenset[int] = _SCALE_1 | _SCALE_001

# UIIDs that carry dayKwh (daily energy total) in params
_HAS_DAY_KWH: frozenset[int] = frozenset({190, 276, 7032})

# UIID 226 uses differently-named params; map standard names → actual param keys
_226_MAP: dict[str, str] = {
    "power": "phase_0_p",
    "current": "phase_0_c",
    "voltage": "phase_0_v",
}


def _to_float(value: object) -> float | None:
    """Convert *value* to float, returning None for None inputs.

    Accepts ``int``, ``float``, and numeric ``str`` values.
    Raises ``ValueError`` for non-numeric strings — bad data is a bug.
    """
    if value is None:
        return None
    return float(value)


def extract_energy(
    device_id: str,
    uiid: int,
    params: dict,
) -> EnergyReading | None:
    """Extract energy metrics from a raw Sonoff LAN ``params`` dict.

    Returns an ``EnergyReading`` when at least one energy field is present,
    or ``None`` when ``params`` contains no recognisable energy data.

    Args:
        device_id:  Device identifier (used as a tag in InfluxDB).
        uiid:       Sonoff device UIID (determines param names and scaling).
        params:     Raw params dict from the LAN event.

    Returns:
        ``EnergyReading`` or ``None``.
    """
    if uiid not in _SUPPORTED:
        return None

    scale: float = 1.0 if uiid in _SCALE_1 else 0.01

    # Resolve raw param values (UIID 226 uses different key names)
    if uiid == 226:
        raw_power = params.get(_226_MAP["power"])
        raw_current = params.get(_226_MAP["current"])
        raw_voltage = params.get(_226_MAP["voltage"])
    else:
        raw_power = params.get("power")
        raw_current = params.get("current")
        raw_voltage = params.get("voltage")

    # Return None if no energy fields are present at all
    if raw_power is None and raw_current is None and raw_voltage is None:
        return None

    # Apply scale factor
    power = (_to_float(raw_power) * scale) if raw_power is not None else None
    current = (_to_float(raw_current) * scale) if raw_current is not None else None
    voltage = (_to_float(raw_voltage) * scale) if raw_voltage is not None else None

    # Extract daily energy total where supported
    energy_today: float | None = None
    if uiid in _HAS_DAY_KWH:
        raw_day_kwh = params.get("dayKwh")
        if raw_day_kwh is not None:
            energy_today = round(_to_float(raw_day_kwh) * 0.01, 4)

    return EnergyReading(
        device_id=device_id,
        uiid=uiid,
        power=power,
        voltage=voltage,
        current=current,
        energy_today=energy_today,
        channel=None,
    )
