# Feature Landscape: Sonoff LAN → InfluxDB Daemon

**Domain:** IoT device-to-time-series bridge daemon
**Researched:** 2026-04-03
**Overall confidence:** HIGH (sourced directly from codebase + official InfluxDB 3 docs)

---

## Sonoff LAN Protocol: Energy Param Reference

This is the authoritative param-name map, extracted directly from `core/devices.py` and
`sensor.py` in the brownfield codebase. All names are exact JSON keys as they appear in
LAN/mDNS TXT payloads.

### Single-Channel Power Monitoring (POWR2 UIID 32, S40 UIID 182, S61STPF UIID 276, POWR3 UIID 190)

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `power` | W | ×1 (POWR2/S40), ×0.01 (POWR3/S61) | Active/instantaneous power |
| `voltage` | V | ×1 (POWR2/S40), ×0.01 (POWR3/S61) | Line voltage |
| `current` | A | ×1 (POWR2/S40), ×0.01 (POWR3/S61) | Line current |
| `dayKwh` | kWh | ×0.01 | Cumulative energy today |
| `weekKwh` | kWh | ×0.01 | Cumulative energy this week |
| `monthKwh` | kWh | ×0.01 | Cumulative energy this month |
| `yearKwh` | kWh | ×0.01 | Cumulative energy this year |

> **Scaling note:** POWR2 (UIID 32) and S40 (UIID 182) deliver `power`/`voltage`/`current`
> as already-scaled floats (no `×0.01` multiply). POWR3 (UIID 190), S61STPF (UIID 276),
> and DualR3 variants use raw integer cents requiring `×0.01`. This is reflected by
> `XSensor100 = spec(XSensor, multiply=0.01, round=2)` in `devices.py`.

### POW (Original, UIID 5)

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `power` | W | ×1 | Instantaneous power (LAN-available) |

> Historical energy for UIID 5 is cloud-only (`hundredDaysKwhData`). Not relevant for
> this daemon (LAN-only, cloud excluded).

### Multi-Channel Power Monitoring (DualR3 UIID 126, SPM-4Relay UIID 130)

Per-channel suffix `_00` = channel 1, `_01` = channel 2, `_02` = channel 3, `_03` = channel 4.

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `current_00` | A | ×0.01 | Channel 1 current |
| `current_01` | A | ×0.01 | Channel 2 current |
| `current_02` | A | ×0.01 | Channel 3 current |
| `current_03` | A | ×0.01 | Channel 4 current |
| `voltage_00` | V | ×0.01 | Channel 1 voltage |
| `voltage_01` | V | ×0.01 | Channel 2 voltage |
| `voltage_02` | V | ×0.01 | Channel 3 voltage |
| `voltage_03` | V | ×0.01 | Channel 4 voltage |
| `actPow_00` | W | ×0.01 | Channel 1 active power |
| `actPow_01` | W | ×0.01 | Channel 2 active power |
| `actPow_02` | W | ×0.01 | Channel 3 active power |
| `actPow_03` | W | ×0.01 | Channel 4 active power |

> `kwhHistories_00` / `kwhHistories_01` (DualR3) and `hoursKwhData` (POWR3) are
> cloud-polled hex-encoded history blobs. These require cloud connection + `XCloudEnergy`
> decode logic. They are **out of scope** for the LAN-only daemon unless the POWR3
> energy endpoint (POST `/zeroconf/getHoursKwh`) is explicitly supported.

### POWR3 POWCT Supply-Side Params (UIID 190, subset)

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `supplyCurrent` | A | ×0.01 | Supply-side current (POWCT variant only) |
| `supplyPower` | W | ×0.01 | Supply-side power (POWCT variant only) |
| `dayPowerSupply` | kWh | ×0.01 | Supply-side energy today |
| `monthPowerSupply` | kWh | ×0.01 | Supply-side energy this month |

### Third-Party / CK-BL602 Variants (UIID 226, 262)

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `phase_0_c` | A | ×1 | Phase current (UIID 226) |
| `phase_0_p` | W | ×1 | Phase power (UIID 226) |
| `phase_0_v` | V | ×1 | Phase voltage (UIID 226) |
| `totalPower` | kWh | ×1 | Total energy (UIID 226) |
| `power` | W | ×0.01 | Power (UIID 262) |
| `current` | A | ×0.01 | Current (UIID 262) |
| `voltage` | V | ×0.01 | Voltage (UIID 262) |

### Zigbee Power Socket (S60ZBTPF UIID 7032)

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `power` | W | ×0.01 | Instantaneous power |
| `current` | A | ×0.01 | Current |
| `voltage` | V | ×0.01 | Voltage |
| `dayKwh` | kWh | ×0.01 | Energy today |
| `monthKwh` | kWh | ×0.01 | Energy this month |

### Dimmer with Power Monitoring (UIID 277)

| Param Name (raw) | Unit | Scaling | Description |
|---|---|---|---|
| `power` | W | ×0.01 | Instantaneous power |
| `current` | A | ×0.01 | Current |
| `voltage` | V | ×0.01 | Voltage |

---

## UIID → Energy Capability Map

| UIID | Device | LAN Energy Params Available |
|---|---|---|
| 5 | Sonoff POW (1st gen) | `power` only (history cloud-only) |
| 32 | Sonoff POWR2 | `power`, `voltage`, `current` |
| 126 | Sonoff DualR3 | `actPow_00/01`, `current_00/01`, `voltage_00/01` |
| 130 | Sonoff SPM-4Relay | `actPow_00-03`, `current_00-03`, `voltage_00-03` |
| 182 | Sonoff S40 | `power`, `voltage`, `current` |
| 190 | Sonoff POWR3 / POWCT | `power`, `voltage`, `current`, `dayKwh`, `monthKwh`; POWCT also has supply-side params |
| 226 | CK-BL602-W102SW18 | `phase_0_c`, `phase_0_p`, `phase_0_v`, `totalPower` |
| 262 | CK-BL602-SWP1-02 | `power`, `current`, `voltage` |
| 276 | Sonoff S61STPF | `power`, `current`, `voltage`, `dayKwh`, `weekKwh`, `monthKwh`, `yearKwh` |
| 277 | MiniDim with power | `power`, `current`, `voltage` |
| 7032 | S60ZBTPF (Zigbee) | `power`, `current`, `voltage`, `dayKwh`, `monthKwh` |

> **Confidence: HIGH** — extracted directly from `custom_components/sonoff/core/devices.py`
> (brownfield codebase, version 3.11.1).

---

## Event Delivery: Push vs Poll

**Sonoff LAN is fully push-based (event-driven), not polled.**

- Devices broadcast state updates via **mDNS TXT record updates** (`_ewelink._tcp.local.`).
- The `zeroconf` `AsyncServiceBrowser` fires `_handler1` → `_handler2` → `_handler3`
  for every device state change.
- There is **no polling loop** for energy data in LAN mode. Each power reading arrives as
  a discrete mDNS event.
- **Update frequency** is device-controlled. Community observations:
  - POWR2/POWR3: typically every **~2–10 seconds** when load is changing; may slow to
    every ~30–60s under stable load. No confirmed fixed interval in firmware.
  - DualR3: similar 2–10s cadence.
  - Devices do **not** push updates when power is zero or the switch is off (silent).
- The daemon must **not poll** — it subscribes and reacts to events.

> **Note:** POWR3 supports an explicit LAN energy-history query via
> `POST /zeroconf/getHoursKwh` (used by `XCloudEnergyPOWR3.get_update()`). This is
> the only energy param that requires an active request rather than passive listening.
> `hoursKwhData` and periodic Wh totals are only reachable this way. For the v1 daemon
> this is **out of scope** (listed as anti-feature below).

---

## InfluxDB 3 Schema Recommendation

### Design Principles Applied
Source: [InfluxDB 3 Core Schema Design Docs](https://docs.influxdata.com/influxdb3/core/write-data/best-practices/schema-design/)

- Tags = metadata / identifying info (low cardinality); stored as strings.
- Fields = measured values (floats/ints).
- In InfluxDB 3, "measurement" = "table". Per-device tables prevent sparse schemas.
- InfluxDB 3 supports **infinite tag value cardinality** — device_id as tag is safe.
- Write all fields of one event in a single point to avoid sparse rows.

### Recommended Schema

```
table (measurement): sonoff_energy
    tag:   device_id    (string, e.g. "1000xxxxxx")   ← primary filter key
    tag:   device_name  (string, e.g. "kitchen_plug")  ← human label
    field: power        (float64, Watts, already-scaled)
    field: voltage      (float64, Volts, already-scaled)
    field: current      (float64, Amperes, already-scaled)
    field: energy_today (float64, kWh, already-scaled)   ← optional, device-dependent
    field: channel      (int64, 0-indexed)               ← multi-channel devices only
    timestamp: nanosecond-precision UTC (supplied by daemon at receive time)
```

**Line protocol example — single channel (POWR2):**
```
sonoff_energy,device_id=1000aabbcc,device_name=kitchen_plug power=1850.5,voltage=230.1,current=8.04 1743676800000000000
```

**Line protocol example — multi-channel (DualR3, channel 0):**
```
sonoff_energy,device_id=1000ddeeff,device_name=dual_switch,channel=0 power=420.0,voltage=229.8,current=1.83 1743676800000000000
```

**Energy accumulator (POWR3 dayKwh, optional):**
```
sonoff_energy,device_id=1000gghhii,device_name=garage_pow power=3200.0,voltage=230.0,current=13.9,energy_today=12.45 1743676800000000000
```

### Schema Design Decisions

| Decision | Rationale |
|---|---|
| Single table `sonoff_energy` | All Sonoff energy devices are homogenous — same field set. Avoids per-device table proliferation. Aligns with InfluxDB 3 "homogenous table" best practice. |
| `device_id` as tag, not field | Used in WHERE clauses constantly. Tags are indexed. InfluxDB 3 infinite cardinality means tag use is safe regardless of device count. |
| `device_name` as tag | Human-readable label for Grafana. Supplied from config, never changes. Low cardinality. |
| `channel` as integer tag | Multi-channel devices (DualR3, SPM-4Relay) need channel disambiguation without creating per-channel tables. Single-channel devices omit this tag (null allowed). |
| Scaling at daemon write time | Raw params scaled to physical units before write (×0.01 where needed). InfluxDB stores the human value — no Flux/SQL math at query time. |
| Timestamp from daemon receive time | Devices do not include an authoritative timestamp in LAN payloads. Using `time.time()` at event receipt is the standard approach. Nanosecond precision (`ns`) is the InfluxDB 3 default. |
| Omit non-numeric energy fields | `kwhHistories_*` (hex blob) and `hundredDaysKwhData` require cloud polling + custom decoder. Excluded from daemon scope. |

---

## Table Stakes

Features that must exist or the daemon is useless.

| Feature | Why Required | Complexity | Notes |
|---|---|---|---|
| mDNS device discovery via zeroconf | Devices announce themselves; no other discovery path | Low | Already implemented in `local.py`; just needs to be unwired from HA |
| AES-128-CBC decryption of encrypted payloads | All non-DIY devices encrypt their LAN data | Low | Implemented in `local.py`; key = `md5(devicekey)` |
| Plain JSON payload support (DIY devices) | Older/DIY devices send unencrypted JSON | Low | Already handled |
| Energy param extraction from device params | Core value delivery | Medium | Must handle per-UIID scaling differences; defer to param map above |
| Write to InfluxDB 3 using `influxdb3-python` | Destination of all data | Low | `InfluxDBClient3.write()` with `Point` objects; synchronous mode |
| Per-device measurement/table routing | Data must land in queryable schema | Low | Single `sonoff_energy` table + `device_id` tag recommended |
| Immediate write per event (no buffering) | Low-latency design requirement; project constraint | Low | Call `client.write()` directly in the event handler; no queue |
| InfluxDB write failure → log and continue | Daemon must not crash on transient InfluxDB unavailability | Low | `try/except InfluxDBError` around each write |
| Graceful shutdown (SIGTERM/SIGINT) | Required for Docker container stop | Low | `asyncio` signal handler; cancel zeroconf browser |
| Docker env var configuration | Only deployment target; no config files | Low | `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_DATABASE`, `DEVICES` |
| Explicit device list from config | Project constraint; no zero-config auto-discovery | Low | Map device IDs/IPs + devicekeys + names; reject unknown devices |
| Structured logging | Operational visibility | Low | `logging` with device ID prefix on every write and error |
| Support both encrypted and plain-JSON devices | Device population is mixed | Low | Auto-detect by presence of `encrypt` field in mDNS TXT |

---

## Differentiators

Nice-to-have features that add value without being required for basic function.

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| `device_name` tag writeable from config | Human-readable labels in Grafana without knowing device IDs | Low | Env var map `DEVICE_NAMES=1000aabbcc=kitchen_plug,...` |
| Per-device `multiply` override in config | Users with odd firmware that returns different scaling | Low | Edge case; most devices match the UIID map |
| Startup connectivity check (InfluxDB ping) | Fail fast and log clearly if InfluxDB unreachable at boot | Low | `client.query("SELECT 1")` at init |
| Write counter metrics in log | Operational: "10 events written in last 60s" heartbeat log line | Low | Simple counter in memory, log periodically |
| `channel` tag on multi-channel writes | Allows per-channel queries on DualR3/SPM-4Relay without table proliferation | Low | Emit separate Point per channel; already required for correct schema |
| POWR3 energy history poll (LAN) | Captures kWh accumulator from POWR3's `/zeroconf/getHoursKwh` endpoint | High | Requires separate poll loop + `XCloudEnergyPOWR3.decode_energy()` hex parser; only device that supports LAN energy polling |

---

## Anti-Features

Explicitly excluded from scope with rationale.

| Anti-Feature | Why Excluded | What to Do Instead |
|---|---|---|
| eWeLink cloud connection | Adds auth complexity, cloud dependency, no SLA | LAN-only; all energy params except history blobs are LAN-available |
| `hundredDaysKwhData` / `kwhHistories_*` history blobs | Cloud-only fetch; requires complex hex decoder; no LAN equivalent for POWR2/DualR3 | Use `dayKwh`/`monthKwh` (available from device push) for accumulator data |
| Auto-discovery of unknown devices | Security risk; unknown devices shouldn't silently write to DB | Explicit config list; log warning for undiscovered devices |
| Home Assistant entity layer | HA platform code is the entire point of removal | All HA imports, `XEntity`, config entries, platform modules stripped |
| Batched writes / write buffering | Adds complexity; per-event write latency is acceptable at IoT scale | Immediate synchronous write per event |
| Non-energy data (switch state, temp, humidity) | Out of scope per PROJECT.md; increases schema complexity | Can be added in a later milestone |
| InfluxDB instance provisioning | Daemon is a writer only; not an admin tool | Target a pre-provisioned InfluxDB 3 Core instance |
| Camera PTZ control | HA-specific, UDP broadcast, irrelevant to energy logging | Remove `camera.py` entirely |
| Multi-account / multi-registry support | Single network segment; one daemon per LAN | N/A |

---

## Feature Dependencies

```
mDNS discovery → AES decrypt → param extraction → InfluxDB write
     ↑                ↑                ↑
  zeroconf        devicekey       UIID scaling
  config list      from env        map (devices.py)
```

- InfluxDB write depends on param extraction (can't write unknown params).
- Param extraction depends on UIID scaling map (wrong scaling = wrong values in DB).
- AES decrypt depends on `devicekey` being in config for each encrypted device.
- Graceful shutdown depends on asyncio event loop being the single thread of control.

---

## MVP Feature Set

**Implement in priority order:**

1. **mDNS listener + decryption** — reuse `XRegistryLocal` stripped of HA references
2. **Param extractor** — map raw params to physical values using UIID scaling table
3. **InfluxDB writer** — `InfluxDBClient3.write()` synchronous mode, `sonoff_energy` table
4. **Config loader** — env vars for InfluxDB connection + per-device `id:devicekey:name`
5. **Error handling** — log-and-continue on write failure; graceful SIGTERM shutdown
6. **Docker packaging** — `Dockerfile` + `docker-compose.yml` with env var documentation

**Defer to later milestone:**

- `device_name` tag from config (useful but not blocking)
- POWR3 LAN energy history poll (high complexity, single device model)
- Write counter heartbeat logging

---

## Known Quirks: Sonoff LAN Energy Reporting

> **Confidence: MEDIUM** — derived from codebase evidence + community issue tracker
> patterns visible in inline comments. No official Sonoff firmware docs available.

| Quirk | Impact | Evidence |
|---|---|---|
| POWR2 delivers `power`/`voltage`/`current` as pre-scaled floats; POWR3 delivers raw integer-cents needing `×0.01` | Incorrect scaling produces wrong values. Must branch on UIID. | `devices.py`: UIID 32 uses `spec(XSensor, param="power")` vs UIID 190 uses `spec(XSensor100, param="power")` where `XSensor100` has `multiply=0.01` |
| Devices broadcast silently when power is zero or switch is off | Gaps in time-series — no "zero watts" events. Grafana will show last-known-value or null depending on visualization. | No explicit "zero" event in protocol; devices simply stop emitting TXT updates |
| `power` field can arrive as a **string** `"0.00"` instead of float on some firmware | Type coercion required; fail silently if non-numeric | `sensor.py:XSensor.set_state`: `value = float(value)` in try/except |
| mDNS TXT record length limits: data split across `data1`/`data2`/`data3`/`data4` keys | Must concatenate all `data[1-4]` keys before JSON-parsing | `local.py:_handler3`: `raw = "".join([data[f"data{i}"] for i in range(1, 5)])` |
| Encrypted payloads: `devicekey` must be configured manually (not discoverable over LAN) | If `devicekey` is missing for a non-DIY device, decryption fails silently → no data | `local.py:decrypt_msg` returns `{}` on failure |
| DualR3 / SPM-4Relay: energy history (`kwhHistories_*`) is cloud-only despite device being LAN-capable for real-time | Cannot get cumulative kWh from these devices without cloud | `XCloudEnergyDualR3.can_update()` checks `self.ewelink.cloud.online` |
| POWR3 supports LAN energy poll via `POST /zeroconf/getHoursKwh` | Only device that allows periodic LAN kWh accumulator fetch | `XCloudEnergyPOWR3.get_update()` uses `ewelink.send()` not `send_cloud()` |
| Zeroconf lib returns devices multiple times on reconnect | Daemon must tolerate duplicate events; writes are idempotent (same timestamp = InfluxDB upserts row) | LAN discovery fires `ServiceStateChange.Added` and `ServiceStateChange.Updated` |
| Some devices return `text/html` instead of JSON on `getState` command | Must handle non-JSON responses without crashing | `local.py:send`: `if r.headers.get(CONTENT_TYPE) == "text/html": return "online"` |

---

## Sources

- **PRIMARY (HIGH confidence):** `custom_components/sonoff/core/devices.py` v3.11.1 — direct param extraction
- **PRIMARY (HIGH confidence):** `custom_components/sonoff/sensor.py` v3.11.1 — units, scaling, decode logic
- **PRIMARY (HIGH confidence):** `custom_components/sonoff/core/ewelink/local.py` v3.11.1 — LAN transport mechanics
- **OFFICIAL (HIGH confidence):** [InfluxDB 3 Core Schema Design](https://docs.influxdata.com/influxdb3/core/write-data/best-practices/schema-design/) — tags vs fields, homogenous tables
- **OFFICIAL (HIGH confidence):** [influxdb3-python Python client library](https://docs.influxdata.com/influxdb3/core/reference/client-libraries/v3/python/) — `InfluxDBClient3.write()`, `Point` class
- **OFFICIAL (HIGH confidence):** [CoolKit eWeLink API UIID Protocol](https://github.com/CoolKit-Technologies/eWeLink-API/blob/main/en/UIIDProtocol.md) — referenced inline in `devices.py:188`
