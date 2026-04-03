"""
Integration tests for InfluxWriter against a live InfluxDB 3 Core instance.

Skipped automatically unless INFLUX_HOST env var is set.
Run manually: INFLUX_HOST=http://localhost:8086 INFLUX_TOKEN=mytoken INFLUX_DATABASE=sonoff_test \
              PYTHONPATH=src python -m pytest tests/test_writer_integration.py -v -m integration

Tests (per D-16, D-17):
- Write a real EnergyReading and query it back — verify measurement, tags, fields
- check_connectivity() succeeds against a live server
- check_connectivity() raises RuntimeError against a bad host
"""
import asyncio
import os
import time
import pytest

from extractor import EnergyReading
from writer import InfluxWriter

# Skip all tests in this module unless INFLUX_HOST is set
pytestmark = pytest.mark.skipif(
    not os.environ.get("INFLUX_HOST"),
    reason="Integration tests require INFLUX_HOST env var"
)

# Read connection config from environment
INFLUX_HOST = os.environ.get("INFLUX_HOST", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_DATABASE = os.environ.get("INFLUX_DATABASE", "sonoff_test")


@pytest.fixture
def writer():
    """Create an InfluxWriter backed by the live test instance."""
    w = InfluxWriter(INFLUX_HOST, INFLUX_TOKEN, INFLUX_DATABASE)
    yield w
    w.close()


@pytest.mark.integration
def test_check_connectivity_live(writer):
    """check_connectivity() returns None (no exception) against a live server."""
    asyncio.run(writer.check_connectivity())  # must not raise


@pytest.mark.integration
def test_check_connectivity_bad_host():
    """check_connectivity() raises RuntimeError when host is unreachable."""
    bad_writer = InfluxWriter("http://localhost:19999", "bad_token", "bad_db")
    with pytest.raises(RuntimeError, match="InfluxDB unreachable"):
        asyncio.run(bad_writer.check_connectivity())
    bad_writer.close()


@pytest.mark.integration
def test_write_and_query_single_reading(writer):
    """
    End-to-end: write EnergyReading → query back → verify measurement, tags, fields.

    Uses a unique device_id to avoid collisions with existing data.
    """
    # Construct a test reading with all four fields populated
    device_id = f"inttest_{int(time.time())}"  # unique per run
    reading = EnergyReading(
        device_id=device_id,
        uiid=190,
        power=123.45,
        voltage=230.10,
        current=0.537,
        energy_today=1.23,
        channel=None,
    )
    device_name = "Integration Test Device"

    # Write to InfluxDB
    asyncio.run(writer.write(reading, device_name))

    # Brief pause for InfluxDB 3 Core to flush the write
    time.sleep(0.5)

    # Query back using the measurement name (= device_id per D-01)
    from influxdb_client_3 import InfluxDBClient3
    client = InfluxDBClient3(host=INFLUX_HOST, token=INFLUX_TOKEN, database=INFLUX_DATABASE)
    try:
        # Query the measurement written (measurement name = device_id per D-01)
        result = client.query(
            f'SELECT * FROM "{device_id}" ORDER BY time DESC LIMIT 1',
            language="sql",
            mode="all",
        )
    finally:
        client.close()

    # Verify result has rows
    assert result is not None
    data = result.to_pydict()
    assert len(data.get("device_id", [])) == 1, "Expected exactly one row"

    # Verify tags (per D-02, INF-03)
    assert data["device_id"][0] == device_id, f"device_id tag mismatch"
    assert data["device_name"][0] == device_name, f"device_name tag mismatch"

    # Verify fields (per D-03, INF-01)
    assert abs(data["power"][0] - reading.power) < 0.001, "power field mismatch"
    assert abs(data["voltage"][0] - reading.voltage) < 0.001, "voltage field mismatch"
    assert abs(data["current"][0] - reading.current) < 0.001, "current field mismatch"
    assert abs(data["energy_today"][0] - reading.energy_today) < 0.001, "energy_today field mismatch"


@pytest.mark.integration
def test_write_omits_none_fields(writer):
    """
    Write a reading with power=None — verify the 'power' field is absent from the result.
    """
    device_id = f"inttest_none_{int(time.time())}"
    reading = EnergyReading(
        device_id=device_id,
        uiid=190,
        power=None,      # omit power
        voltage=230.0,
        current=0.5,
        energy_today=None,
        channel=None,
    )

    asyncio.run(writer.write(reading, "None Field Test"))
    time.sleep(0.5)

    from influxdb_client_3 import InfluxDBClient3
    client = InfluxDBClient3(host=INFLUX_HOST, token=INFLUX_TOKEN, database=INFLUX_DATABASE)
    try:
        result = client.query(
            f'SELECT * FROM "{device_id}" ORDER BY time DESC LIMIT 1',
            language="sql",
            mode="all",
        )
    finally:
        client.close()

    data = result.to_pydict()
    assert len(data.get("device_id", [])) == 1
    # power must be absent or None — not a real float
    assert "power" not in data or data["power"][0] is None, \
        "power field should be absent when reading.power is None"
    # voltage and current should be present
    assert abs(data["voltage"][0] - 230.0) < 0.001
    assert abs(data["current"][0] - 0.5) < 0.001
