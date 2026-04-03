# Codebase Concerns

**Analysis Date:** 2026-04-03

---

## Tech Debt

**Near-duplicate `send_bulk` / `send_bulk_configure` functions:**
- Issue: Two nearly identical batching functions exist; the author acknowledged this with a TODO comment
- Files: `custom_components/sonoff/core/ewelink/__init__.py:172`
- Impact: Changes to batching logic must be applied twice; risk of divergence
- Fix approach: Extract shared logic into a private `_send_bulk_impl(method, ...)` helper and have both call it

**Timing-based batching via `asyncio.sleep(0.1)`:**
- Issue: `send_bulk` uses a 100ms sleep as a coalescing window — fragile and environment-dependent
- Files: `custom_components/sonoff/core/ewelink/__init__.py` (`send_bulk`)
- Impact: On slow systems the window may expire before all updates arrive; on fast systems it's wasted latency
- Fix approach: Use a proper debounce/coalesce pattern with a `asyncio.Event` or `asyncio.Queue`

**`devices.py` flat mapping with no abstraction:**
- Issue: 891-line file of repetitive `spec()` calls with no grouping or abstraction for common power-monitoring patterns
- Files: `custom_components/sonoff/core/devices.py`
- Impact: Adding a new device type requires copy-pasting large blocks; easy to miss a capability
- Fix approach: Define named spec presets (e.g., `POWER_STRIP_SPEC`, `ENERGY_METER_SPEC`) and reference them

**`spec()` uses `type()` for dynamic class creation:**
- Issue: `spec()` in `devices.py` dynamically creates classes via `type()` — this confuses IDEs, mypy, and static analysis
- Files: `custom_components/sonoff/core/devices.py`
- Impact: No autocomplete or type checking on dynamically created entity classes; hard to refactor
- Fix approach: Use explicit class definitions or dataclass-based descriptors

**`unwrap_cached_properties()` workaround:**
- Issue: A helper function exists specifically to work around HA's `CachedProperties` metaclass interfering with `spec()`'s dynamic `type()` call
- Files: `custom_components/sonoff/core/xutils.py` (`unwrap_cached_properties`), `custom_components/sonoff/core/devices.py`
- Impact: Any HA version that changes its metaclass behavior could silently break all entity registration
- Fix approach: Migrate away from `type()`-based entity creation

**`REGIONS` as a 200+ line inline dict:**
- Issue: The region-to-endpoint mapping is a large static dict inline in `cloud.py`
- Files: `custom_components/sonoff/core/ewelink/cloud.py`
- Impact: Clutters the file; harder to update independently; not shareable
- Fix approach: Move to `core/const.py` or a dedicated `core/regions.py`

**`source_hash()` stores result in `__doc__`:**
- Issue: `xutils.py`'s `source_hash()` stores computed hash in the module's `__doc__` attribute as a caching mechanism — semantically wrong
- Files: `custom_components/sonoff/core/xutils.py`
- Impact: Fragile caching; `__doc__` is not intended for runtime data; tools that read docstrings will see the hash
- Fix approach: Use a module-level `_cache` variable or `functools.lru_cache`

**Incomplete camera ping/pong handling:**
- Issue: `CMD_PONG` is defined but the TODO comment indicates the pong response is never actually sent
- Files: `custom_components/sonoff/core/ewelink/camera.py:116`
- Impact: Camera WebSocket connections may time out prematurely if the server expects a pong
- Fix approach: Implement the pong send in the `CMD_PING` handler branch

**Near-duplicate sensor correction classes:**
- Issue: `XTempCorrection` and `XHumCorrection` in `sensor.py` have nearly identical `set_state()` implementations
- Files: `custom_components/sonoff/sensor.py`
- Impact: Bug fixes must be applied to both; they will drift over time
- Fix approach: Extract a shared `XCorrection` base class parameterised by attribute name

---

## Security Considerations

**Hardcoded app ID in `cloud.py`:**
- Risk: `APP = ["R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv"]` is a hardcoded credential — if revoked, all users break silently
- Files: `custom_components/sonoff/core/ewelink/cloud.py:249`
- Current mitigation: None
- Recommendations: Document the app ID as a known constant; add a runtime check and clear error if auth fails due to invalid app

**Obfuscated secret-key derivation (`sign()`):**
- Risk: The `sign()` function uses base64-encoded obfuscation rather than a real secret store; the signing key is effectively embedded in source code
- Files: `custom_components/sonoff/core/ewelink/cloud.py:289–297`
- Current mitigation: The obfuscation is light security-through-obscurity
- Recommendations: Accept this as a limitation of reverse-engineered APIs; document it explicitly; don't add more sensitive material nearby

**`APP` list is module-level mutable — multi-reload accumulation:**
- Risk: `APP.append(conf[CONF_APPSECRET])` in `__init__.py:116` appends on every HA config reload; after N reloads `APP` contains N copies of the secret
- Files: `custom_components/sonoff/__init__.py:116`, `custom_components/sonoff/core/ewelink/cloud.py`
- Current mitigation: None — the duplicate entries are harmless today but indicate the pattern is unsafe
- Recommendations: Guard with `if conf[CONF_APPSECRET] not in APP:` before appending, or reset `APP` to its default each setup

**MD5 used for encryption key derivation:**
- Risk: `hashlib.md5` is used to derive the AES key from the device's `devicekey` — MD5 is a weak hash
- Files: `custom_components/sonoff/core/ewelink/local.py:29, 49`
- Current mitigation: This mirrors the official eWeLink LAN protocol — it is a protocol constraint, not a free choice
- Recommendations: Document that this is a protocol requirement and cannot be changed without firmware changes; ensure the concern is not mistaken for a fixable code issue

**Hardcoded dummy `selfApikey: "123"` in local protocol:**
- Risk: The local LAN protocol sends `"selfApikey": "123"` as a placeholder
- Files: `custom_components/sonoff/core/ewelink/local.py:169`
- Current mitigation: The device appears not to validate this field
- Recommendations: Document as a protocol quirk; no action required unless device firmware starts enforcing it

---

## Performance Bottlenecks

**Camera runs a blocking thread outside the event loop:**
- Problem: `XCameras` subclasses `threading.Thread` and calls `socket.recvfrom()` in a blocking loop
- Files: `custom_components/sonoff/core/ewelink/camera.py`
- Cause: Camera discovery uses a UDP broadcast protocol that predates asyncio support in this codebase
- Improvement path: Migrate to `asyncio.DatagramProtocol` / `loop.create_datagram_endpoint()`; eliminates the thread entirely

**`run_forever()` polls ALL devices every 5 seconds:**
- Problem: The keep-alive / status refresh loop iterates over every registered device regardless of whether it is local/cloud/offline
- Files: `custom_components/sonoff/core/ewelink/__init__.py` (`run_forever`)
- Cause: No per-device state machine to skip idle or unreachable devices
- Improvement path: Track per-device last-seen timestamp; skip devices that are definitively cloud-only during LAN poll cycle

**Synchronous filesystem walk in `source_hash()`:**
- Problem: `source_hash()` walks the filesystem to hash source files — slow on first call
- Files: `custom_components/sonoff/core/xutils.py`
- Cause: Called via `async_add_executor_job` in diagnostics (correct), but still adds latency to diagnostics generation
- Improvement path: Compute once at module load time and cache in a module-level variable

---

## Fragile Areas

**`UNIQUE_DEVICES` global dict not cleared on reload:**
- Files: `custom_components/sonoff/__init__.py:101`
- Why fragile: `UNIQUE_DEVICES = {}` is set at module level; HA reloads the integration without re-importing the module, so stale device entries accumulate
- Safe modification: Clear the dict explicitly in `async_unload_entry` or use HA's `hass.data` namespace which is properly scoped per config entry
- Test coverage: Not tested

**`XRegistry.config` is a class attribute shared across all instances:**
- Files: `custom_components/sonoff/core/ewelink/__init__.py`
- Why fragile: If two config entries exist (e.g., two accounts), the second entry's `config` overwrites the first's
- Safe modification: Move `config` to an instance attribute set in `__init__`
- Test coverage: No multi-instance tests exist

**`XRegistryBase._sequence` / `_sequence_lock` are class-level:**
- Files: `custom_components/sonoff/core/ewelink/base.py`
- Why fragile: Sequence numbers are shared across all registry instances — two instances will interleave sequence numbers, potentially confusing device acknowledgement
- Safe modification: Move to instance attributes
- Test coverage: Not tested

**Camera `wait()` has no timeout:**
- Files: `custom_components/sonoff/core/ewelink/camera.py:64–67`
- Why fragile: If the camera device never responds, `wait()` blocks the thread forever — no watchdog
- Safe modification: Replace `wait()` with `wait(timeout=N)` and handle the `False` return
- Test coverage: No camera tests exist

**LAN send uses recursion for `ECONNRESET` retry:**
- Files: `custom_components/sonoff/core/ewelink/local.py` (`send()`)
- Why fragile: Retries up to 10 times recursively — on a flaky network this risks deep call stacks and `RecursionError`
- Safe modification: Convert to an iterative loop with `for attempt in range(10):`
- Test coverage: Not tested

**Commented-out `cloud_connected` task block in `__init__.py`:**
- Files: `custom_components/sonoff/__init__.py`
- Why fragile: Dead code that was once active; unclear if it represents a feature removed intentionally or a work-in-progress
- Safe modification: Remove entirely with a git commit message explaining the intent, or re-enable with a TODO explaining why it's disabled
- Test coverage: N/A

---

## Known Bugs

**`asyncio.get_event_loop()` deprecated since Python 3.10:**
- Symptoms: `DeprecationWarning` emitted at runtime on Python 3.10+; will become an error in a future Python version
- Files: `custom_components/sonoff/core/ewelink/cloud.py:274`
- Trigger: Any cloud connection attempt on Python 3.10+
- Workaround: None currently; HA suppresses most deprecation warnings

**`APP.append()` on every config reload:**
- Symptoms: After multiple HA reloads, `APP` contains duplicate appsecret values
- Files: `custom_components/sonoff/__init__.py:116`
- Trigger: Reload the integration or restart HA multiple times without a full Python process restart
- Workaround: Restart the HA process (not just integration reload)

---

## Missing Critical Features

**No rate limiting on local LAN sends:**
- Problem: There is no per-device rate limit on outgoing LAN commands beyond the coalescing window
- Blocks: Safe operation with devices that have strict firmware-side rate limits (some POW devices)

**No exponential backoff on cloud reconnect:**
- Problem: Cloud WebSocket reconnect uses a fixed delay — aggressive reconnects during outages could be rate-limited by the eWeLink cloud
- Files: `custom_components/sonoff/core/ewelink/cloud.py`
- Blocks: Graceful handling of extended cloud outages

---

## Test Coverage Gaps

**Cloud WebSocket logic completely untested:**
- What's not tested: Connect, reconnect, message dispatch, ping/pong, authentication handshake
- Files: `custom_components/sonoff/core/ewelink/cloud.py`
- Risk: Regressions in cloud connectivity go undetected until runtime
- Priority: High

**LAN discovery and send untested:**
- What's not tested: Zeroconf device discovery, local AES encrypt/decrypt round-trip, `ECONNRESET` retry logic
- Files: `custom_components/sonoff/core/ewelink/local.py`
- Risk: Local-only users can be broken by a refactor with no test signal
- Priority: High

**Camera entirely untested:**
- What's not tested: UDP broadcast, frame decoding, thread lifecycle, `wait()` timeout
- Files: `custom_components/sonoff/core/ewelink/camera.py`
- Risk: Any change to camera code is unverifiable without a physical device
- Priority: Medium

**Integration setup / teardown untested:**
- What's not tested: `async_setup_entry`, `async_unload_entry`, `UNIQUE_DEVICES` lifecycle
- Files: `custom_components/sonoff/__init__.py`
- Risk: Multi-account and reload scenarios are untested; stale state bugs go undetected
- Priority: High

**Config flow untested:**
- What's not tested: User-facing setup wizard, credential validation, region selection
- Files: `custom_components/sonoff/config_flow.py`
- Risk: UI regressions not caught; new HA config flow API changes break setup silently
- Priority: Medium

**`test_backward.py` uses wildcard imports:**
- What's fragile: `from x import *` means new symbols added to source modules automatically enter test scope — test may pass or fail for the wrong reasons
- Files: `tests/test_backward.py`
- Risk: False positives on backward-compatibility checks
- Priority: Low

**Multi-instance (two config entries) never tested:**
- What's not tested: Two simultaneous `XRegistry` instances, shared class attributes, `UNIQUE_DEVICES` collisions
- Files: `custom_components/sonoff/core/ewelink/__init__.py`, `custom_components/sonoff/__init__.py`
- Risk: Class-level shared state bugs only manifest in multi-account setups
- Priority: Medium

---

## Dependencies at Risk

**eWeLink cloud API (reverse-engineered, no SLA):**
- Risk: The cloud protocol is reverse-engineered; Sonoff/eWeLink can change endpoints, auth, or signing at any time
- Impact: Cloud-dependent features break for all users simultaneously with no warning
- Migration plan: No alternative; maintain close watch on upstream `AlexxIT/SonoffLAN` for protocol updates

**Home Assistant internal APIs (`CachedProperties`, entity registration):**
- Risk: HA's `CachedProperties` metaclass is an internal implementation detail; `unwrap_cached_properties()` workaround will break silently if HA refactors it
- Impact: Entity registration fails; no entities appear in HA
- Migration plan: Track HA changelog for metaclass changes; replace `type()`-based entity creation with explicit classes

---

*Concerns audit: 2026-04-03*
