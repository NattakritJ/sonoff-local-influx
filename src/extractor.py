"""
extractor.py — Pure energy parameter extraction for Sonoff LAN devices.

Converts raw Sonoff LAN ``params`` dicts into typed ``EnergyReading`` values
that can be written directly to InfluxDB.  No I/O, no logging, no HA imports.

Supported single-channel UIIDs and their scaling:

  ×1 (pass-through):
    - 182  (S40):             power, current, voltage
    - 226  (CK-BL602):        phase_0_p → power, phase_0_c → current, phase_0_v → voltage

  ×1 or ×0.01 (auto-detected per-message for UIID 32):
    - 32   (POWR2 / POWR3):   power, current, voltage
      POWR2 / S31 firmware (3.x) sends pre-scaled floats — `"234.53"` V → ×1.
      POWR3 hardware on the same UIID (firmware 1.2.1) sends raw centi-units —
      `23455` → ÷100 = 234.55 V.  Detected by checking whether the raw voltage
      (or any available metric) exceeds 1000 after float conversion: residential
      voltage is always 100–280 V (pre-scaled) or 10000–28000 (raw cents), so
      the threshold is unambiguous.

  ×0.01:
    - 190  (POWR3 / S60):     power, current, voltage; dayKwh → energy_today
    - 262  (CK-BL602-SWP1):   power, current, voltage
    - 276  (S61STPF):         power, current, voltage; dayKwh → energy_today
    - 277  (XMiniDim):        power, current, voltage
    - 7032 (S60ZBTPF):        power, current, voltage; dayKwh → energy_today

Multi-channel UIIDs (actPow_00..03 params, ×0.01 scaling):
  - 126  (DualR3):         2 channels — actPow_00/01, current_00/01, voltage_00/01
  - 130  (SPM-4Relay):     4 channels — actPow_00..03, current_00..03, voltage_00..03
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
    energy_backfeed_today: float | None = None  # daily export kWh (UIID 190 only; dayPowerSupply × 0.01)


# UIIDs whose raw values are already in final units (×1 pass-through)
_SCALE_1: frozenset[int] = frozenset({182, 226})

# UIIDs whose raw values must be divided by 100 (×0.01)
_SCALE_001: frozenset[int] = frozenset({190, 262, 276, 277, 7032})

# UIID 32 (POWR2 / POWR3) is handled separately: the scale factor is
# auto-detected per-message because two firmware families share UIID 32:
#   • POWR2 / S31 (fw 3.x):  pre-scaled floats, e.g. "234.53" V  → ×1
#   • POWR3 (fw 1.2.1):      raw centi-units,   e.g. 23455      → ÷100
# Residential voltage is always 100–280 V when pre-scaled, or 10000–28000
# when in centi-volts, so any raw value > 1000 unambiguously needs ÷100.
_UIID_32_CENTI_THRESHOLD: float = 1000.0

# All supported single-channel UIIDs
_SUPPORTED: frozenset[int] = _SCALE_1 | _SCALE_001 | frozenset({32})

# UIIDs that carry dayKwh (daily energy total) in params
_HAS_DAY_KWH: frozenset[int] = frozenset({190, 276, 7032})

# UIID 226 uses differently-named params; map standard names → actual param keys
_226_MAP: dict[str, str] = {
    "power": "phase_0_p",
    "current": "phase_0_c",
    "voltage": "phase_0_v",
}

# Multi-channel UIID → number of channels
_MULTI_CHANNEL_UIIDS: dict[int, int] = {
    126: 2,  # DualR3: 2 channels
    130: 4,  # SPM-4Relay: 4 channels
}

# Positional suffixes for multi-channel params (channel index → suffix)
_MULTI_PARAM_SUFFIXES: list[str] = ["_00", "_01", "_02", "_03"]


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

    # UIID 32: auto-detect scale from the first available raw value.
    # Pre-scaled firmware (POWR2/S31) sends values like "234.53" (≤ 1000 after
    # float conversion).  POWR3 firmware 1.2.1 sends raw centi-units like 23455
    # (> 1000).  Check voltage first (most reliable sentinel); fall back to
    # power, then current.
    if uiid == 32:
        _sentinel = (
            params.get("voltage")
            if params.get("voltage") is not None
            else (
                params.get("power")
                if params.get("power") is not None
                else params.get("current")
            )
        )
        if _sentinel is not None and float(_sentinel) > _UIID_32_CENTI_THRESHOLD:
            scale: float = 0.01
        else:
            scale = 1.0
    else:
        scale = 1.0 if uiid in _SCALE_1 else 0.01

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

    # -----------------------------------------------------------------------
    # UIID 190 (POWCT): sign-encoded backfeed extraction
    # supplyPower > 0 means grid export → use negative sign in power/current.
    # consumption (power > 0, supplyPower == 0) stays positive as before.
    # Both-zero: write 0.0 explicitly (per D-13) — never return None for 190.
    # -----------------------------------------------------------------------
    if uiid == 190:
        raw_supply_power = params.get("supplyPower")
        raw_supply_current = params.get("supplyCurrent")
        raw_day_supply = params.get("dayPowerSupply")

        supply_power_val = _to_float(raw_supply_power) if raw_supply_power is not None else 0.0
        supply_current_val = _to_float(raw_supply_current) if raw_supply_current is not None else 0.0

        # Resolve power/current using three-way logic (per D-07):
        consumption_power = _to_float(raw_power) if raw_power is not None else 0.0
        consumption_current = _to_float(raw_current) if raw_current is not None else 0.0

        if consumption_power > 0 and supply_power_val == 0:
            # Normal consumption: use positive values
            power = round(consumption_power * 0.01, 2)
            current = round(consumption_current * 0.01, 2)
        elif supply_power_val > 0 and consumption_power == 0:
            # Grid export: negate supply values (per D-04)
            power = round(-supply_power_val * 0.01, 2)
            current = round(-supply_current_val * 0.01, 2)
        elif consumption_power > 0 and supply_power_val > 0:
            # Defensive: both non-zero (shouldn't happen per D-09) — use consumption
            power = round(consumption_power * 0.01, 2)
            current = round(consumption_current * 0.01, 2)
        else:
            # Both zero: write 0.0 explicitly (per D-13)
            power = 0.0
            current = 0.0

        voltage = round(_to_float(raw_voltage) * 0.01, 2) if raw_voltage is not None else None

        energy_backfeed_today: float | None = None
        if raw_day_supply is not None:
            energy_backfeed_today = round(_to_float(raw_day_supply) * 0.01, 4)

        energy_today_190: float | None = None
        raw_day_kwh = params.get("dayKwh")
        if raw_day_kwh is not None:
            energy_today_190 = round(_to_float(raw_day_kwh) * 0.01, 4)

        return EnergyReading(
            device_id=device_id,
            uiid=uiid,
            power=power,
            voltage=voltage,
            current=current,
            energy_today=energy_today_190,
            channel=None,
            energy_backfeed_today=energy_backfeed_today,
        )

    # Apply scale factor and round to 2 dp to eliminate IEEE 754 artifacts
    power = round(_to_float(raw_power) * scale, 2) if raw_power is not None else None
    current = round(_to_float(raw_current) * scale, 2) if raw_current is not None else None
    voltage = round(_to_float(raw_voltage) * scale, 2) if raw_voltage is not None else None

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
        energy_backfeed_today=None,
    )


def extract_energy_multi(
    device_id: str,
    uiid: int,
    params: dict,
) -> list[EnergyReading]:
    """Extract energy metrics for multi-channel Sonoff devices (DualR3 / SPM-4Relay).

    Each channel uses ``actPow_0N``, ``current_0N``, ``voltage_0N`` params (×0.01 scale).
    Only channels for which at least one param is present are included in the result.
    Channels with no params at all are silently skipped.

    No ``energy_today`` is available for these UIIDs via LAN (cloud-only energy history).

    Supported UIIDs:
        - 126 (DualR3):      2 channels
        - 130 (SPM-4Relay):  4 channels

    Args:
        device_id:  Device identifier (used as a tag in InfluxDB).
        uiid:       Sonoff device UIID.  Returns ``[]`` for unsupported UIIDs.
        params:     Raw params dict from the LAN event.

    Returns:
        List of ``EnergyReading`` objects, one per present channel (may be empty).
    """
    if uiid not in _MULTI_CHANNEL_UIIDS:
        return []

    num_channels = _MULTI_CHANNEL_UIIDS[uiid]
    readings: list[EnergyReading] = []

    for ch_idx in range(num_channels):
        suffix = _MULTI_PARAM_SUFFIXES[ch_idx]
        raw_power = params.get(f"actPow{suffix}")
        raw_current = params.get(f"current{suffix}")
        raw_voltage = params.get(f"voltage{suffix}")

        # Skip channels with no params present
        if raw_power is None and raw_current is None and raw_voltage is None:
            continue

        power = round(_to_float(raw_power) * 0.01, 2) if raw_power is not None else None
        current = round(_to_float(raw_current) * 0.01, 2) if raw_current is not None else None
        voltage = round(_to_float(raw_voltage) * 0.01, 2) if raw_voltage is not None else None

        readings.append(
            EnergyReading(
                device_id=device_id,
                uiid=uiid,
                power=power,
                voltage=voltage,
                current=current,
                energy_today=None,  # No dayKwh for DualR3/SPM via LAN
                channel=ch_idx + 1,  # 1-based channel number
                energy_backfeed_today=None,
            )
        )

    return readings
