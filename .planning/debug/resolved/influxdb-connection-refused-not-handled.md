---
status: resolved
trigger: "When InfluxDB is down, the daemon throws an unhandled NewConnectionError / ConnectionRefusedError traceback instead of silently logging and continuing."
created: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — The except clause in writer.py already caught the exception broadly (Exception), but passed `exc_info=e` to `_LOGGER.error()` which forced the full traceback to be printed.
test: Replaced `_LOGGER.error(... exc_info=e)` with `_LOGGER.warning("InfluxDB write failed: %s", e)`.
expecting: All 18 unit tests pass (confirmed). Next: human verify in live environment.
next_action: Await human confirmation that live daemon no longer prints traceback on InfluxDB downtime.

## Symptoms

expected: When InfluxDB is unavailable, the daemon logs a warning and continues processing the next event without crashing or printing a full traceback.
actual: A full traceback is printed to stdout ending with `urllib3.exceptions.NewConnectionError: HTTPConnection(host='192.168.2.10', port=8181): Failed to establish a new connection: [Errno 111] Connection refused`. The stack originates at `/app/src/writer.py` line 70.
errors: |
  File "/app/src/writer.py", line 70, in write
      await asyncio.to_thread(self._client.write, record=point)
  ...
  urllib3.exceptions.NewConnectionError: HTTPConnection(host='192.168.2.10', port=8181): Failed to establish a new connection: [Errno 111] Connection refused
reproduction: Stop the InfluxDB container while the daemon is running. The next telemetry event write attempt produces the traceback.
started: Existing behaviour — error handling for InfluxDB downtime was never implemented.

## Eliminated

- hypothesis: Exception is unhandled / escapes the try/except block entirely
  evidence: src/writer.py lines 71-77 already have `except Exception as e` wrapping the write call — the exception IS caught. The traceback comes from `exc_info=e` passed to `_LOGGER.error()`, not from an unhandled exception.
  timestamp: 2026-04-04T00:00:00Z

- hypothesis: urllib3.exceptions.NewConnectionError is not a subclass of Exception and evades the broad catch
  evidence: Checked MRO: NewConnectionError -> ConnectTimeoutError -> TimeoutError -> HTTPError -> Exception. It IS caught by `except Exception`.
  timestamp: 2026-04-04T00:00:00Z

## Evidence

- timestamp: 2026-04-04T00:00:00Z
  checked: src/writer.py lines 68-77
  found: try/except Exception block exists; uses `_LOGGER.error(..., exc_info=e)` which prints full traceback
  implication: The exception IS caught; the traceback is deliberately printed by `exc_info=e`. Fix = remove exc_info and downgrade to warning.

- timestamp: 2026-04-04T00:00:00Z
  checked: InfluxDBClient3.write() source (influxdb_client_3 package)
  found: Only catches InfluxDBError (HTTP-level errors). Raw urllib3/network exceptions (NewConnectionError, MaxRetryError) are NOT wrapped — they propagate directly through to our code.
  implication: Our except Exception is the only catch point. We need it to be broad (Exception) to catch both InfluxDBError and raw urllib3 errors.

- timestamp: 2026-04-04T00:00:00Z
  checked: urllib3.exceptions.NewConnectionError MRO
  found: NewConnectionError -> ConnectTimeoutError -> TimeoutError -> HTTPError -> Exception (NOT OSError, NOT InfluxDBError)
  implication: A narrow catch of `OSError` or `InfluxDBError` alone would NOT catch this. Must catch `Exception` broadly.

- timestamp: 2026-04-04T00:00:00Z
  checked: src/__main__.py lines 113-127 (caller: _write_reading)
  found: Caller does NOT wrap write() in try/except; comment says "writer.write() never raises". No changes needed to caller.
  implication: writer.py is the correct and only place to fix. Caller design is correct and consistent with the fix.

- timestamp: 2026-04-04T00:00:00Z
  checked: Programming-error exceptions (TypeError, ValueError) from bad data construction
  found: These would be raised at lines 64-66 (Point construction / field assignment), BEFORE the try/except block. They are NOT caught by the write exception handler. Requirement satisfied.
  implication: The broad `except Exception` at the write() call site is safe — it only runs if the actual I/O call fails.

## Resolution

root_cause: src/writer.py already had `except Exception as e` wrapping the write call — the exception WAS caught. The traceback was being printed because `exc_info=e` was passed to `_LOGGER.error()`. Python's logging `exc_info` parameter triggers full traceback formatting, which is what produced the noisy stack dump. `InfluxDBClient3.write()` only wraps `InfluxDBError` (HTTP-level); raw network exceptions (urllib3.exceptions.NewConnectionError, which inherits HTTPError → Exception, NOT InfluxDBError) pass through unwrapped — requiring the broad `except Exception` that was already present.
fix: Replaced the 5-line `_LOGGER.error(... exc_info=e)` block with a single `_LOGGER.warning("InfluxDB write failed: %s", e)` — no `exc_info`, no re-raise. Also updated the docstring from "logs ERROR" to "logs WARNING (no traceback)".
verification: All 18 unit tests in tests/test_writer.py pass. Test 13 updated to assert WARNING level and no exc_info. No other callers need changes — __main__.py._write_reading() already relies on write() not raising (comment: "writer.write() never raises").
files_changed: [src/writer.py, tests/test_writer.py]
