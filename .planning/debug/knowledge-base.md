# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

## influxdb-connection-refused-not-handled — InfluxDB write prints full traceback instead of single warning on connection refused
- **Date:** 2026-04-04
- **Error patterns:** NewConnectionError, ConnectionRefusedError, traceback, InfluxDB, write, urllib3, connection refused, exc_info, writer.py
- **Root cause:** writer.py already caught network exceptions via `except Exception`, but passed `exc_info=e` to `_LOGGER.error()` which triggers Python logging's full traceback output. `InfluxDBClient3.write()` only wraps `InfluxDBError` (HTTP-level errors); raw urllib3 network exceptions (NewConnectionError → HTTPError → Exception, NOT InfluxDBError) pass through unwrapped and hit our handler which then dumps the stack.
- **Fix:** Replaced `_LOGGER.error(... exc_info=e)` with `_LOGGER.warning("InfluxDB write failed: %s", e)` — no exc_info, no re-raise. Also updated docstring and test 13 to assert WARNING level with no exc_info.
- **Files changed:** src/writer.py, tests/test_writer.py
---


