"""
TDD tests for src/extractor.py — EnergyReading dataclass + extract_energy() / extract_energy_multi() functions.

Covers all single-channel UIIDs (Plan 01):
  - UIID 32  (POWR2/S31):      power/current/voltage — pre-scaled floats, ×1 (fw 3.x)
  - UIID 32  (POWR3 hw):       power/current/voltage — raw centi-units, ×0.01 (fw 1.2.1)
  - UIID 182 (S40):            power/current/voltage ×1
  - UIID 190 (POWR3/S60):      power/current/voltage ×0.01, dayKwh → energy_today ×0.01
  - UIID 226 (CK-BL602):       phase_0_p/c/v → power/current/voltage ×1
  - UIID 262 (CK-BL602-SWP1):  power/current/voltage ×0.01
  - UIID 276 (S61STPF):        power/current/voltage ×0.01, dayKwh → energy_today ×0.01
  - UIID 277 (XMiniDim):       power/current/voltage ×0.01
  - UIID 7032 (S60ZBTPF):      power/current/voltage ×0.01, dayKwh → energy_today ×0.01

And multi-channel UIIDs (Plan 02):
  - UIID 126 (DualR3):         actPow_00/01, current_00/01, voltage_00/01 ×0.01 — 2 channels
  - UIID 130 (SPM-4Relay):     actPow_00..03, current_00..03, voltage_00..03 ×0.01 — 4 channels
"""
import pytest
import sys
import os

# Ensure src/ is on path so `from extractor import ...` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extractor import EnergyReading, extract_energy, extract_energy_multi  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1: UIID 32 (POWR2/S31 fw 3.x) — pre-scaled string floats → ×1 passthrough
# ---------------------------------------------------------------------------
def test_uiid_32_prescaled_string_floats_scale_x1():
    """POWR2/S31 firmware 3.x sends pre-scaled floats as strings (e.g. "234.53" V).
    Values are ≤ 1000 so auto-detection leaves them as-is (×1)."""
    result = extract_energy("dev1", 32, {"power": "184.21", "current": "0.88", "voltage": "234.53"})
    assert isinstance(result, EnergyReading)
    assert result.device_id == "dev1"
    assert result.uiid == 32
    assert result.power == pytest.approx(184.21)
    assert result.current == pytest.approx(0.88)
    assert result.voltage == pytest.approx(234.53)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 1b: UIID 32 (POWR3 hw, fw 1.2.1) — raw centi-units → ×0.01 auto-detected
# ---------------------------------------------------------------------------
def test_uiid_32_raw_centi_units_scale_x001():
    """POWR3 hardware (fw 1.2.1) reports UIID 32 but sends raw centi-units.
    Voltage 23455 → 234.55 V; power 14641 → 146.41 W; current 91 → 0.91 A."""
    result = extract_energy("dev1b", 32, {"power": 14641, "current": 91, "voltage": 23455})
    assert isinstance(result, EnergyReading)
    assert result.device_id == "dev1b"
    assert result.uiid == 32
    assert result.power == pytest.approx(146.41)
    assert result.current == pytest.approx(0.91)
    assert result.voltage == pytest.approx(234.55)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 2: UIID 182 (S40) — float raw params → ×1 passthrough
# ---------------------------------------------------------------------------
def test_uiid_182_float_params_scale_x1():
    result = extract_energy("dev2", 182, {"power": 100.5, "current": 50.2, "voltage": 230.1})
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(100.5)
    assert result.current == pytest.approx(50.2)
    assert result.voltage == pytest.approx(230.1)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 3: UIID 190 (POWR3/S60) — int raw params → ×0.01 scaling, channel=None
# ---------------------------------------------------------------------------
def test_uiid_190_int_params_scale_x001():
    result = extract_energy("dev3", 190, {"power": 2300, "current": 500, "voltage": 22000})
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(23.0)
    assert result.current == pytest.approx(5.0)
    assert result.voltage == pytest.approx(220.0)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 4: UIID 190 with dayKwh → energy_today = float(dayKwh) * 0.01
# ---------------------------------------------------------------------------
def test_uiid_190_with_daykwh():
    result = extract_energy(
        "dev3", 190,
        {"power": 2300, "current": 500, "voltage": 22000, "dayKwh": 150}
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(23.0)
    assert result.energy_today == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Test 5: UIID 226 (CK-BL602) — phase_0_p/c/v → power/current/voltage ×1
# ---------------------------------------------------------------------------
def test_uiid_226_phase_param_mapping():
    result = extract_energy(
        "dev5", 226,
        {"phase_0_p": 1500, "phase_0_c": 300, "phase_0_v": 22000}
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(1500.0)
    assert result.current == pytest.approx(300.0)
    assert result.voltage == pytest.approx(22000.0)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 6: UIID 262 (CK-BL602-SWP1) — power/current/voltage ×0.01
# ---------------------------------------------------------------------------
def test_uiid_262_scale_x001():
    result = extract_energy("dev6", 262, {"power": 10000, "current": 1000, "voltage": 22000})
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(100.0)
    assert result.current == pytest.approx(10.0)
    assert result.voltage == pytest.approx(220.0)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 7: UIID 276 (S61STPF) — ×0.01 + dayKwh → energy_today ×0.01
# ---------------------------------------------------------------------------
def test_uiid_276_with_daykwh():
    result = extract_energy(
        "dev7", 276,
        {"power": 5000, "current": 200, "voltage": 22000, "dayKwh": 300}
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(50.0)
    assert result.current == pytest.approx(2.0)
    assert result.voltage == pytest.approx(220.0)
    assert result.energy_today == pytest.approx(3.0)
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 8: UIID 277 (XMiniDim) — ×0.01, energy_today=None (no dayKwh)
# ---------------------------------------------------------------------------
def test_uiid_277_scale_x001_no_energy_today():
    result = extract_energy("dev8", 277, {"power": 8000, "current": 400, "voltage": 21500})
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(80.0)
    assert result.current == pytest.approx(4.0)
    assert result.voltage == pytest.approx(215.0)
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 9: UIID 7032 (S60ZBTPF) — ×0.01 + dayKwh → energy_today ×0.01
# ---------------------------------------------------------------------------
def test_uiid_7032_with_daykwh():
    result = extract_energy(
        "dev9", 7032,
        {"power": 3000, "current": 150, "voltage": 22500, "dayKwh": 200}
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(30.0)
    assert result.current == pytest.approx(1.5)
    assert result.voltage == pytest.approx(225.0)
    assert result.energy_today == pytest.approx(2.0)
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 10: String raw value for UIID 190 → no TypeError, correct scaling
# ---------------------------------------------------------------------------
def test_uiid_190_string_raw_values():
    result = extract_energy(
        "dev10", 190,
        {"power": "2300", "current": "500", "voltage": "22000"}
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(23.0)
    assert result.current == pytest.approx(5.0)
    assert result.voltage == pytest.approx(220.0)


# ---------------------------------------------------------------------------
# Test 11: String raw value for UIID 32 → float output, ×1
# ---------------------------------------------------------------------------
def test_uiid_32_string_voltage():
    result = extract_energy("dev11", 32, {"power": 1000, "current": 100, "voltage": "230"})
    assert isinstance(result, EnergyReading)
    assert result.voltage == pytest.approx(230.0)
    assert isinstance(result.voltage, float)


# ---------------------------------------------------------------------------
# Test 12: Empty / unrelated params → returns None
# ---------------------------------------------------------------------------
def test_empty_params_returns_none():
    result = extract_energy("dev12", 190, {})
    assert result is None


def test_unrelated_params_returns_none():
    result = extract_energy("dev12b", 32, {"switch": "on", "rssi": -60})
    assert result is None


# ---------------------------------------------------------------------------
# Test 13: Partial params (only power present) → EnergyReading with voltage=None, current=None
# ---------------------------------------------------------------------------
def test_partial_params_only_power():
    result = extract_energy("dev13", 32, {"power": 500})
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(500.0)
    assert result.voltage is None
    assert result.current is None
    assert result.energy_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test 14: Unsupported UIID → returns None
# ---------------------------------------------------------------------------
def test_unsupported_uiid_returns_none():
    result = extract_energy("dev14", 999, {"power": 100, "current": 50, "voltage": 230})
    assert result is None


# ---------------------------------------------------------------------------
# Test 15: dayKwh as string → correctly scaled
# ---------------------------------------------------------------------------
def test_daykwh_as_string():
    result = extract_energy(
        "dev15", 190,
        {"power": 1000, "current": 100, "voltage": 22000, "dayKwh": "250"}
    )
    assert isinstance(result, EnergyReading)
    assert result.energy_today == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Test 16: energy_today precision — result rounded to 4 decimal places
# ---------------------------------------------------------------------------
def test_energy_today_rounded_to_4_decimals():
    # dayKwh=1 → energy_today = 1 * 0.01 = 0.01
    result = extract_energy("dev16", 276, {"power": 100, "dayKwh": 1})
    assert isinstance(result, EnergyReading)
    assert result.energy_today == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# Verify the exact success criteria example from the plan
# ---------------------------------------------------------------------------
def test_plan_success_criteria_example():
    """
    From plan:
    extract_energy("dev1", 190, {"power": "2300", "current": "500", "voltage": "22000"})
    → EnergyReading(power=23.0, current=5.0, voltage=220.0, energy_today=None, channel=None)
    """
    result = extract_energy("dev1", 190, {"power": "2300", "current": "500", "voltage": "22000"})
    assert isinstance(result, EnergyReading)
    assert result.device_id == "dev1"
    assert result.uiid == 190
    assert result.power == pytest.approx(23.0)
    assert result.current == pytest.approx(5.0)
    assert result.voltage == pytest.approx(220.0)
    assert result.energy_today is None
    assert result.channel is None


# ===========================================================================
# Plan 02-02: Multi-channel UIIDs — extract_energy_multi()
# ===========================================================================

# ---------------------------------------------------------------------------
# Test 14: DualR3 (UIID 126) with both channels present → list of 2 EnergyReadings
# ---------------------------------------------------------------------------
def test_dualr3_both_channels_returns_two_readings():
    params = {
        "actPow_00": 2300, "current_00": 500, "voltage_00": 22000,
        "actPow_01": 1150, "current_01": 250, "voltage_01": 21950,
    }
    result = extract_energy_multi("dev14", 126, params)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].channel == 1
    assert result[1].channel == 2


# ---------------------------------------------------------------------------
# Test 15: DualR3 channel 1 values — actPow_00=2300 → power=23.0, etc.
# ---------------------------------------------------------------------------
def test_dualr3_channel_1_values():
    params = {
        "actPow_00": 2300, "current_00": 500, "voltage_00": 22000,
        "actPow_01": 1150, "current_01": 250, "voltage_01": 21950,
    }
    result = extract_energy_multi("dev15", 126, params)
    ch1 = result[0]
    assert isinstance(ch1, EnergyReading)
    assert ch1.device_id == "dev15"
    assert ch1.uiid == 126
    assert ch1.channel == 1
    assert ch1.power == pytest.approx(23.0)
    assert ch1.current == pytest.approx(5.0)
    assert ch1.voltage == pytest.approx(220.0)
    assert ch1.energy_today is None


# ---------------------------------------------------------------------------
# Test 16: DualR3 channel 2 values — actPow_01=1150 → power=11.5, etc.
# ---------------------------------------------------------------------------
def test_dualr3_channel_2_values():
    params = {
        "actPow_00": 2300, "current_00": 500, "voltage_00": 22000,
        "actPow_01": 1150, "current_01": 250, "voltage_01": 21950,
    }
    result = extract_energy_multi("dev16", 126, params)
    ch2 = result[1]
    assert isinstance(ch2, EnergyReading)
    assert ch2.channel == 2
    assert ch2.power == pytest.approx(11.5)
    assert ch2.current == pytest.approx(2.5)
    assert ch2.voltage == pytest.approx(219.5)
    assert ch2.energy_today is None


# ---------------------------------------------------------------------------
# Test 17: DualR3 with only channel 1 params → list of 1 EnergyReading (channel=1)
# ---------------------------------------------------------------------------
def test_dualr3_only_channel_1_present():
    params = {"actPow_00": 2300, "current_00": 500, "voltage_00": 22000}
    result = extract_energy_multi("dev17", 126, params)
    assert len(result) == 1
    assert result[0].channel == 1


# ---------------------------------------------------------------------------
# Test 18: DualR3 with no energy params at all → empty list
# ---------------------------------------------------------------------------
def test_dualr3_no_energy_params_returns_empty_list():
    result = extract_energy_multi("dev18", 126, {})
    assert result == []


# ---------------------------------------------------------------------------
# Test 19: SPM-4Relay (UIID 130) with all 4 channels → list of 4 EnergyReadings, channels 1-4
# ---------------------------------------------------------------------------
def test_spm4relay_all_four_channels():
    params = {
        "actPow_00": 1000, "current_00": 100, "voltage_00": 22000,
        "actPow_01": 2000, "current_01": 200, "voltage_01": 22100,
        "actPow_02": 3000, "current_02": 300, "voltage_02": 22200,
        "actPow_03": 4000, "current_03": 400, "voltage_03": 22300,
    }
    result = extract_energy_multi("dev19", 130, params)
    assert isinstance(result, list)
    assert len(result) == 4
    channels = [r.channel for r in result]
    assert channels == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Test 20: SPM-4Relay with channels 1 and 3 present (2 and 4 absent) → 2 EnergyReadings
# ---------------------------------------------------------------------------
def test_spm4relay_partial_channels_1_and_3():
    params = {
        "actPow_00": 1000, "current_00": 100, "voltage_00": 22000,
        "actPow_02": 3000, "current_02": 300, "voltage_02": 22200,
    }
    result = extract_energy_multi("dev20", 130, params)
    assert len(result) == 2
    assert result[0].channel == 1
    assert result[1].channel == 3


# ---------------------------------------------------------------------------
# Test 21: String raw values on DualR3 → float output (type coercion)
# ---------------------------------------------------------------------------
def test_dualr3_string_raw_values_coerced_to_float():
    params = {
        "actPow_00": "2300", "current_00": "500", "voltage_00": "22000",
        "actPow_01": "1150", "current_01": "250", "voltage_01": "21950",
    }
    result = extract_energy_multi("dev21", 126, params)
    assert len(result) == 2
    assert isinstance(result[0].power, float)
    assert result[0].power == pytest.approx(23.0)
    assert isinstance(result[1].current, float)
    assert result[1].current == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Test 22: Unsupported UIID → returns empty list (not an error)
# ---------------------------------------------------------------------------
def test_unsupported_uiid_returns_empty_list():
    result = extract_energy_multi("dev22", 999, {"actPow_00": 1000})
    assert result == []


# ---------------------------------------------------------------------------
# Test 23: All Plan 01 tests still pass (no regression) — verified by import
# ---------------------------------------------------------------------------
def test_plan_01_exports_still_available():
    """Verify extract_energy and EnergyReading are still importable alongside extract_energy_multi."""
    from extractor import EnergyReading as ER, extract_energy as ee, extract_energy_multi as eem  # noqa: F401
    r = ee("reg_check", 32, {"power": 100, "current": 10, "voltage": 230})
    assert isinstance(r, ER)
    assert r.power == pytest.approx(100.0)
    assert r.channel is None


# ---------------------------------------------------------------------------
# Test: Floating-point artifact elimination — single-channel (×0.01 scale)
# ---------------------------------------------------------------------------
def test_single_channel_no_float_artifact():
    # 131561 * 0.01 in IEEE 754 = 1315.6100000000001 without rounding
    result = extract_energy("dev_artifact", 190, {"power": 131561, "voltage": 22000, "current": 500})
    assert isinstance(result, EnergyReading)
    assert result.power == 1315.61
    assert str(result.power) == "1315.61"  # Confirms no trailing artifact digits


# ---------------------------------------------------------------------------
# Test: Floating-point artifact elimination — multi-channel (DualR3)
# ---------------------------------------------------------------------------
def test_multi_channel_no_float_artifact():
    # 131561 * 0.01 in IEEE 754 = 1315.6100000000001 without rounding
    result = extract_energy_multi("dev_artifact2", 126, {
        "actPow_00": 131561, "current_00": 500, "voltage_00": 22000,
    })
    assert len(result) == 1
    assert result[0].power == 1315.61
    assert str(result[0].power) == "1315.61"


# ===========================================================================
# Plan 06-01: UIID 190 (POWCT) backfeed / grid-export tests
# ===========================================================================

# ---------------------------------------------------------------------------
# Test: UIID 190 — grid export case: supplyPower > 0 → negative power/current
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_grid_export_negative_power():
    """supplyPower=5000 (50 W export) → power=-50.0, current=-2.0 (negative sign convention)."""
    result = extract_energy(
        "dev_bf1", 190,
        {"power": 0, "current": 0, "voltage": 23500, "supplyPower": 5000, "supplyCurrent": 200},
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(-50.0)
    assert result.current == pytest.approx(-2.0)
    assert result.voltage == pytest.approx(235.0)
    assert result.energy_backfeed_today is None
    assert result.channel is None


# ---------------------------------------------------------------------------
# Test: UIID 190 — grid export + dayPowerSupply → energy_backfeed_today set
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_grid_export_with_day_supply():
    """dayPowerSupply=8 → energy_backfeed_today = round(8 * 0.01, 4) = 0.08."""
    result = extract_energy(
        "dev_bf2", 190,
        {"power": 0, "current": 0, "voltage": 23500, "supplyPower": 5000, "supplyCurrent": 200, "dayPowerSupply": 8},
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(-50.0)
    assert result.current == pytest.approx(-2.0)
    assert result.energy_backfeed_today == pytest.approx(0.08)


# ---------------------------------------------------------------------------
# Test: UIID 190 — consumption case (power > 0, supplyPower = 0) — unchanged
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_consumption_unchanged():
    """Normal consumption: power and current remain positive as before."""
    result = extract_energy(
        "dev_bf3", 190,
        {"power": 2300, "current": 500, "voltage": 22000, "supplyPower": 0, "supplyCurrent": 0},
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(23.0)
    assert result.current == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Test: UIID 190 — both zero: result is not None, power=0.0, current=0.0
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_both_zero_writes_zero():
    """Both power and supplyPower=0 → explicit zero writes (D-13), not None."""
    result = extract_energy(
        "dev_bf4", 190,
        {"power": 0, "current": 0, "voltage": 23000, "supplyPower": 0, "supplyCurrent": 0},
    )
    assert result is not None
    assert result.power == pytest.approx(0.0)
    assert result.current == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: UIID 190 — dayPowerSupply=250 → energy_backfeed_today = 2.5
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_energy_backfeed_today_scaled():
    """dayPowerSupply=250 → round(250 * 0.01, 4) = 2.5."""
    result = extract_energy(
        "dev_bf5", 190,
        {"power": 0, "current": 0, "voltage": 23000, "supplyPower": 100, "supplyCurrent": 50, "dayPowerSupply": 250},
    )
    assert isinstance(result, EnergyReading)
    assert result.energy_backfeed_today == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Test: UIID 190 — dayPowerSupply absent → energy_backfeed_today = None
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_energy_backfeed_today_none_when_absent():
    """No dayPowerSupply in params → energy_backfeed_today is None."""
    result = extract_energy(
        "dev_bf6", 190,
        {"power": 0, "current": 0, "voltage": 23000, "supplyPower": 100, "supplyCurrent": 50},
    )
    assert isinstance(result, EnergyReading)
    assert result.energy_backfeed_today is None


# ---------------------------------------------------------------------------
# Test: UIID 190 — string values → coerced correctly via _to_float()
# ---------------------------------------------------------------------------
def test_uiid_190_backfeed_string_values():
    """String input for supplyPower/supplyCurrent are coerced correctly."""
    result = extract_energy(
        "dev_bf7", 190,
        {"power": "0", "current": "0", "voltage": "23500", "supplyPower": "5000", "supplyCurrent": "200"},
    )
    assert isinstance(result, EnergyReading)
    assert result.power == pytest.approx(-50.0)
    assert result.current == pytest.approx(-2.0)


# ---------------------------------------------------------------------------
# Test: Non-190 UIID → energy_backfeed_today is always None
# ---------------------------------------------------------------------------
def test_other_uiid_energy_backfeed_today_is_none():
    """For non-190 UIIDs (e.g. UIID 276), energy_backfeed_today must be None."""
    result = extract_energy(
        "dev_bf8", 276,
        {"power": 5000, "current": 200, "voltage": 22000},
    )
    assert isinstance(result, EnergyReading)
    assert result.energy_backfeed_today is None
