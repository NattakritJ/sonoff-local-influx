"""
Unit tests for polling task lifecycle and failure handling in SonoffDaemon.

Covers:
  - _poll_device() coroutine: success (no warning), failure (logs WARNING), cancellation propagates
  - _poll_device() exception from registry.send(): logs WARNING and continues loop
  - SonoffDaemon.run() routing: all-ip → no AsyncZeroconf; no-ip → no polling tasks; mixed → both
"""

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src/ is on path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ---------------------------------------------------------------------------
# Module-level import of src/__main__.py (avoid shadowing pytest __main__)
# ---------------------------------------------------------------------------
_SRC_MAIN_PATH = Path(__file__).parent.parent / "src" / "__main__.py"
_spec = importlib.util.spec_from_file_location("sonoff_main", _SRC_MAIN_PATH)
_sonoff_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sonoff_main)

SonoffDaemon = _sonoff_main.SonoffDaemon
_LOGGER_NAME = "sonoff_main"  # module name used when patching logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cfg(device_id: str, ip: str | None = None, devicekey: str = "key123") -> dict:
    """Build a minimal DeviceConfig dict for test use."""
    cfg = {
        "device_id": device_id,
        "uiid": 190,
        "devicekey": devicekey,
        "device_name": f"Device {device_id}",
    }
    if ip is not None:
        cfg["ip"] = ip
    return cfg


def _make_writer() -> MagicMock:
    """Build a minimal InfluxWriter mock."""
    from writer import InfluxWriter
    writer = MagicMock(spec=InfluxWriter)
    writer._host = "http://localhost:8086"
    return writer


# ---------------------------------------------------------------------------
# TestPollDevice — unit tests for _poll_device() coroutine
# ---------------------------------------------------------------------------


class TestPollDevice:
    """Unit tests for SonoffDaemon._poll_device()."""

    @pytest.mark.asyncio
    async def test_online_result_no_warning(self):
        """send() returns 'online' → _LOGGER.warning is NOT called."""
        daemon = SonoffDaemon([_make_cfg("dev1", ip="192.168.1.10")], _make_writer())

        mock_registry = MagicMock()
        mock_registry.send = AsyncMock(return_value="online")

        cfg = _make_cfg("dev1", ip="192.168.1.10")

        with patch.object(_sonoff_main, "_LOGGER") as mock_logger:
            task = asyncio.create_task(
                daemon._poll_device(cfg, mock_registry, interval=1)
            )
            await asyncio.sleep(0.05)  # Let one iteration complete
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_result_logs_warning(self):
        """send() returns 'timeout' → _LOGGER.warning called with 'POLL FAILED'."""
        daemon = SonoffDaemon([_make_cfg("dev1", ip="192.168.1.10")], _make_writer())

        mock_registry = MagicMock()
        mock_registry.send = AsyncMock(return_value="timeout")

        cfg = _make_cfg("dev1", ip="192.168.1.10")

        with patch.object(_sonoff_main, "_LOGGER") as mock_logger:
            task = asyncio.create_task(
                daemon._poll_device(cfg, mock_registry, interval=1)
            )
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            warning_calls = mock_logger.warning.call_args_list
            assert any("POLL FAILED" in str(c) for c in warning_calls), (
                f"Expected 'POLL FAILED' in warning calls, got: {warning_calls}"
            )

    @pytest.mark.asyncio
    async def test_cancelled_propagates(self):
        """CancelledError from asyncio.sleep() propagates out (not swallowed)."""
        daemon = SonoffDaemon([_make_cfg("dev1", ip="192.168.1.10")], _make_writer())

        mock_registry = MagicMock()
        mock_registry.send = AsyncMock(return_value="online")

        cfg = _make_cfg("dev1", ip="192.168.1.10")

        task = asyncio.create_task(
            daemon._poll_device(cfg, mock_registry, interval=60)
        )
        # Give it a moment to start and reach sleep
        await asyncio.sleep(0.05)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_exception_from_send_logs_warning_and_continues(self):
        """send() raises RuntimeError once → logs WARNING, loop continues (returns 'online' on 2nd call)."""
        daemon = SonoffDaemon([_make_cfg("dev1", ip="192.168.1.10")], _make_writer())

        mock_registry = MagicMock()
        # First call raises, second returns "online"
        mock_registry.send = AsyncMock(
            side_effect=[RuntimeError("connection refused"), "online"]
        )

        cfg = _make_cfg("dev1", ip="192.168.1.10")

        with patch.object(_sonoff_main, "_LOGGER") as mock_logger:
            task = asyncio.create_task(
                daemon._poll_device(cfg, mock_registry, interval=0)
            )
            # Wait enough for 2 iterations (interval=0 means very fast)
            await asyncio.sleep(0.15)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            warning_calls = mock_logger.warning.call_args_list
            assert any("POLL ERROR" in str(c) for c in warning_calls), (
                f"Expected 'POLL ERROR' in warning calls, got: {warning_calls}"
            )
            # Registry should have been called at least twice (exception + success)
            assert mock_registry.send.call_count >= 2


# ---------------------------------------------------------------------------
# TestRunRouting — integration-style unit tests for run() routing logic
# ---------------------------------------------------------------------------


class TestRunRouting:
    """Unit tests for SonoffDaemon.run() device routing (polling vs mDNS)."""

    @pytest.mark.asyncio
    async def test_all_ip_devices_no_azc(self):
        """All devices have ip → AsyncZeroconf is never created."""
        devices = [
            _make_cfg("dev1", ip="192.168.1.10"),
            _make_cfg("dev2", ip="192.168.1.11"),
        ]
        daemon = SonoffDaemon(devices, _make_writer())

        mock_registry = MagicMock()
        mock_registry.dispatcher_connect = MagicMock()
        mock_registry.send = AsyncMock(return_value="online")
        mock_registry.stop = AsyncMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch.object(_sonoff_main, "AsyncZeroconf") as mock_azc_cls, \
             patch.object(_sonoff_main, "XRegistryLocal", return_value=mock_registry), \
             patch.object(_sonoff_main, "aiohttp") as mock_aiohttp, \
             patch.object(_sonoff_main, "parse_poll_interval", return_value=60):

            mock_aiohttp.ClientSession.return_value = mock_session

            async def trigger_shutdown():
                await asyncio.sleep(0.05)
                daemon._shutdown.set()

            asyncio.create_task(trigger_shutdown())
            await daemon.run()

        # AsyncZeroconf should NOT have been instantiated
        mock_azc_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_ip_devices_no_polling_tasks(self):
        """No devices have ip → no poll- named tasks are created."""
        devices = [
            _make_cfg("dev1"),  # no ip
            _make_cfg("dev2"),  # no ip
        ]
        daemon = SonoffDaemon(devices, _make_writer())

        mock_registry = MagicMock()
        mock_registry.dispatcher_connect = MagicMock()
        mock_registry.stop = AsyncMock()
        mock_registry.start = MagicMock()

        mock_azc = MagicMock()
        mock_azc.zeroconf = MagicMock()
        mock_azc.async_close = AsyncMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        poll_task_names: list[str] = []
        _original_create_task = asyncio.create_task

        def track_create_task(coro, **kwargs):
            name = kwargs.get("name", "")
            if isinstance(name, str) and "poll-" in name:
                poll_task_names.append(name)
            return _original_create_task(coro, **kwargs)

        with patch.object(_sonoff_main, "AsyncZeroconf", return_value=mock_azc), \
             patch.object(_sonoff_main, "XRegistryLocal", return_value=mock_registry), \
             patch.object(_sonoff_main, "aiohttp") as mock_aiohttp, \
             patch.object(_sonoff_main, "parse_poll_interval", return_value=60), \
             patch("asyncio.create_task", side_effect=track_create_task):

            mock_aiohttp.ClientSession.return_value = mock_session

            async def trigger_shutdown():
                await asyncio.sleep(0.05)
                daemon._shutdown.set()

            asyncio.create_task(trigger_shutdown())
            await daemon.run()

        assert len(poll_task_names) == 0, (
            f"Expected no poll tasks, but found: {poll_task_names}"
        )

    @pytest.mark.asyncio
    async def test_mixed_both_modes_active(self):
        """One ip device + one mDNS device → both AsyncZeroconf created AND one polling task started."""
        devices = [
            _make_cfg("dev1", ip="192.168.1.10"),  # polling
            _make_cfg("dev2"),  # mDNS
        ]
        daemon = SonoffDaemon(devices, _make_writer())

        mock_registry = MagicMock()
        mock_registry.dispatcher_connect = MagicMock()
        mock_registry.send = AsyncMock(return_value="online")
        mock_registry.stop = AsyncMock()
        mock_registry.start = MagicMock()

        mock_azc = MagicMock()
        mock_azc.zeroconf = MagicMock()
        mock_azc.async_close = AsyncMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        poll_task_names: list[str] = []
        _original_create_task = asyncio.create_task

        def track_create_task(coro, **kwargs):
            name = kwargs.get("name", "")
            if isinstance(name, str) and "poll-" in name:
                poll_task_names.append(name)
            return _original_create_task(coro, **kwargs)

        with patch.object(_sonoff_main, "AsyncZeroconf", return_value=mock_azc) as mock_azc_cls, \
             patch.object(_sonoff_main, "XRegistryLocal", return_value=mock_registry), \
             patch.object(_sonoff_main, "aiohttp") as mock_aiohttp, \
             patch.object(_sonoff_main, "parse_poll_interval", return_value=60), \
             patch("asyncio.create_task", side_effect=track_create_task):

            mock_aiohttp.ClientSession.return_value = mock_session

            async def trigger_shutdown():
                await asyncio.sleep(0.05)
                daemon._shutdown.set()

            asyncio.create_task(trigger_shutdown())
            await daemon.run()

        # AsyncZeroconf should have been created (for mDNS device)
        mock_azc_cls.assert_called_once()
        # One poll task for the ip device
        assert len(poll_task_names) == 1, (
            f"Expected 1 poll task, got: {poll_task_names}"
        )
        assert "poll-dev1" in poll_task_names[0]
