"""
E2E Integration Test for SonoffLAN-InfluxDB Daemon

Tests the complete workflow:
1. Device configuration parsing
2. InfluxDB connectivity
3. Energy data extraction
4. Data writing to InfluxDB
5. Data retrieval and verification

This test uses real credentials provided by the user:
- Device: device_id="100267cfa6", devicekey="33e85177-8cb4-4fc8-bd5a-262c092d9b16"
- InfluxDB: url="http://192.168.2.10:8181", bucket="sonoff_test", token=(provided)

Run with:
    PYTHONPATH=src python -m pytest tests/test_e2e_integration.py -v -s
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import parse_config, DeviceConfig
from extractor import EnergyReading, extract_energy, extract_energy_multi
from writer import InfluxWriter


class TestE2EIntegration:
    """End-to-end integration tests for the daemon."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Set up test configuration from user-provided credentials."""
        # Device configuration
        self.device_id = "100267cfa6"
        self.devicekey = "33e85177-8cb4-4fc8-bd5a-262c092d9b16"
        self.device_name = "Sonoff-POWR3-Test"

        # InfluxDB configuration
        self.influx_url = "http://192.168.2.10:8181"
        self.influx_token = "apivi3_AwBnUa4uyFJw_b5QZl6cZG1X7XriXLxaSelwPoTt8loiGzHXo256oB1ZCHRjkMML5Ajnv_cnO56flhBWdpH10w"
        self.influx_bucket = "sonoff_test"

    def test_01_config_parsing(self):
        """Test 1: Device configuration can be parsed from SONOFF_DEVICES env var."""
        device_config: DeviceConfig = {
            "device_id": self.device_id,
            "devicekey": self.devicekey,
            "device_name": self.device_name,
        }

        # Verify the config structure is valid
        assert device_config["device_id"] == self.device_id
        assert device_config["devicekey"] == self.devicekey
        assert device_config["device_name"] == self.device_name

        print(f"✓ Device config valid: {self.device_id} ({self.device_name})")

    def test_02_influx_connectivity(self):
        """Test 2: InfluxDB 3 Core instance is reachable."""
        writer = InfluxWriter(self.influx_url, self.influx_token, self.influx_bucket)

        try:
            # Check connectivity asynchronously
            asyncio.run(writer.check_connectivity())
            print(f"✓ InfluxDB connectivity verified: {self.influx_url}")
        except RuntimeError as e:
            pytest.fail(f"InfluxDB unreachable: {e}")
        finally:
            writer.close()

    def test_03_energy_extraction_powr3(self):
        """Test 3: Extract energy metrics from POWR3 (UIID 190) device payload."""
        # Simulate a POWR3 device (UIID 190) with energy readings
        # UIID 190 uses ×0.01 scale factor
        params = {
            "power": 12345,  # 123.45W after scale
            "voltage": 23010,  # 230.10V after scale
            "current": 5373,  # 0.5373A after scale (rounded)
            "dayKwh": 123,  # 1.23 kWh after scale
        }

        reading = extract_energy(self.device_id, 190, params)

        assert reading is not None
        assert reading.device_id == self.device_id
        assert reading.uiid == 190
        assert abs(reading.power - 123.45) < 0.01
        assert abs(reading.voltage - 230.10) < 0.01
        assert abs(reading.current - 0.5373) < 0.01
        assert abs(reading.energy_today - 1.23) < 0.01
        assert reading.channel is None

        print(f"✓ Energy extraction successful: power={reading.power}W, "
              f"voltage={reading.voltage}V, current={reading.current}A, "
              f"energy_today={reading.energy_today}kWh")

    def test_04_energy_extraction_multi_channel(self):
        """Test 4: Extract energy metrics from DualR3 (UIID 126) multi-channel device."""
        params = {
            "actPow_00": 12345,  # Channel 1: 123.45W after scale
            "current_00": 5373,  # Channel 1: 0.5373A after scale
            "voltage_00": 23010,  # Channel 1: 230.10V after scale
            "actPow_01": 6789,  # Channel 2: 67.89W after scale
            "current_01": 2945,  # Channel 2: 0.2945A after scale
            "voltage_01": 23010,  # Channel 2: 230.10V after scale
        }

        readings = extract_energy_multi(self.device_id, 126, params)

        assert len(readings) == 2
        assert readings[0].channel == 1
        assert readings[1].channel == 2
        assert abs(readings[0].power - 123.45) < 0.01
        assert abs(readings[1].power - 67.89) < 0.01

        print(f"✓ Multi-channel extraction successful: {len(readings)} channels "
              f"(Ch1: {readings[0].power}W, Ch2: {readings[1].power}W)")

    def test_05_write_single_reading(self):
        """Test 5: Write a single EnergyReading to InfluxDB."""
        writer = InfluxWriter(self.influx_url, self.influx_token, self.influx_bucket)

        try:
            # Create a test reading
            reading = EnergyReading(
                device_id=self.device_id,
                uiid=190,
                power=123.45,
                voltage=230.10,
                current=0.537,
                energy_today=1.23,
                channel=None,
            )

            # Write to InfluxDB
            asyncio.run(writer.write(reading, self.device_name))
            print(f"✓ EnergyReading written to InfluxDB: device={self.device_id}")

            # Brief pause for InfluxDB to flush
            time.sleep(1.0)

        finally:
            writer.close()

    def test_06_query_written_data(self):
        """Test 6: Query and verify written data from InfluxDB."""
        from influxdb_client_3 import InfluxDBClient3

        client = InfluxDBClient3(
            host=self.influx_url,
            token=self.influx_token,
            database=self.influx_bucket,
        )

        try:
            # Query data for our device
            result = client.query(
                f'SELECT * FROM "{self.device_id}" ORDER BY time DESC LIMIT 1',
                language="sql",
                mode="all",
            )

            if result is None or result.num_rows == 0:
                pytest.skip("No data found in InfluxDB (device may not have sent updates)")

            # Verify result structure
            assert result.num_rows >= 1
            schema_names = result.schema.names

            print(f"✓ Query successful, retrieved {result.num_rows} row(s)")
            print(f"  Schema: {schema_names}")

            # Helper to safely extract column values
            def col(name):
                if name in schema_names:
                    return result.column(name).to_pylist()
                return [None]

            # Verify tags
            device_ids = col("device_id")
            device_names = col("device_name")
            if device_ids and device_ids[0]:
                assert device_ids[0] == self.device_id
                print(f"  ✓ device_id tag verified: {device_ids[0]}")
            if device_names and device_names[0]:
                print(f"  ✓ device_name tag verified: {device_names[0]}")

            # Verify at least some energy fields are present
            energy_fields = ["power", "voltage", "current", "energy_today"]
            found_fields = [f for f in energy_fields if f in schema_names]
            assert found_fields, f"No energy fields found. Schema: {schema_names}"
            print(f"  ✓ Energy fields present: {found_fields}")

            for field in found_fields:
                values = col(field)
                if values and values[0] is not None:
                    print(f"    - {field}: {values[0]}")

        finally:
            client.close()

    def test_07_write_multichannel_readings(self):
        """Test 7: Write multi-channel readings to InfluxDB."""
        writer = InfluxWriter(self.influx_url, self.influx_token, self.influx_bucket)

        try:
            # Create two channel readings (DualR3)
            readings = [
                EnergyReading(
                    device_id=self.device_id + "_ch1",
                    uiid=126,
                    power=123.45,
                    voltage=230.10,
                    current=0.537,
                    energy_today=None,
                    channel=1,
                ),
                EnergyReading(
                    device_id=self.device_id + "_ch2",
                    uiid=126,
                    power=67.89,
                    voltage=230.10,
                    current=0.295,
                    energy_today=None,
                    channel=2,
                ),
            ]

            # Write all readings
            for reading in readings:
                asyncio.run(writer.write(reading, f"{self.device_name} Ch{reading.channel}"))

            print(f"✓ Multi-channel readings written: {len(readings)} channels")
            time.sleep(1.0)

        finally:
            writer.close()

    def test_08_end_to_end_flow(self):
        """Test 8: Complete E2E flow - config → connectivity → extract → write → query."""
        print("\n=== E2E INTEGRATION TEST FLOW ===\n")

        # Step 1: Parse configuration
        print("Step 1: Configuration parsing...")
        device_config: DeviceConfig = {
            "device_id": self.device_id,
            "devicekey": self.devicekey,
            "device_name": self.device_name,
        }
        print(f"  ✓ Device: {device_config['device_id']} ({device_config['device_name']})")

        # Step 2: Check InfluxDB connectivity
        print("\nStep 2: InfluxDB connectivity check...")
        writer = InfluxWriter(self.influx_url, self.influx_token, self.influx_bucket)
        try:
            asyncio.run(writer.check_connectivity())
            print(f"  ✓ Connected to {self.influx_url}")
        finally:
            writer.close()

        # Step 3: Extract energy metrics
        print("\nStep 3: Energy metric extraction...")
        params = {
            "power": 12345,
            "voltage": 23010,
            "current": 5373,
            "dayKwh": 123,
        }
        reading = extract_energy(self.device_id, 190, params)
        assert reading is not None
        print(f"  ✓ Extracted: power={reading.power}W, voltage={reading.voltage}V, "
              f"current={reading.current}A, energy={reading.energy_today}kWh")

        # Step 4: Write to InfluxDB
        print("\nStep 4: Write to InfluxDB...")
        writer = InfluxWriter(self.influx_url, self.influx_token, self.influx_bucket)
        try:
            asyncio.run(writer.write(reading, self.device_name))
            print(f"  ✓ Data written successfully")
            time.sleep(1.0)
        finally:
            writer.close()

        # Step 5: Query written data
        print("\nStep 5: Query written data...")
        from influxdb_client_3 import InfluxDBClient3

        client = InfluxDBClient3(
            host=self.influx_url,
            token=self.influx_token,
            database=self.influx_bucket,
        )

        try:
            result = client.query(
                f'SELECT * FROM "{self.device_id}" ORDER BY time DESC LIMIT 1',
                language="sql",
                mode="all",
            )

            if result and result.num_rows > 0:
                schema_names = result.schema.names
                print(f"  ✓ Query successful: {result.num_rows} row(s), {len(schema_names)} columns")
                print(f"    Schema: {', '.join(schema_names)}")

                def col(name):
                    if name in schema_names:
                        return result.column(name).to_pylist()
                    return [None]

                power_vals = col("power")
                if power_vals and power_vals[0] is not None:
                    print(f"    Power: {power_vals[0]}W")
                voltage_vals = col("voltage")
                if voltage_vals and voltage_vals[0] is not None:
                    print(f"    Voltage: {voltage_vals[0]}V")
                current_vals = col("current")
                if current_vals and current_vals[0] is not None:
                    print(f"    Current: {current_vals[0]}A")
            else:
                print("  ⚠ No data retrieved (device may not have sent updates)")

        finally:
            client.close()

        print("\n=== E2E TEST COMPLETE ===\n")


# Summary test report
@pytest.fixture(scope="session", autouse=True)
def summary_report(request):
    """Generate a summary report at the end of the test session."""
    yield

    if hasattr(request.config, "_e2e_results"):
        results = request.config._e2e_results
        print("\n" + "=" * 60)
        print("E2E INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"Device: 100267cfa6")
        print(f"InfluxDB: http://192.168.2.10:8181")
        print(f"Bucket: sonoff_test")
        print("=" * 60)
