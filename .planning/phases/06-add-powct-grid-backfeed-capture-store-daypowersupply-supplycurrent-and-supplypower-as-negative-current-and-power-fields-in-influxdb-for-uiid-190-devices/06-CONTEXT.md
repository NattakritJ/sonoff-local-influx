# Phase 6: Add POWCT Grid Backfeed Capture - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

For UIID 190 devices with a CT clamp (SONOFF POWCT / `SN-ESP32D0-POWCT-01`, product model "POWCT"), extend the energy extractor to capture grid backfeed metrics — `supplyPower`, `supplyCurrent`, and `dayPowerSupply` — from LAN params and write them to InfluxDB using the existing `power` and `current` fields with **negative sign** to represent grid export, plus a new `energy_backfeed_today` field for the daily accumulator.

Scope is limited to:
1. `src/extractor.py` — extend `extract_energy()` and `EnergyReading` dataclass
2. `src/writer.py` — extend `write()` to handle the new `energy_backfeed_today` field
3. `tests/test_extractor.py` — new tests for UIID 190 backfeed logic
4. No changes to daemon wiring (`__main__.py`), config, Docker, or writer interface beyond the new field

</domain>

<decisions>
## Implementation Decisions

### Device Data Structure

- **D-01:** The POWCT device (UIID 190) sends `supplyPower`, `supplyCurrent`, and `dayPowerSupply` in the same `params` dict alongside the existing `power`, `current`, `voltage`, `dayKwh` fields (confirmed in `powct.json`)
- **D-02:** `power` and `supplyPower` are **mutually exclusive** — when the device is consuming from the grid, `supplyPower = 0`; when exporting to the grid, `power = 0`. Both can be 0 simultaneously (no power flow). They should never both be non-zero.
- **D-03:** Raw values use ×0.01 scaling, same as all other UIID 190 params. `supplyPower: 0` → `0.0 W`; `supplyCurrent: 0` → `0.0 A`; `dayPowerSupply: 8` → `0.08 kWh`.

### Sign Convention for InfluxDB

- **D-04:** Grid backfeed (export) is stored as **negative** values in the existing `power` and `current` InfluxDB fields:
  - `power = -supplyPower * 0.01` when `supplyPower > 0`
  - `current = -supplyCurrent * 0.01` when `supplyCurrent > 0`
  - This allows a single Grafana query on the `power` field to show both consumption (positive) and export (negative) in one time series
- **D-05:** No new `supply_power` or `supply_current` InfluxDB fields — the sign-encoded `power` and `current` fields carry both directions

### Merge Logic in extract_energy()

- **D-06:** The sign logic is implemented **inside `extract_energy()`** as a UIID 190-specific branch — no new function created. All existing callers and the daemon's `_on_update()` remain unchanged.
- **D-07:** Three-way logic for `power` / `current` fields on UIID 190:
  1. `power > 0, supplyPower = 0` → normal positive reading (consumption)
  2. `supplyPower > 0, power = 0` → negative reading (grid export): `power = -supplyPower * 0.01`, `current = -supplyCurrent * 0.01`
  3. `power = 0, supplyPower = 0` → **write zeros explicitly**: `power = 0.0`, `current = 0.0` — ensures InfluxDB time series is continuous even during zero-flow periods
- **D-08:** Voltage is always taken from the `voltage` param (not negated) — it represents the grid voltage regardless of direction
- **D-09:** Defensive case if both non-zero (shouldn't happen per device spec): write positive consumption values, ignore supply values

### EnergyReading Dataclass

- **D-10:** Add one new field to `EnergyReading`: `energy_backfeed_today: float | None`
  - Populated from `dayPowerSupply * 0.01` for UIID 190 (same scaling as `dayKwh`)
  - `None` for all other UIIDs (non-breaking addition)
  - Field name chosen over `energy_supply_today` for clarity — "backfeed" unambiguously means energy fed back to the grid

### InfluxDB Field: energy_backfeed_today

- **D-11:** `energy_backfeed_today` is written as a new InfluxDB field alongside `energy_today` — the writer includes it when non-None, exactly like `energy_today`
- **D-12:** No changes to the measurement name, tags, or other fields — the schema extension is additive

### Zero-Power Write Behavior

- **D-13:** When `power = 0` and `supplyPower = 0` (no power flow), write `power = 0.0` and `current = 0.0` explicitly — **do not return `None`**. This is an explicit exception to the existing "return None if no energy fields present" rule, because the both-zero case is a valid measured state (the device is on but idle), not an absence of data. Voltage and `energy_backfeed_today` are still written if present.

### Agent's Discretion

- Exact placement of the UIID 190 branch within `extract_energy()` — inline vs helper function is implementation detail
- Whether to add `energy_backfeed_today` before or after `energy_today` in the dataclass definition
- Whether `_HAS_DAY_SUPPLY_KWH` frozenset mirrors the existing `_HAS_DAY_KWH` pattern for the new field

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Device Data Sample
- `powct.json` (project root) — Real LAN params payload from a POWCT device (UIID 190). Contains `power`, `current`, `voltage`, `dayKwh`, `supplyPower`, `supplyCurrent`, `dayPowerSupply`, `monthPowerSupply`. **Read this first** — it is the ground truth for field names, raw value magnitudes, and scaling.

### Source to Extend
- `src/extractor.py` — `EnergyReading` dataclass (add `energy_backfeed_today` field) and `extract_energy()` (add UIID 190 backfeed branch). Read the full module including the existing UIID 32 auto-detect pattern and `_HAS_DAY_KWH` frozenset.
- `src/writer.py` — `InfluxWriter.write()` method: extend the `fields` dict construction to include `energy_backfeed_today` when non-None, following the same pattern as `energy_today` (lines 47–54).

### Tests to Extend
- `tests/test_extractor.py` — Existing UIID 190 tests (lines ~77–100, ~177–200) to understand the test structure and patterns before adding backfeed test cases.

### Requirements
- `.planning/REQUIREMENTS.md` §Energy Extraction — EXT-01 through EXT-05; backfeed capture is an extension to EXT-01 (power/current) and EXT-02 (energy accumulator) for UIID 190 specifically.

### Project Constraints
- `.planning/PROJECT.md` §Constraints — Energy metrics only; immediate write; log-and-continue.
- `.planning/STATE.md` §Accumulated Context — Scaling decisions, `EnergyReading` design, `None`-omission pattern in writer.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/extractor.py:40-49` — `EnergyReading` dataclass: add `energy_backfeed_today: float | None` as a new field after `energy_today`
- `src/extractor.py:56` — `_SCALE_001` frozenset already includes `190` — no scale change needed
- `src/extractor.py:69-70` — `_HAS_DAY_KWH` frozenset includes `190` — `dayKwh` extraction already handled; new `dayPowerSupply` extraction mirrors this pattern
- `src/writer.py:46-54` — `fields` dict construction: extend with `if reading.energy_backfeed_today is not None: fields["energy_backfeed_today"] = reading.energy_backfeed_today`

### Established Patterns
- UIID-specific branching: the existing `if uiid == 32:` block (auto-detect scale) is the established pattern for UIID-specific logic inside `extract_energy()`
- `_to_float()` helper: used for all raw param coercion — backfeed values go through same helper
- `round(..., 2)` for power/current/voltage; `round(..., 4)` for energy accumulators (dayKwh uses 4 dp — use same for dayPowerSupply)
- None-omission in writer: all fields use `if reading.X is not None: fields["X"] = reading.X` pattern

### Integration Points
- `src/__main__.py:_on_update()` — calls `extract_energy()` for single-channel UIIDs including 190. No changes needed to daemon wiring — the function signature and return type are unchanged.
- `src/writer.py:write()` — receives `EnergyReading`; extend field dict only. New `energy_backfeed_today` is additive — non-190 devices always pass `None`, writer skips it silently.

</code_context>

<specifics>
## Specific Ideas

- User confirmed: `power` and `supplyPower` are **mutually exclusive in practice** — device design guarantees one is always 0 when the other is non-zero
- User chose **`energy_backfeed_today`** (not `energy_supply_today`) — "supply" is ambiguous in this context; "backfeed" clearly means energy fed back to the grid
- Both-zero case (no power flow) should **write zeros explicitly** — not return `None` — to keep the InfluxDB time series continuous during idle periods
- Negative sign convention maps to a single Grafana `power` field query: positive = consumption, negative = export. No separate field queries needed for solar/grid scenarios.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-add-powct-grid-backfeed-capture-store-daypowersupply-supplycurrent-and-supplypower-as-negative-current-and-power-fields-in-influxdb-for-uiid-190-devices*
*Context gathered: 2026-04-04*
