"""
TDD tests for src/extractor.py — EnergyReading dataclass + extract_energy() function.

Covers all single-channel UIIDs:
  - UIID 32  (POWR2):          power/current/voltage ×1
  - UIID 182 (S40):            power/current/voltage ×1
  - UIID 190 (POWR3/S60):      power/current/voltage ×0.01, dayKwh → energy_today ×0.01
  - UIID 226 (CK-BL602):       phase_0_p/c/v → power/current/voltage ×1
  - UIID 262 (CK-BL602-SWP1):  power/current/voltage ×0.01
  - UIID 276 (S61STPF):        power/current/voltage ×0.01, dayKwh → energy_today ×0.01
  - UIID 277 (XMiniDim):       power/current/voltage ×0.01
  - UIID 7032 (S60ZBTPF):      power/current/voltage ×0.01, dayKwh → energy_today ×0.01
"""
import pytest
import sys
import os

# Ensure src/ is on path so `from extractor import ...` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extractor import EnergyReading, extract_energy  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1: UIID 32 (POWR2) — int raw params → float output, ×1, channel=None
# ---------------------------------------------------------------------------
def test_uiid_32_int_params_scale_x1():
    result = extract_energy("dev1", 32, {"power": 2300, "current": 500, "voltage": 23000})
    assert isinstance(result, EnergyReading)
    assert result.device_id == "dev1"
    assert result.uiid == 32
    assert result.power == pytest.approx(2300.0)
    assert result.current == pytest.approx(500.0)
    assert result.voltage == pytest.approx(23000.0)
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
