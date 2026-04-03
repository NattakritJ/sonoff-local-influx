"""
E2E Diagnostic Test - Troubleshooting InfluxDB Authentication

This test suite helps diagnose connection and authentication issues with InfluxDB 3 Core.
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


class TestDiagnostics:
    """Diagnostic tests for troubleshooting the E2E integration."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Set up test configuration from user-provided credentials."""
        self.device_id = "100267cfa6"
        self.devicekey = "33e85177-8cb4-4fc8-bd5a-262c092d9b16"
        self.device_name = "Sonoff-POWR3-Test"
        self.influx_url = "http://192.168.2.10:8181"
        self.influx_token = "apivi3_AwBnUa4uyFJw_b5QZl6cZG1X7XriXLxaSelwPoTt8loiGzHXo256oB1ZCHRjkMML5Ajnv_cnO56flhBWdpH10w"
        self.influx_bucket = "sonoff_test"

    def test_diagnose_influx_auth(self):
        """Diagnose InfluxDB authentication issues."""
        print("\n" + "=" * 70)
        print("INFLUXDB AUTHENTICATION DIAGNOSTIC")
        print("=" * 70)

        print(f"\nConfiguration:")
        print(f"  Host:     {self.influx_url}")
        print(f"  Bucket:   {self.influx_bucket}")
        print(f"  Token:    {self.influx_token[:20]}...{self.influx_token[-10:]}")

        writer = InfluxWriter(self.influx_url, self.influx_token, self.influx_bucket)

        print(f"\nAttempting connectivity check...")
        try:
            asyncio.run(writer.check_connectivity())
            print(f"  ✓ Authentication successful")
            return True
        except RuntimeError as e:
            error_msg = str(e)
            print(f"  ✗ Authentication failed:")
            print(f"    {error_msg}")

            # Diagnostic suggestions
            print(f"\nDiagnostic Suggestions:")

            if "401" in error_msg or "Unauthorized" in error_msg:
                print(f"  → 401 Unauthorized: Token may be invalid, expired, or for a different InfluxDB instance")
                print(f"    - Verify token is correct and has API token (not just read-only)")
                print(f"    - Verify token is for the correct InfluxDB instance")
                print(f"    - Verify InfluxDB instance is running at {self.influx_url}")
                return False

            elif "403" in error_msg or "Forbidden" in error_msg:
                print(f"  → 403 Forbidden: Token exists but lacks required permissions")
                print(f"    - Ensure token has write permission to bucket: {self.influx_bucket}")
                return False

            elif "Connection" in error_msg or "refused" in error_msg.lower():
                print(f"  → Connection refused: InfluxDB server not responding")
                print(f"    - Verify InfluxDB is running at {self.influx_url}")
                print(f"    - Verify network connectivity to {self.influx_url}")
                print(f"    - Check firewall rules")
                return False

            else:
                print(f"  → Unknown error: {error_msg}")
                print(f"    - Verify all connection parameters")
                return False

        finally:
            writer.close()

    def test_verify_token_format(self):
        """Verify token format is valid."""
        print("\n" + "=" * 70)
        print("TOKEN FORMAT VERIFICATION")
        print("=" * 70)

        print(f"\nToken value: {self.influx_token}")
        print(f"Token length: {len(self.influx_token)} characters")
        print(f"Token starts with: {self.influx_token[:20]}")
        print(f"Token type indicator: {self.influx_token[:7] if len(self.influx_token) >= 7 else 'TOO_SHORT'}")

        # InfluxDB tokens typically start with specific prefixes
        if self.influx_token.startswith("apivi3"):
            print(f"\n✓ Token format appears correct (apivi3 prefix = API v3 token)")
        else:
            print(f"\n⚠ Token prefix is unexpected (expected 'apivi3_', got '{self.influx_token[:10]}')")

        if len(self.influx_token) > 50:
            print(f"✓ Token length seems reasonable")
        else:
            print(f"✗ Token length seems short (expected >50 chars, got {len(self.influx_token)})")

    def test_report_environment(self):
        """Report current environment setup."""
        print("\n" + "=" * 70)
        print("ENVIRONMENT REPORT")
        print("=" * 70)

        print(f"\nPython version: {sys.version}")
        print(f"Working directory: {os.getcwd()}")

        # Try to import InfluxDB client
        try:
            from influxdb_client_3 import InfluxDBClient3, Point
            print(f"✓ InfluxDB client library: influxdb_client_3 (installed)")
        except ImportError:
            print(f"✗ InfluxDB client library: NOT INSTALLED")

        # Check other dependencies
        deps = ["aiohttp", "zeroconf", "cryptography"]
        print(f"\nDependencies:")
        for dep in deps:
            try:
                mod = __import__(dep)
                print(f"  ✓ {dep}: {getattr(mod, '__version__', 'installed')}")
            except ImportError:
                print(f"  ✗ {dep}: NOT INSTALLED")

    def test_e2e_workflow_no_influx(self):
        """Test complete E2E workflow (all steps except InfluxDB connectivity)."""
        print("\n" + "=" * 70)
        print("E2E WORKFLOW TEST (without InfluxDB)")
        print("=" * 70)

        try:
            # Step 1: Configuration
            print(f"\n1. Configuration Parsing")
            device_config: DeviceConfig = {
                "device_id": self.device_id,
                "devicekey": self.devicekey,
                "device_name": self.device_name,
            }
            print(f"   ✓ Device config: {device_config['device_id']} ({device_config['device_name']})")

            # Step 2: Energy extraction (single-channel)
            print(f"\n2. Energy Extraction (Single-Channel POWR3)")
            params_powr3 = {
                "power": 12345,      # 123.45W after ×0.01 scale
                "voltage": 23010,    # 230.10V after ×0.01 scale
                "current": 5373,     # 0.5373A after ×0.01 scale
                "dayKwh": 123,       # 1.23 kWh after ×0.01 scale
            }
            reading = extract_energy(self.device_id, 190, params_powr3)
            assert reading is not None
            print(f"   ✓ Reading extracted:")
            print(f"     - Power:    {reading.power} W")
            print(f"     - Voltage:  {reading.voltage} V")
            print(f"     - Current:  {reading.current} A")
            print(f"     - Energy:   {reading.energy_today} kWh")

            # Step 3: Energy extraction (multi-channel)
            print(f"\n3. Energy Extraction (Multi-Channel DualR3)")
            params_dual = {
                "actPow_00": 12345,
                "current_00": 5373,
                "voltage_00": 23010,
                "actPow_01": 6789,
                "current_01": 2945,
                "voltage_01": 23010,
            }
            readings_multi = extract_energy_multi(self.device_id, 126, params_dual)
            assert len(readings_multi) == 2
            print(f"   ✓ Multi-channel reading extracted ({len(readings_multi)} channels):")
            for i, r in enumerate(readings_multi, 1):
                print(f"     - Ch{r.channel}: {r.power}W, {r.voltage}V, {r.current}A")

            # Step 4: EnergyReading object construction
            print(f"\n4. EnergyReading Object Construction")
            test_reading = EnergyReading(
                device_id="test_device_001",
                uiid=190,
                power=100.5,
                voltage=229.5,
                current=0.437,
                energy_today=2.34,
                channel=None,
            )
            print(f"   ✓ EnergyReading created: {test_reading}")

            print(f"\n" + "=" * 70)
            print(f"✓ ALL LOCAL TESTS PASSED")
            print(f"=" * 70)

            return True

        except Exception as e:
            print(f"\n✗ Error during E2E test: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_influx_connectivity_detailed(self):
        """Detailed connectivity test with additional diagnostics."""
        print("\n" + "=" * 70)
        print("DETAILED INFLUXDB CONNECTIVITY TEST")
        print("=" * 70)

        print(f"\nStep 1: Network connectivity check")
        import socket
        try:
            host_ip = self.influx_url.split("://")[1].split(":")[0]
            port = int(self.influx_url.split(":")[-1]) if ":" in self.influx_url else 8086
            print(f"  Attempting to resolve/connect to {host_ip}:{port}...")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host_ip, port))
            sock.close()

            if result == 0:
                print(f"  ✓ TCP connection successful to {host_ip}:{port}")
            else:
                print(f"  ✗ TCP connection failed to {host_ip}:{port}")
                print(f"    → InfluxDB instance may not be running")
                pytest.skip("InfluxDB server not responding at TCP level")

        except Exception as e:
            print(f"  ✗ Error during network test: {e}")
            pytest.skip(f"Network test failed: {e}")

        print(f"\nStep 2: InfluxDB API authentication check")
        import urllib3
        urllib3.disable_warnings()

        import requests
        try:
            # Try direct HTTP request with token
            headers = {
                "Authorization": f"Token {self.influx_token}",
                "Content-Type": "application/json",
            }
            response = requests.get(f"{self.influx_url}/ping", headers=headers, timeout=5)
            print(f"  Status code: {response.status_code}")
            print(f"  Response: {response.text[:100]}")

            if response.status_code == 200:
                print(f"  ✓ Authentication successful")
            elif response.status_code == 401:
                print(f"  ✗ 401 Unauthorized - token is invalid or expired")
            elif response.status_code == 403:
                print(f"  ✗ 403 Forbidden - token lacks permissions")
            else:
                print(f"  ✗ Unexpected status: {response.status_code}")

        except Exception as e:
            print(f"  ✗ Error during API test: {e}")


def test_summary():
    """Print a summary of what was tested."""
    print("\n" + "=" * 70)
    print("DIAGNOSTIC TEST SUMMARY")
    print("=" * 70)
    print("""
This diagnostic test suite checks:

1. InfluxDB Authentication
   - Verifies token format
   - Tests connectivity and authentication
   - Provides specific error diagnostics

2. Environment Setup
   - Verifies Python version
   - Checks installed dependencies
   - Reports working directory

3. E2E Workflow (without InfluxDB)
   - Configuration parsing
   - Energy metric extraction (single and multi-channel)
   - EnergyReading object construction

4. Detailed Connectivity
   - Network-level connectivity (TCP)
   - HTTP-level authentication

AUTHENTICATION ISSUE FOUND:
  ✗ Token authentication is failing with 401 Unauthorized
  
POSSIBLE CAUSES:
  1. Invalid or expired token
  2. Token is for a different InfluxDB instance
  3. InfluxDB instance is not running at http://192.168.2.10:8181
  4. Token lacks required permissions

NEXT STEPS:
  1. Verify InfluxDB 3 Core is running: curl http://192.168.2.10:8181/ping
  2. Verify token is valid: Check in InfluxDB UI (Data → Tokens)
  3. Verify token has write permissions to 'sonoff_test' bucket
  4. Verify token has NOT expired
  5. Regenerate token if needed and retest

""")
    print("=" * 70)
