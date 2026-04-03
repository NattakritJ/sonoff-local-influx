"""
test_writer.py — Unit tests for InfluxWriter (TDD RED phase).

Tests use mocked InfluxDBClient3 — no live InfluxDB connection required.
"""
import asyncio
import logging
import pytest
from unittest.mock import MagicMock, patch, call

from extractor import EnergyReading
from writer import InfluxWriter


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _reading(
    device_id="dev1",
    uiid=190,
    power=1.5,
    voltage=230.0,
    current=0.5,
    energy_today=None,
    channel=None,
):
    return EnergyReading(
        device_id=device_id,
        uiid=uiid,
        power=power,
        voltage=voltage,
        current=current,
        energy_today=energy_today,
        channel=channel,
    )


def _all_none_reading():
    return EnergyReading(
        device_id="dev1",
        uiid=190,
        power=None,
        voltage=None,
        current=None,
        energy_today=None,
        channel=None,
    )


# ---------------------------------------------------------------------------
# Test 1: Constructor
# ---------------------------------------------------------------------------

def test_constructor_creates_instance():
    """InfluxWriter('http://localhost:8086', 'token', 'db') creates instance without error."""
    with patch("writer.InfluxDBClient3") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        writer = InfluxWriter("http://localhost:8086", "token", "db")
        assert writer is not None
        assert writer._client is mock_client
        mock_cls.assert_called_once_with(
            host="http://localhost:8086",
            token="token",
            database="db",
        )


# ---------------------------------------------------------------------------
# Test 2: measurement name = device_name
# ---------------------------------------------------------------------------

def test_write_builds_point_with_measurement_device_name():
    """write() builds Point with measurement = device_name arg."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        # Set up Point chain
        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(device_id="sonoff_abc123")
        asyncio.run(writer.write(reading, "My Device"))

        # NEW — device_name arg "My Device" is the measurement
        mock_point_cls.assert_called_once_with("My Device")


# ---------------------------------------------------------------------------
# Test 3: no tags
# ---------------------------------------------------------------------------

def test_write_adds_no_tags():
    """write() adds NO tags — measurement name carries device identity."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(device_id="dev42")
        asyncio.run(writer.write(reading, "Dev 42"))

        assert mock_point.tag.call_count == 0


# ---------------------------------------------------------------------------
# Test 4: measurement name uses device_name (with fallback to device_id when None)
# ---------------------------------------------------------------------------

def test_write_measurement_uses_device_name_arg():
    """write() sets measurement name = device_name arg when provided."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(device_id="dev1")
        asyncio.run(writer.write(reading, "Kitchen Plug"))

        mock_point_cls.assert_called_once_with("Kitchen Plug")


def test_write_measurement_falls_back_to_device_id_when_name_is_none():
    """write() sets measurement name = device_id when device_name arg is None."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(device_id="dev99")
        asyncio.run(writer.write(reading, None))

        mock_point_cls.assert_called_once_with("dev99")


# ---------------------------------------------------------------------------
# Test 5: field power
# ---------------------------------------------------------------------------

def test_write_adds_field_power_when_not_none():
    """write() adds field 'power' = reading.power when power is not None."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(power=42.5, voltage=None, current=None)
        asyncio.run(writer.write(reading, "dev"))

        field_calls = mock_point.field.call_args_list
        assert call("power", 42.5) in field_calls


# ---------------------------------------------------------------------------
# Test 6: field voltage
# ---------------------------------------------------------------------------

def test_write_adds_field_voltage_when_not_none():
    """write() adds field 'voltage' = reading.voltage when voltage is not None."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(power=None, voltage=230.5, current=None)
        asyncio.run(writer.write(reading, "dev"))

        field_calls = mock_point.field.call_args_list
        assert call("voltage", 230.5) in field_calls


# ---------------------------------------------------------------------------
# Test 7: field current
# ---------------------------------------------------------------------------

def test_write_adds_field_current_when_not_none():
    """write() adds field 'current' = reading.current when current is not None."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(power=None, voltage=None, current=0.75)
        asyncio.run(writer.write(reading, "dev"))

        field_calls = mock_point.field.call_args_list
        assert call("current", 0.75) in field_calls


# ---------------------------------------------------------------------------
# Test 8: field energy_today
# ---------------------------------------------------------------------------

def test_write_adds_field_energy_today_when_not_none():
    """write() adds field 'energy_today' = reading.energy_today when not None."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(power=1.0, voltage=None, current=None, energy_today=3.14)
        asyncio.run(writer.write(reading, "dev"))

        field_calls = mock_point.field.call_args_list
        assert call("energy_today", 3.14) in field_calls


# ---------------------------------------------------------------------------
# Test 9: omits power field when None
# ---------------------------------------------------------------------------

def test_write_omits_power_field_when_none():
    """write() does NOT add 'power' field when reading.power is None."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.Point") as mock_point_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_cls.return_value = mock_point

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading(power=None, voltage=230.0, current=0.5)
        asyncio.run(writer.write(reading, "dev"))

        field_names = [c[0][0] for c in mock_point.field.call_args_list]
        assert "power" not in field_names


# ---------------------------------------------------------------------------
# Test 10: all-None fields → do NOT call client.write()
# ---------------------------------------------------------------------------

def test_write_does_not_call_client_when_all_fields_none():
    """write() does NOT call client.write() when all four fields are None."""
    with patch("writer.InfluxDBClient3") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _all_none_reading()
        asyncio.run(writer.write(reading, "dev1"))

        assert mock_client.write.call_count == 0


# ---------------------------------------------------------------------------
# Test 11: write() uses asyncio.to_thread()
# ---------------------------------------------------------------------------

def test_write_uses_asyncio_to_thread():
    """write() calls self._client.write via asyncio.to_thread()."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.asyncio") as mock_asyncio:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        # Make asyncio.to_thread a coroutine so it can be awaited
        async def fake_to_thread(fn, **kwargs):
            return fn(**kwargs)

        mock_asyncio.to_thread = fake_to_thread

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading()
        asyncio.run(writer.write(reading, "dev"))

        # client.write was called (through our fake to_thread)
        assert mock_client.write.call_count == 1


# ---------------------------------------------------------------------------
# Test 12: write() returns None on success
# ---------------------------------------------------------------------------

def test_write_returns_none_on_success():
    """write() returns None (awaitable resolves to None)."""
    with patch("writer.InfluxDBClient3") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading()
        result = asyncio.run(writer.write(reading, "dev"))

        assert result is None


# ---------------------------------------------------------------------------
# Test 13: write() swallows exceptions, logs ERROR
# ---------------------------------------------------------------------------

def test_write_catches_exception_and_logs_error(caplog):
    """write() catches exceptions from client.write(), logs ERROR, returns None."""
    with patch("writer.InfluxDBClient3") as mock_cls:
        mock_client = MagicMock()
        mock_client.write.side_effect = Exception("connection refused")
        mock_cls.return_value = mock_client

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        reading = _reading()

        with caplog.at_level(logging.ERROR, logger="writer"):
            result = asyncio.run(writer.write(reading, "dev"))

        assert result is None
        assert any("ERROR" in r.levelname for r in caplog.records)


# ---------------------------------------------------------------------------
# Test 14: check_connectivity() uses asyncio.to_thread()
# ---------------------------------------------------------------------------

def test_check_connectivity_uses_asyncio_to_thread():
    """check_connectivity() calls get_server_version via asyncio.to_thread()."""
    with patch("writer.InfluxDBClient3") as mock_cls, \
         patch("writer.asyncio") as mock_asyncio:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        async def fake_to_thread(fn, **kwargs):
            return fn(**kwargs)

        mock_asyncio.to_thread = fake_to_thread

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        asyncio.run(writer.check_connectivity())

        assert mock_client.get_server_version.call_count == 1


# ---------------------------------------------------------------------------
# Test 15: check_connectivity() returns None on success
# ---------------------------------------------------------------------------

def test_check_connectivity_returns_none_on_success():
    """check_connectivity() returns None (no exception) when get_server_version() succeeds."""
    with patch("writer.InfluxDBClient3") as mock_cls:
        mock_client = MagicMock()
        mock_client.get_server_version.return_value = "v3.0.0"
        mock_cls.return_value = mock_client

        writer = InfluxWriter("http://localhost:8086", "token", "db")
        result = asyncio.run(writer.check_connectivity())

        assert result is None


# ---------------------------------------------------------------------------
# Test 16: check_connectivity() raises RuntimeError on failure
# ---------------------------------------------------------------------------

def test_check_connectivity_raises_runtime_error_on_failure():
    """check_connectivity() raises RuntimeError containing 'InfluxDB unreachable' on failure."""
    with patch("writer.InfluxDBClient3") as mock_cls:
        mock_client = MagicMock()
        mock_client.get_server_version.side_effect = Exception("Connection refused")
        mock_cls.return_value = mock_client

        writer = InfluxWriter("http://localhost:8086", "token", "db")

        with pytest.raises(RuntimeError, match="InfluxDB unreachable"):
            asyncio.run(writer.check_connectivity())


# ---------------------------------------------------------------------------
# Test 17: async coroutines
# ---------------------------------------------------------------------------

def test_write_and_check_connectivity_are_async():
    """write() and check_connectivity() are async coroutine functions."""
    import inspect
    assert inspect.iscoroutinefunction(InfluxWriter.write)
    assert inspect.iscoroutinefunction(InfluxWriter.check_connectivity)
