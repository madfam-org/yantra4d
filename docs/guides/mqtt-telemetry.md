# MQTT Telemetry — Real-Time Sensor Data for 4D Hyperobjects

The MQTT Telemetry Service injects continuous temporal data from IoT sensors, printer telemetry, or external systems into parametric models, enabling real-time 3D Digital Twin behavior.

## Overview

When enabled, a background MQTT client subscribes to topics representing sensor feeds. Incoming data is:

1. **Cached** in-memory for latest-state lookups
2. **Broadcast** to registered callbacks for per-topic processing
3. **Queued** into a global queue (max 1,000 events) for SSE streaming to the frontend
4. **Merged** into CAD parameters at render time via `inject_telemetry_to_params()`

This provides the "Phased" (temporal) dimension to Bounded 4D Hyperobjects — geometry adapts to live sensor input right before OpenSCAD/CadQuery compilation.

## Configuration

All configuration is via environment variables. The service is **disabled by default**.

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_ENABLED` | `false` | Enable/disable the MQTT telemetry service |
| `MQTT_BROKER` | `localhost` | MQTT broker hostname or IP |
| `MQTT_PORT` | `1883` | MQTT broker port (IANA standard) |
| `MQTT_USERNAME` | — | Optional authentication username |
| `MQTT_PASSWORD` | — | Optional authentication password |
| `MQTT_TLS` | `false` | Enable TLS encryption for the connection |
| `MQTT_CA_CERTS` | — | Optional path to custom CA certificate bundle (when TLS enabled) |

### Quick Start (local dev)

```bash
# Start a local MQTT broker (e.g., Mosquitto)
docker run -d -p 1883:1883 eclipse-mosquitto

# Enable telemetry in your .env
MQTT_ENABLED=true
MQTT_BROKER=localhost
MQTT_PORT=1883
```

The `docker-compose.dev.yml` includes a pre-configured Mosquitto service with the config at `scripts/dev/mosquitto.conf`.

## Architecture

### Service Lifecycle

```
App startup
  └─► telemetry_service.start()
        ├─ If MQTT_ENABLED=false → logs "disabled", returns
        ├─ Configures auth (username/password) if provided
        ├─ Configures TLS if MQTT_TLS=true
        ├─ Sets reconnect delay (1s initial, 120s max)
        ├─ Connects to broker
        └─ Spawns daemon thread running client.loop_forever()

App shutdown (atexit)
  └─► telemetry_service.stop()
        ├─ Disconnects MQTT client
        └─ Joins background thread (5s timeout)
```

### Message Flow

```
MQTT Broker
  │
  ▼
_on_internal_message()
  ├─ Decode payload (JSON, float, int, or raw string)
  ├─ Update telemetry_cache[topic]
  ├─ Fire registered callbacks
  └─ Push to telemetry_queue (global, for SSE routes)
       │
       ▼
  SSE endpoint streams events to frontend
```

### Payload Parsing

Incoming MQTT payloads are parsed in order:

1. **JSON object** — parsed as-is (e.g., `{"temperature": 215.5, "humidity": 42}`)
2. **Numeric string** — wrapped as `{"value": 215.5}` or `{"value": 42}`
3. **Raw string** — wrapped as `{"value": "some-string"}`

### Parameter Injection

`inject_telemetry_to_params(base_params, topic)` merges telemetry state into CAD parameters:

- Each telemetry key is prefixed with `telemetry_` to avoid name collisions
- Example: MQTT payload `{"temperature": 215}` becomes `{"telemetry_temperature": 215}` in the parameter dict
- The merged dict is passed to the render engine, where `$telemetry_temperature` is available in OpenSCAD

### Queue Overflow

The global queue holds up to 1,000 events. When full, the oldest event is discarded to make room for new data (drop-oldest strategy).

## Topic Subscriptions

Register topic callbacks for specific hyperobject telemetry feeds:

```python
from services.core.mqtt_telemetry import telemetry_service

def handle_temperature(topic, payload):
    print(f"Temperature update: {payload}")

telemetry_service.subscribe("printer/bed_temperature", handle_temperature)
```

On reconnect, all registered topics are automatically re-subscribed.

## Reconnection

The MQTT client uses exponential backoff for reconnection:

- Initial delay: **1 second**
- Maximum delay: **120 seconds**
- Auto-reconnect is enabled by default via `paho-mqtt`
- On reconnect, all registered topic subscriptions are restored

## Integration with Printer Telemetry (Sprint 15)

The MQTT telemetry bridge was wired into the printer panel in Sprint 15. OctoPrint and Moonraker printer integrations publish temperature, print progress, and status events to MQTT topics. The `PrintPanel.jsx` frontend component polls these events via SSE for live temperature gauges and status display.

## Key Files

| File | Purpose |
|------|---------|
| `apps/api/services/core/mqtt_telemetry.py` | MQTT client, telemetry cache, parameter injection |
| `apps/api/routes/integrations/printer.py` | Printer dispatch and telemetry SSE endpoints |
| `apps/studio/src/components/studio/PrintPanel.jsx` | Printer UI with live telemetry display |
| `scripts/dev/mosquitto.conf` | Local Mosquitto broker configuration |
| `scripts/dev/mock_telemetry_publisher.py` | Mock publisher for development/testing |
