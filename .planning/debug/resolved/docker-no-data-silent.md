---
status: resolved
trigger: "Daemon runs correctly locally but Docker run is completely silent after startup — no data written, no further logs, no errors."
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED — macOS Docker Desktop does not forward mDNS multicast UDP into containers even with network_mode:host. The daemon starts and logs "ready" but zeroconf receives zero events.
test: Verified by reading docker-compose.yml (network_mode:host), Dockerfile (Linux container), ewelink/local.py (AsyncServiceBrowser with no interface binding), and cross-referencing known Docker Desktop macOS multicast limitation.
expecting: Fix applied — awaiting human verification of local run workaround (or Linux Docker confirmation).
next_action: Human verifies either (a) local run works on macOS, or (b) Docker on Linux receives events.

## Symptoms

expected: Daemon starts, logs 'ready', receives mDNS/LAN telemetry events from Sonoff device, writes energy readings to InfluxDB.
actual: Container starts up, logs startup messages ('InfluxDB connected', 'SonoffLAN-InfluxDB ready'), then produces no further output and writes nothing to InfluxDB.
errors: No errors logged — just silence after startup.
reproduction: docker compose up --build using the project's docker-compose.yml on macOS.
started: First Docker run attempt; local run works correctly with same .env config.

## Eliminated

- hypothesis: .env file not being loaded by docker-compose
  evidence: docker-compose.yml has env_file: .env; daemon logs "ready" with correct device count, so parse_config() succeeded — env vars are definitely being loaded.
  timestamp: 2026-04-03T00:02:00Z

- hypothesis: Python module path / PYTHONPATH differences
  evidence: CMD is "python -u src/__main__.py" from WORKDIR /app. Python adds src/ to sys.path automatically. All imports resolve correctly (daemon starts without ImportError).
  timestamp: 2026-04-03T00:02:00Z

- hypothesis: Missing system dependencies inside container
  evidence: Dockerfile installs libssl-dev; pip installs all requirements; daemon starts without error — cryptography and zeroconf are working fine.
  timestamp: 2026-04-03T00:02:00Z

- hypothesis: asyncio event loop differences / Python version mismatch
  evidence: Dockerfile uses python:3.12-slim-bookworm. Daemon starts and heartbeat task is scheduled. No asyncio errors. Python version is fine.
  timestamp: 2026-04-03T00:02:00Z

## Evidence

- timestamp: 2026-04-03T00:01:00Z
  checked: docker-compose.yml line 6
  found: network_mode: host is set
  implication: On Linux this would work; on macOS Docker Desktop, host networking does NOT give the container access to the macOS host network stack. Multicast UDP never reaches the container.

- timestamp: 2026-04-03T00:01:01Z
  checked: Dockerfile CMD + WORKDIR
  found: WORKDIR /app, CMD ["python", "-u", "src/__main__.py"]. Non-root user (sonoff). No PYTHONPATH set.
  implication: Module imports use relative paths (from config import ...) — this works because CMD is run from /app which contains src/. But the src/ directory is not on sys.path; Python resolves imports relative to the script directory (src/), which is fine.

- timestamp: 2026-04-03T00:01:02Z
  checked: src/__main__.py — AsyncZeroconf init and registry.start()
  found: azc = AsyncZeroconf(); registry.start(azc.zeroconf) — no interface or address binding parameters passed to AsyncZeroconf.
  implication: On macOS Docker Desktop, even with network_mode:host, the container's network interface is a virtual one (inside the Linux VM that Docker Desktop runs). mDNS multicast never arrives because macOS does NOT forward multicast packets into the Linux VM. The zeroconf browser starts successfully (no error), but receives zero events → complete silence.

- timestamp: 2026-04-03T00:01:03Z
  checked: macOS Docker Desktop networking behavior
  found: Docker Desktop on macOS runs containers inside a Linux VM (HyperKit/QEMU). network_mode:host binds the container to the VM's host network, NOT the macOS host network. mDNS multicast (224.0.0.251:5353) is sent on the macOS LAN interface — this never crosses into the VM's network stack. This is a documented Docker Desktop limitation; host networking on macOS is effectively a no-op for multicast.
  implication: ROOT CAUSE CONFIRMED. The zeroconf AsyncServiceBrowser starts without errors (socket opens fine inside the VM), but zero mDNS packets arrive → _handler1 is never called → no SIGNAL_UPDATE dispatched → no writes. Perfectly explains the symptoms: startup logs appear, then complete silence.

- timestamp: 2026-04-03T00:01:04Z
  checked: env_file loading — docker-compose.yml env_file: .env
  found: env_file: .env is correctly configured and the .env file exists at project root. SONOFF_DEVICES parsing would succeed (daemon starts and logs "ready" with correct device count). Config parsing is NOT the issue.
  implication: Environment variables work correctly — this is not the cause.

- timestamp: 2026-04-03T00:01:05Z
  checked: PYTHONPATH / module resolution
  found: CMD runs python -u src/__main__.py from /app. Python adds src/ to sys.path (directory of the script). All imports in __main__.py are relative to src/ (from config import ..., from ewelink import ...). This works identically to local run.
  implication: Module path is fine — not the cause.

- timestamp: 2026-04-03T00:03:00Z
  checked: README.md SONOFF_DEVICES examples
  found: All README examples were missing the required 'uiid' field — they would cause an immediate sys.exit(1) with error "is missing the required 'uiid' field" (from config.py parse_config validation). This is a separate documentation bug.
  implication: Secondary bug fixed alongside main fix — all README examples now include uiid.

## Resolution

root_cause: macOS Docker Desktop does not support multicast UDP forwarding for mDNS/zeroconf. network_mode:host in docker-compose.yml binds the container to the Docker Desktop Linux VM's virtual network interface, not the macOS host's physical LAN interface. mDNS discovery packets (multicast 224.0.0.251:5353) sent by Sonoff devices on the LAN never reach the container. The zeroconf AsyncServiceBrowser starts without error but receives zero events, so _handler1 is never called, SIGNAL_UPDATE is never dispatched, and nothing is ever written to InfluxDB.
fix: |
  1. docker-compose.yml: Added prominent comment explaining the macOS/Windows limitation — network_mode:host only works on Linux.
  2. README.md Network requirements section: Added explicit macOS/Windows warning with callout block directing users to the local run path.
  3. README.md SONOFF_DEVICES examples: Added missing required 'uiid' field to all three examples (single device, multiple devices, DIY device) — these were all broken without it.
  4. README.md SONOFF_DEVICES object fields table: Added missing 'uiid' row (required field).
  The daemon code itself is correct — no code changes needed. The issue is purely a platform/networking constraint that needs documentation.
verification: Confirmed by user — local run (python src/__main__.py) works correctly on macOS. Docker silent issue is explained and understood. Workaround verified working.
files_changed:
  - docker-compose.yml
  - README.md

