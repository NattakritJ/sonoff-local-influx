# SonoffLAN-InfluxDB

A standalone Python daemon that listens for energy telemetry from Sonoff smart devices on the local network and writes the data to an **InfluxDB 3 Core** instance.

No Home Assistant. No cloud account. No buffering. Every energy event is written to InfluxDB immediately as it arrives over LAN.

---

## How it works

1. The daemon discovers Sonoff devices on the local network using **mDNS/zeroconf**.
2. When a device broadcasts an energy update, the payload is decrypted (AES-128-CBC) using the device key you supply.
3. `power`, `voltage`, `current`, and `energy_today` are extracted and written as a Point to InfluxDB 3 Core.
4. Each device gets its own **measurement** named by `device_id`, with `device_id` and `device_name` as tags.

---

## Supported devices

Energy metering devices supported over LAN:

| UIID | Models                  | Channels   |
| ---- | ----------------------- | ---------- |
| 32   | POWR2, POWR3, PSF-X67   | Single     |
| 126  | DualR3                  | 2 channels |
| 130  | SPM-4Relay              | 4 channels |
| 182  | S40 (S40TPB)            | Single     |
| 190  | POWCT, POWR320D, S60TPF | Single     |
| 226  | CK-BL602-W102SW18       | Single     |
| 262  | CK-BL602-SWP1-02        | Single     |
| 276  | S61STPF                 | Single     |
| 277  | MINI-DIM                | Single     |
| 7032 | S60ZBTPF                | Single     |

See [DEVICES.md](DEVICES.md) for the full device compatibility table.

---

## Prerequisites

- Docker and Docker Compose
- A running **InfluxDB 3 Core** instance reachable from the host
- Your Sonoff device IDs and device keys (see [Finding your device credentials](#finding-your-device-credentials))

---

## Deploy with Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/your-org/SonoffLAN-influx.git
cd SonoffLAN-influx
```

### 2. Create your `.env` file

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# JSON array of Sonoff devices to monitor
SONOFF_DEVICES=[{"device_id":"1000xxxxxx","uiid":190,"devicekey":"abcd1234abcd1234abcd1234abcd1234","device_name":"Kitchen Socket"}]

# InfluxDB 3 Core connection
INFLUX_HOST=http://192.168.1.100:8086
INFLUX_TOKEN=your-influxdb-token-here
INFLUX_DATABASE=sonoff
```

**Multiple devices:**

```env
SONOFF_DEVICES=[
  {"device_id":"1000aaaaaa","uiid":190,"devicekey":"key1aaaaaaaaaaaaaaaaaaaaaaaaaaa1","device_name":"Living Room"},
  {"device_id":"1000bbbbbb","uiid":126,"devicekey":"key2bbbbbbbbbbbbbbbbbbbbbbbbbbbb","device_name":"Office"}
]
```

**DIY / unencrypted devices** (omit `devicekey`):

```env
SONOFF_DEVICES=[{"device_id":"1000cccccc","uiid":32,"device_name":"DIY Plug"}]
```

### 3. Start the daemon

```bash
docker compose up -d
```

The daemon builds the image on first run. To rebuild after a code change:

```bash
docker compose up -d --build
```

### 4. Verify it is running

```bash
docker compose logs -f
```

Expected output on startup:

```
2026-04-03T10:00:00 INFO sonoff_daemon: InfluxDB connected | host=http://192.168.1.100:8086 | database=sonoff
2026-04-03T10:00:00 INFO sonoff_daemon: SonoffLAN-InfluxDB ready | devices=1 | influx=http://192.168.1.100:8086 | ids=['1000xxxxxx']
```

When a device reports energy data:

```
2026-04-03T10:00:05 INFO sonoff_daemon: WRITE | 1000xxxxxx (Kitchen Socket) | ch=- | power=45.3 W | voltage=230.1 V | current=0.197 A
```

### 5. Stop the daemon

```bash
docker compose down
```

---

## Environment variable reference

| Variable          | Required | Description                                                   |
| ----------------- | -------- | ------------------------------------------------------------- |
| `SONOFF_DEVICES`  | Yes      | JSON array of device objects (see below)                      |
| `INFLUX_HOST`     | Yes      | Full URL to InfluxDB 3 Core, e.g. `http://192.168.1.100:8086` |
| `INFLUX_TOKEN`    | Yes      | InfluxDB API token with write access                          |
| `INFLUX_DATABASE` | Yes      | InfluxDB database (bucket) name                               |

### `SONOFF_DEVICES` object fields

| Field         | Required | Description                                                                                                           |
| ------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `device_id`   | Yes      | 10-digit Sonoff device ID                                                                                             |
| `uiid`        | Yes      | Sonoff device type ID (e.g. `190` for POWR3/POWCT, `32` for POWR2/S31, `126` for DualR3). See supported device table |
| `devicekey`   | No       | 32-character AES device key — omit for DIY/unencrypted devices                                                        |
| `device_name` | No       | Human-readable label (defaults to `device_id`)                                                                        |

---

## InfluxDB data model

Each energy event is written as a Point:

- **Measurement:** `device_id` (e.g. `1000xxxxxx`)
- **Tags:** `device_id`, `device_name`
- **Fields:** `power` (W), `voltage` (V), `current` (A), `energy_today` (kWh, where available)
- `None` / missing values are omitted — no nulls written

Multi-channel devices (DualR3, SPM-4Relay) write one Point per channel, with a `channel` field (1-based).

---

## Finding your device credentials

### Device ID

The device ID is the 10-digit serial number printed on the device label, or visible in the eWeLink app under **Device Info**.

### Device key (`devicekey`)

The device key is a 32-character AES-128 key used to encrypt LAN traffic. To retrieve it:

1. Open the [eWeLink web console](https://web.ewelink.cc) or use the mobile app.
2. Navigate to **Device** → **Device Info** → look for the device API key / LAN key.
3. Alternatively, use a tool like [SonoffLAN](https://github.com/AlexxIT/SonoffLAN) in Home Assistant — it logs device keys when it discovers devices.

DIY-mode devices (Sonoff DIY firmware) do not use encryption; omit `devicekey` for these.

---

## Network requirements

The daemon uses `network_mode: host` in Docker Compose. This is **required on Linux** for mDNS/zeroconf to work — the container must be on the same Layer 2 network segment as your Sonoff devices.

> **macOS / Windows Docker Desktop:** `network_mode: host` does **not** work on macOS or Windows Docker Desktop. Docker Desktop runs containers inside a Linux VM; multicast UDP packets (mDNS) sent by Sonoff devices on your LAN never reach the container. The daemon will start and log "ready" but receive no events and write nothing.
>
> **On macOS/Windows, run the daemon locally without Docker** (see [Running locally](#running-locally-without-docker) below).

If your Docker host (Linux) and Sonoff devices are on different VLANs, mDNS discovery will not work without a multicast proxy (e.g. `avahi-daemon` with reflector mode, or `mdns-repeater`).

---

## Running locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SONOFF_DEVICES='[{"device_id":"1000xxxxxx","uiid":190,"devicekey":"...","device_name":"Test"}]'
export INFLUX_HOST=http://localhost:8086
export INFLUX_TOKEN=my-token
export INFLUX_DATABASE=sonoff

python src/__main__.py
```

---

## Logging

Log output goes to stdout in the format:

```
YYYY-MM-DDTHH:MM:SS LEVEL logger: message
```

Key log events:

| Level     | Event                                       |
| --------- | ------------------------------------------- |
| `INFO`    | Startup, InfluxDB connection, each write    |
| `INFO`    | Heartbeat every 60 s with total write count |
| `WARNING` | Decryption failure for a device payload     |
| `ERROR`   | InfluxDB write failure (daemon continues)   |

---

## License

See [LICENSE.md](LICENSE.md).
