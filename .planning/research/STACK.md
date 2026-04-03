# Technology Stack

**Project:** SonoffLAN-InfluxDB standalone daemon
**Researched:** 2026-04-03
**Sources verified:** PyPI (live), GitHub source (main branch), Docker Hub (live)

---

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12 | Runtime | LTS line, best performance per InfluxDB client docs; client supports 3.8–3.13, use 3.12-slim for Docker |
| asyncio | stdlib | Event loop | Already used throughout codebase; no alternative needed |

### Core Dependencies (carry forward from HA codebase)

| Library | PyPI Version | Purpose | Why |
|---------|-------------|---------|-----|
| `zeroconf` | **0.148.0** | mDNS discovery (`_ewelink._tcp.local.`) | Already used in `core/ewelink/local.py`; `AsyncServiceBrowser` + `AsyncServiceInfo` APIs unchanged |
| `aiohttp` | **3.13.5** | HTTP POST to devices (LAN command/ping) | Already used in `core/ewelink/local.py`; `ClientSession` is the stable async HTTP client |
| `cryptography` | **46.0.6** | AES-128-CBC decrypt of encrypted LAN payloads | Already used; `hazmat.primitives.ciphers` (Cipher, algorithms.AES, modes.CBC) + PKCS7 padding — API stable across major versions |

### New Dependencies

| Library | PyPI Version | Purpose | Why |
|---------|-------------|---------|-----|
| `influxdb3-python` | **0.18.0** | Write energy metrics to InfluxDB 3 Core | Official InfluxData client for v3 API; uses HTTP write endpoint + Apache Arrow Flight for queries; only client that natively targets the v3 write API (not v1/v2 line protocol legacy path) |

### Dev / Build Only

| Library | PyPI Version | Purpose | Why |
|---------|-------------|---------|-----|
| `pytest` | latest | Test runner | Already used in codebase (`tests/pytest.ini`) |
| `pytest-asyncio` | latest | Async test support | Required for testing asyncio-based daemon code |

---

## influxdb3-python: Write API Deep-Dive

**Package name (install):** `influxdb3-python`
**Import name:** `influxdb_client_3`
**Latest:** 0.18.0 (released 2026-02-19) — active release cadence (monthly)
**License:** MIT
**Status:** Beta (PyPI classifier: Development Status 4 - Beta)

### Key Finding: No Native `write_async()`

The `InfluxDBClient3.write()` method is **synchronous/blocking**. The client does expose `query_async()` but has **no `write_async()`** method. Source confirmed in `influxdb_client_3/__init__.py` (main branch, 2026-04-03).

**Integration pattern for asyncio daemon:**

```python
import asyncio
from influxdb_client_3 import InfluxDBClient3, Point

# Initialize once at startup (synchronous, not per-write)
_influx = InfluxDBClient3(
    host=os.environ["INFLUX_HOST"],       # e.g. "http://192.168.1.10:8086"
    token=os.environ["INFLUX_TOKEN"],
    database=os.environ["INFLUX_DATABASE"],
)

async def write_energy(device_id: str, params: dict) -> None:
    """Write one energy event. Called from asyncio event loop."""
    point = (
        Point(device_id)                          # measurement = device_id
        .field("power",   float(params["power"]))
        .field("voltage", float(params["voltage"]))
        .field("current", float(params["current"]))
    )
    loop = asyncio.get_running_loop()
    try:
        # Offload blocking write to thread pool — keeps event loop unblocked
        await loop.run_in_executor(None, _influx.write, point)
    except Exception as e:
        logger.error("InfluxDB write failed for %s: %s", device_id, e)
        # log-and-continue: do not re-raise
```

**Why `run_in_executor`:** `influxdb3-python` uses `urllib3` + `reactivex` under the hood for the synchronous write path. Calling `_influx.write()` directly from a coroutine blocks the event loop for the duration of the HTTP POST. Wrapping with `run_in_executor(None, ...)` runs it in the default `ThreadPoolExecutor`, keeping mDNS + aiohttp I/O responsive.

### Write API Reference

```python
from influxdb_client_3 import InfluxDBClient3, Point, WritePrecision

# Constructor
client = InfluxDBClient3(
    host="http://192.168.1.10:8086",   # scheme + host + port
    token="my-token",
    database="sonoff",                  # InfluxDB 3 "database" == v2 "bucket"
    org="default",                      # required for write path; use "default" for Core
)

# Point builder (fluent API)
point = (
    Point("my_measurement")            # measurement name
    .tag("device_id", "1000abcd")      # tag (indexed, string)
    .field("power", 125.4)             # field (float)
    .field("voltage", 230.1)           # field (float)
    .field("current", 0.545)           # field (float)
    # .time(ts, WritePrecision.NS)     # optional: defaults to server time
)

# Synchronous write (default WriteType.synchronous)
client.write(record=point)

# Line protocol string also works:
client.write(record="energy_usage power=125.4,voltage=230.1 1712345678000000000")

# Explicit synchronous write options (use for daemon — no batching)
from influxdb_client_3 import WriteOptions, WriteType, write_client_options
wco = write_client_options(
    write_options=WriteOptions(write_type=WriteType.synchronous)
)
client = InfluxDBClient3(..., write_client_options=wco)

# Cleanup
client.close()
```

### Environment Variable Support (built-in)

`InfluxDBClient3.from_env()` reads these env vars natively:

| Env Var | Purpose |
|---------|---------|
| `INFLUX_HOST` | Server URL |
| `INFLUX_TOKEN` | Auth token |
| `INFLUX_DATABASE` | Database/bucket name |
| `INFLUX_ORG` | Org (default: "default") |
| `INFLUX_PRECISION` | Write precision |
| `INFLUX_WRITE_TIMEOUT` | Write timeout (ms) |

**Recommendation:** Use `InfluxDBClient3.from_env()` in the daemon entrypoint — it reads the three required vars and raises `ValueError` with a clear message if any are missing. No custom env-parsing code needed for the InfluxDB connection.

### Transitive Dependencies

`influxdb3-python` pulls in:
- `pyarrow` (auto-installed) — Arrow Flight for queries; required even for write-only use
- `reactivex` — batching write internals (not used in synchronous mode but installed)
- `urllib3` — HTTP write transport

**No pandas needed** — we never call `write_dataframe()` or `write_file()`.

---

## What NOT to Use

### ❌ `influxdb-client` (the v2 client)

```
pip install influxdb-client   # DO NOT USE
```

- Targets InfluxDB 1.x / 2.x API
- Uses `/api/v2/write` endpoint (v2 line protocol)
- InfluxDB 3 Core does not expose the v2 write API by default
- Different auth model (org/bucket vs database)
- Maintained separately; no v3 support roadmap

### ❌ Direct HTTP writes (requests / aiohttp to `/api/v2/write`)

- Tempting to reuse the existing `aiohttp.ClientSession`, but InfluxDB 3 Core uses a different write endpoint and auth scheme
- `influxdb3-python` handles auth header injection, precision encoding, and error classification correctly
- Not worth reinventing for this project's scope

### ❌ Telegraf as a sidecar

- Adds operational complexity (two containers, config sync)
- Loses the direct integration with the LAN protocol layer
- Out of scope per PROJECT.md

---

## Docker Packaging

### Base Image

```dockerfile
FROM python:3.12-slim
```

**Why `3.12-slim`:**
- `slim` = Debian bookworm base stripped of docs/locales/unused packages (~41 MB compressed amd64 vs ~150 MB full)
- `3.12` = current LTS Python; InfluxDB client recommends 3.11+ for best performance; 3.12 is the sweet spot (3.13 is latest but `pyarrow` wheels may lag on some platforms — use 3.12 to be safe)
- Do **not** use `alpine`: `cryptography` and `pyarrow` require Rust/C build tools on alpine; `slim` has pre-built wheels for both

**Specific pinned form (for reproducibility):**
```dockerfile
FROM python:3.12-slim-bookworm
```
Bookworm (Debian 12) is the current stable base; `3.12-slim` resolves to it as of 2026-04.

### Packaging Approach: `pyproject.toml` + `requirements.txt`

Use a `requirements.txt` pinned for Docker and a `pyproject.toml` for project metadata.

**Rationale:** The existing codebase has no packaging files (declared as HA manifest-only). For a daemon:
- `pyproject.toml` — project metadata, Python version constraint, optional dev dependencies
- `requirements.txt` — pinned versions for reproducible Docker builds

```
# requirements.txt (pinned)
influxdb3-python==0.18.0
zeroconf==0.148.0
aiohttp==3.13.5
cryptography==46.0.6
```

```toml
# pyproject.toml
[project]
name = "sonofflan-influx"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "influxdb3-python>=0.18.0",
    "zeroconf>=0.148.0",
    "aiohttp>=3.13.5",
    "cryptography>=46.0.6",
]

[project.scripts]
sonofflan-influx = "daemon:main"
```

### Dockerfile Pattern

```dockerfile
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root user (security best practice)
RUN useradd -r -s /bin/false daemon
USER daemon

# Env vars — all required, no defaults (fail fast at startup)
# INFLUX_HOST, INFLUX_TOKEN, INFLUX_DATABASE, SONOFF_DEVICES

CMD ["python", "-m", "daemon"]
```

**No `CMD` arg parsing needed** — all config via `ENV` / `docker run -e` / `docker-compose environment:`.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| InfluxDB client | `influxdb3-python` | `influxdb-client` (v2) | v2 client doesn't support InfluxDB 3 write API; different auth/endpoint |
| InfluxDB client | `influxdb3-python` | raw `aiohttp` to `/api/v3/write` | influxdb3-python handles precision, auth, error codes; not worth reinventing |
| Base image | `python:3.12-slim-bookworm` | `python:3.12-alpine` | Alpine needs Rust build tools for `cryptography`; `pyarrow` wheels unavailable on musl; significantly larger final image |
| Base image | `python:3.12-slim-bookworm` | `python:3.13-slim` | 3.13 is latest but `pyarrow` wheels occasionally lag; 3.12 is safer for this dependency set |
| Packaging | `requirements.txt` + `pyproject.toml` | `poetry` / `uv` | Adds tooling complexity for a single-file daemon; standard pip is sufficient |
| Async write | `run_in_executor` + `influxdb3-python` | standalone `asyncio` HTTP client | `influxdb3-python` handles auth, precision, error codes; worth the thread hop |

---

## Sources

| Source | URL | Confidence |
|--------|-----|------------|
| influxdb3-python PyPI | https://pypi.org/project/influxdb3-python/ | HIGH — verified live |
| influxdb3-python source | https://github.com/InfluxCommunity/influxdb3-python/blob/main/influxdb_client_3/__init__.py | HIGH — read directly |
| zeroconf PyPI | pip index versions (live) | HIGH |
| aiohttp PyPI | pip index versions (live) | HIGH |
| cryptography PyPI | pip index versions (live) | HIGH |
| Docker Hub python tags | https://hub.docker.com/_/python/tags | HIGH — verified live |

---

*Stack research: 2026-04-03*
