# Phase 6: Add POWCT Grid Backfeed Capture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 06-add-powct-grid-backfeed-capture-store-daypowersupply-supplycurrent-and-supplypower-as-negative-current-and-power-fields-in-influxdb-for-uiid-190-devices
**Areas discussed:** Device data structure (from powct.json), Negative value representation, Merge logic, dayPowerSupply mapping, Extraction function design, EnergyReading dataclass, Both-zero edge case, Field naming

---

## Pre-discussion: Device Data

The user directed the agent to read `powct.json` before asking questions. Key finding: the POWCT device sends `power`, `current`, `voltage`, `supplyPower`, `supplyCurrent`, `dayKwh`, and `dayPowerSupply` all in the same params dict. `power` and `supplyPower` are mutually exclusive (confirmed by user).

---

## Negative Value Representation

| Option | Description | Selected |
|--------|-------------|----------|
| Two rows, same fields | Two EnergyReadings per update — one positive, one negative | |
| New fields, one row | Add supply_power/supply_current as positive fields | |
| Combined row, distinct fields | One row with both power and supply_power | |
| User answer | Mutually exclusive → merge into same field with sign | ✓ |

**User's choice:** Merge `supplyPower` into `power` field with negative sign. Since both can't have value simultaneously, no need for two rows or separate fields. If `supplyPower` has value and `power` is 0, store as negative.

---

## Merge Logic

| Option | Description | Selected |
|--------|-------------|----------|
| Exclusive merge — one row | if supplyPower > 0 and power == 0: write negative. Otherwise positive. | ✓ |
| Non-zero preference | Prefer whichever is non-zero | |
| Always two rows | Always write separate rows | |

**User's choice:** Exclusive merge — one row. Additionally: handle both-zero case (both power and supplyPower can be 0 simultaneously — no power flow).

---

## dayPowerSupply Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| New energy_supply_today field | Add separate accumulator field for grid export kWh | ✓ |
| Negative energy_today | Use signed energy_today for both directions | |
| Omit dayPowerSupply | Only capture real-time, not daily accumulator | |

**User's choice:** New dedicated field. (Field later renamed to `energy_backfeed_today` — see Field Naming section.)

---

## Extraction Function Design

| Option | Description | Selected |
|--------|-------------|----------|
| Extend extract_energy() | Add UIID 190 branch inside existing function | ✓ |
| New extract_energy_backfeed() | Separate function; daemon calls both | |
| UIID 190-specific function | Full replacement for UIID 190 | |

**User's choice:** Extend `extract_energy()` — keep all UIID 190 logic in one place, no daemon changes needed.

---

## EnergyReading Dataclass

| Option | Description | Selected |
|--------|-------------|----------|
| Add field to dataclass | Add energy_supply_today (→ energy_backfeed_today) field | ✓ |
| Separate kwarg to writer | Pass as extra kwarg, keep dataclass unchanged | |

**User's choice:** Add field to dataclass — consistent with existing pattern (`energy_today`).

---

## Both-Zero Edge Case

| Option | Description | Selected |
|--------|-------------|----------|
| Return None — skip write | No row when power=0 and supplyPower=0 | |
| Write zeros explicitly | Write power=0.0, current=0.0 for continuous time series | ✓ |
| Partial write — voltage only | Write voltage even when power is zero | |

**User's choice:** Write zeros explicitly — continuous time series is preferred, zero-flow is a valid measured state.

---

## Field Naming

**User's choice (free text):** Use `energy_backfeed_today` instead of `energy_supply_today`. "Supply" is ambiguous — "backfeed" clearly means energy fed back to the grid.

---

## Agent's Discretion

- Exact placement of the UIID 190 branch within `extract_energy()`
- Whether to add a `_HAS_DAY_SUPPLY_KWH` frozenset mirroring `_HAS_DAY_KWH`
- Field ordering in `EnergyReading` dataclass

## Deferred Ideas

None — discussion stayed within phase scope.
