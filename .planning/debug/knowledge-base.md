# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## docker-no-data-silent — Docker daemon silent after startup on macOS (mDNS multicast not received)
- **Date:** 2026-04-03
- **Error patterns:** silent, no data, no logs, docker, mDNS, zeroconf, network_mode host, multicast, macOS, ready
- **Root cause:** macOS Docker Desktop runs containers inside a Linux VM. `network_mode: host` attaches to the VM's virtual NIC, not the macOS host's physical LAN. mDNS multicast packets (224.0.0.251:5353) from Sonoff devices on the LAN never enter the VM — `AsyncServiceBrowser` starts without error but receives zero events, so no writes ever occur.
- **Fix:** No code changes needed. Added comment to docker-compose.yml and explicit macOS/Windows warning to README Network requirements section directing users to the local run path. Also fixed all README `SONOFF_DEVICES` examples that were missing the required `uiid` field.
- **Files changed:** docker-compose.yml, README.md
---

