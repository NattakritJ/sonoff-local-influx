---
type: quick
id: 260403-r2z
title: "Commit: remove legacy HA files, add CI/SonarCloud config"
completed: "2026-04-03"
duration: "2 min"
tasks: 2
files_modified: 62
commits:
  - hash: "69178ae"
    message: "chore: remove legacy HA integration files and simplify test config"
  - hash: "ae7acb7"
    message: "ci: add GitHub Actions workflows and SonarCloud config"
---

# Quick Task 260403-r2z: Commit — Remove Legacy HA Files, Add CI/SonarCloud Config Summary

**One-liner:** Atomic two-commit cleanup removing all HA custom_components/tests (60 files, 11850 deletions) and adding GitHub Actions CI pipeline + SonarCloud config as daemon migration milestone commit record.

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Remove legacy HA integration files and simplify test config | `69178ae` | 60 files deleted/modified |
| 2 | Add GitHub Actions workflows and SonarCloud config | `ae7acb7` | 2 files added |

---

## What Was Done

### Task 1 — Legacy HA Removal (`69178ae`)

Staged and committed the deletion of all Home Assistant integration artifacts that became obsolete after the daemon migration:

- **`custom_components/sonoff/**`** — 52 files deleted (all HA platform modules, core/, ewelink/, translations/)
- **`hacs.json`** — HACS integration config, no longer needed
- **`README.md`** — Old HA-centric README (deleted; daemon README written in Phase 4)
- **`tests/`** — 8 HA-specific test files deleted (`test_entity.py`, `test_climate.py`, `test_energy.py`, `test_misc.py`, `test_backward.py`, `conftest.py`, `pytest.ini`, `__init__.py`)
- **`conftest.py`** — Updated: HA stub imports removed (daemon tests need no HA)
- **`pytest.ini`** — Updated: HA-specific pytest options stripped

60 files changed, 11850 deletions.

### Task 2 — CI/SonarCloud Config (`ae7acb7`)

Staged and committed the new CI tooling files:

- **`.github/workflows/build.yml`** — GitHub Actions CI pipeline (build, test, push)
- **`sonar-project.properties`** — SonarCloud static analysis integration config

2 files added, 27 insertions.

---

## Exclusions (Intentionally Not Committed)

| File | Reason |
|------|--------|
| `powct.json` | Device credentials — secret, never commit |
| `sonoff_data.json` | Runtime cache — transient state, not source |
| `.DS_Store` | macOS finder metadata — noise |
| `.planning/config.json` | Internal GSD planner state — not project source |

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check

### Files exist:
- `.github/workflows/build.yml` — created via commit `ae7acb7`
- `sonar-project.properties` — created via commit `ae7acb7`

### Commits exist:
- `69178ae` — confirmed in `git log --oneline -3`
- `ae7acb7` — confirmed in `git log --oneline -3` (HEAD)

### No secrets in commits:
- `git log --all --full-history -- powct.json sonoff_data.json .DS_Store` returns only the initial project state commit (`f843999`) — neither new commit touches these files ✅

### git status clean:
- Only `powct.json`, `sonoff_data.json`, `.DS_Store`, `.planning/config.json`, `.planning/quick/` remain — all untracked or excluded ✅

## Self-Check: PASSED
