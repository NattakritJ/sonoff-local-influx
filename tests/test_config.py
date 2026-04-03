"""
Unit tests for src/config.py — parse_log_level().

Covers:
  - LOG_LEVEL unset → defaults to logging.INFO
  - LOG_LEVEL=DEBUG → returns logging.DEBUG
  - LOG_LEVEL=WARNING → returns logging.WARNING
  - LOG_LEVEL=debug (lowercase) → returns logging.DEBUG (case-insensitive)
  - LOG_LEVEL=BOGUS → sys.exit(1) (invalid value)
  - LOG_LEVEL=NOTSET → sys.exit(1) (NOTSET disallowed — too permissive)
"""

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
