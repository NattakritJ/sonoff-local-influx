"""
Unit tests for src/config.py — parse_log_level(), parse_config() ip field, parse_poll_interval().

Covers:
  - LOG_LEVEL unset → defaults to logging.INFO
  - LOG_LEVEL=DEBUG → returns logging.DEBUG
  - LOG_LEVEL=WARNING → returns logging.WARNING
  - LOG_LEVEL=debug (lowercase) → returns logging.DEBUG (case-insensitive)
  - LOG_LEVEL=BOGUS → sys.exit(1) (invalid value)
  - LOG_LEVEL=NOTSET → sys.exit(1) (NOTSET disallowed — too permissive)
  - DeviceConfig ip field: optional, conditionally populated from JSON
  - parse_poll_interval(): default 10, valid integers, sys.exit(1) on invalid
"""

import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is on path so `from config import ...` works
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestParseLogLevel:
    """Unit tests for parse_log_level() in config.py."""

    def test_unset_defaults_to_info(self):
        """LOG_LEVEL unset → returns logging.INFO (20)."""
        from config import parse_log_level

        env = {k: v for k, v in os.environ.items() if k != "LOG_LEVEL"}
        with patch.dict(os.environ, env, clear=True):
            assert parse_log_level() == logging.INFO

    def test_debug_returns_debug(self):
        """LOG_LEVEL=DEBUG → returns logging.DEBUG (10)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            assert parse_log_level() == logging.DEBUG

    def test_warning_returns_warning(self):
        """LOG_LEVEL=WARNING → returns logging.WARNING (30)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            assert parse_log_level() == logging.WARNING

    def test_error_returns_error(self):
        """LOG_LEVEL=ERROR → returns logging.ERROR (40)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            assert parse_log_level() == logging.ERROR

    def test_critical_returns_critical(self):
        """LOG_LEVEL=CRITICAL → returns logging.CRITICAL (50)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "CRITICAL"}):
            assert parse_log_level() == logging.CRITICAL

    def test_lowercase_case_insensitive(self):
        """LOG_LEVEL=debug (lowercase) → returns logging.DEBUG (case-insensitive)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            assert parse_log_level() == logging.DEBUG

    def test_mixed_case_accepted(self):
        """LOG_LEVEL=Warning (mixed case) → returns logging.WARNING."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "Warning"}):
            assert parse_log_level() == logging.WARNING

    def test_invalid_level_exits(self):
        """LOG_LEVEL=BOGUS → calls sys.exit(1) with clear error message."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "BOGUS"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_log_level()
            assert exc_info.value.code == 1

    def test_notset_disallowed(self):
        """LOG_LEVEL=NOTSET → calls sys.exit(1) (too permissive, disallowed)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "NOTSET"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_log_level()
            assert exc_info.value.code == 1

    def test_numeric_string_invalid(self):
        """LOG_LEVEL=10 (numeric string) → calls sys.exit(1)."""
        from config import parse_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "10"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_log_level()
            assert exc_info.value.code == 1


class TestParseConfigIp:
    """Unit tests for ip field in DeviceConfig / parse_config()."""

    def _devices_env(self, devices: list) -> str:
        """Helper to JSON-encode devices list for SONOFF_DEVICES env var."""
        return json.dumps(devices)

    def test_device_without_ip_has_no_ip_key(self):
        """Device without 'ip' key → DeviceConfig has no 'ip' key (total=False, optional)."""
        from config import parse_config

        devices = [{"device_id": "1000aabbcc", "uiid": 190, "devicekey": "abc123"}]
        with patch.dict(os.environ, {"SONOFF_DEVICES": self._devices_env(devices)}):
            result = parse_config()
        assert len(result) == 1
        assert "ip" not in result[0]

    def test_device_with_ip_includes_ip_field(self):
        """Device with 'ip' field → parse_config() includes ip in DeviceConfig."""
        from config import parse_config

        devices = [{"device_id": "1000aabbcc", "uiid": 190, "devicekey": "abc123", "ip": "192.168.1.50"}]
        with patch.dict(os.environ, {"SONOFF_DEVICES": self._devices_env(devices)}):
            result = parse_config()
        assert len(result) == 1
        assert result[0]["ip"] == "192.168.1.50"

    def test_device_with_ip_and_devicekey_both_present(self):
        """Device with ip + devicekey → both fields present in DeviceConfig."""
        from config import parse_config

        devices = [{"device_id": "1000aabbcc", "uiid": 190, "devicekey": "secret123", "ip": "10.0.0.5"}]
        with patch.dict(os.environ, {"SONOFF_DEVICES": self._devices_env(devices)}):
            result = parse_config()
        assert result[0]["ip"] == "10.0.0.5"
        assert result[0]["devicekey"] == "secret123"

    def test_existing_config_without_ip_parses_without_error(self):
        """Existing configs without ip continue to parse without error (backward compat)."""
        from config import parse_config

        devices = [{"device_id": "olddevice", "uiid": 32}]
        with patch.dict(os.environ, {"SONOFF_DEVICES": self._devices_env(devices)}):
            result = parse_config()
        assert result[0]["device_id"] == "olddevice"
        assert "ip" not in result[0]

    def test_mixed_devices_some_with_ip_some_without(self):
        """Two devices: one with ip, one without → only first has ip key."""
        from config import parse_config

        devices = [
            {"device_id": "dev1", "uiid": 190, "ip": "192.168.1.10"},
            {"device_id": "dev2", "uiid": 32},
        ]
        with patch.dict(os.environ, {"SONOFF_DEVICES": self._devices_env(devices)}):
            result = parse_config()
        assert result[0]["ip"] == "192.168.1.10"
        assert "ip" not in result[1]


class TestParsePollInterval:
    """Unit tests for parse_poll_interval() in config.py."""

    def test_unset_returns_default_10(self):
        """SONOFF_POLL_INTERVAL unset → returns 10 (integer default)."""
        from config import parse_poll_interval

        env = {k: v for k, v in os.environ.items() if k != "SONOFF_POLL_INTERVAL"}
        with patch.dict(os.environ, env, clear=True):
            result = parse_poll_interval()
        assert result == 10
        assert isinstance(result, int)

    def test_valid_30(self):
        """SONOFF_POLL_INTERVAL='30' → returns 30."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "30"}):
            assert parse_poll_interval() == 30

    def test_valid_1_minimum(self):
        """SONOFF_POLL_INTERVAL='1' → returns 1 (minimum valid)."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "1"}):
            assert parse_poll_interval() == 1

    def test_valid_3600(self):
        """SONOFF_POLL_INTERVAL='3600' → returns 3600."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "3600"}):
            assert parse_poll_interval() == 3600

    def test_zero_exits(self):
        """SONOFF_POLL_INTERVAL='0' → sys.exit(1) with clear error message."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "0"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_poll_interval()
            assert exc_info.value.code == 1

    def test_negative_exits(self):
        """SONOFF_POLL_INTERVAL='-5' → sys.exit(1) with clear error message."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "-5"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_poll_interval()
            assert exc_info.value.code == 1

    def test_non_integer_string_exits(self):
        """SONOFF_POLL_INTERVAL='abc' → sys.exit(1) with clear error message."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "abc"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_poll_interval()
            assert exc_info.value.code == 1

    def test_float_string_exits(self):
        """SONOFF_POLL_INTERVAL='10.5' → sys.exit(1) (not an integer)."""
        from config import parse_poll_interval

        with patch.dict(os.environ, {"SONOFF_POLL_INTERVAL": "10.5"}):
            with pytest.raises(SystemExit) as exc_info:
                parse_poll_interval()
            assert exc_info.value.code == 1
