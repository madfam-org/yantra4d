#!/usr/bin/env python3
"""
scripts/dev/mock_telemetry_publisher.py

Publishes synthetic 4D telemetry to a local Mosquitto broker so the Yantra4D
MQTT telemetry service has live data to inject into parametric renders in dev.

Usage:
    python3 scripts/dev/mock_telemetry_publisher.py [options]

Options:
    --broker   MQTT broker host         (default: localhost)
    --port     MQTT broker port         (default: 1883)
    --project  Project slug to target   (default: gridfinity)
    --interval Seconds between publishes (default: 2.0)
    --oneshot  Publish once and exit

Examples:
    # Publish to gridfinity with default settings
    python3 scripts/dev/mock_telemetry_publisher.py

    # Publish to implicit-lattice-hyperobject with faster interval
    python3 scripts/dev/mock_telemetry_publisher.py --project implicit-lattice-hyperobject --interval 0.5

    # Publish a single payload and exit (useful for CI)
    python3 scripts/dev/mock_telemetry_publisher.py --oneshot

Topics published:
    yantra4d/telemetry/projects/<slug>   → JSON payload with simulated_energy,
                                           ambient_temp_c, and print_progress_pct
"""

import argparse
import json
import math
import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt is not installed.")
    print("  pip install paho-mqtt")
    sys.exit(1)


def make_payload(tick: int, project: str) -> dict:
    """
    Generate a sinusoidal temperature profile simulating a 4D print cycle.

    The simulated_energy ramps from 20°C (ambient) up to 240°C (near melt)
    and back, looping every 120 ticks. This drives the Digital Twin phase
    simulation in the browser when energy crosses glass_transition_temp.
    """
    cycle = (tick % 120) / 120.0  # 0.0 → 1.0 over 120 ticks
    # Sinusoidal: peaks at 240°C, troughs at 20°C
    simulated_energy = 20.0 + 220.0 * math.sin(math.pi * cycle)
    ambient_temp = 22.0 + 3.0 * math.sin(math.pi * cycle * 2)  # slight room variation
    progress_pct = (tick % 100) + 1

    return {
        "simulated_energy": round(simulated_energy, 2),
        "ambient_temp_c": round(ambient_temp, 2),
        "print_progress_pct": progress_pct,
        "tick": tick,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Publish synthetic 4D telemetry to local MQTT broker"
    )
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--project", default="gridfinity", help="Project slug")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between publishes")
    parser.add_argument("--oneshot", action="store_true", help="Publish once and exit")
    args = parser.parse_args()

    topic = f"yantra4d/telemetry/projects/{args.project}"

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    connected = False

    def on_connect(c, userdata, flags, reason_code, properties):
        nonlocal connected
        if reason_code == 0:
            connected = True
            print(f"[OK]  Connected to {args.broker}:{args.port}")
            print(f"[>>]  Publishing to topic: {topic}")
            if not args.oneshot:
                print("      Press Ctrl+C to stop.\n")
        else:
            print(f"[ERR] Connection failed (code {reason_code})")
            sys.exit(1)

    client.on_connect = on_connect

    print(f"[..] Connecting to MQTT broker at {args.broker}:{args.port} ...")
    try:
        client.connect(args.broker, args.port, keepalive=60)
    except ConnectionRefusedError:
        print("[ERR] Connection refused. Is Mosquitto running?")
        print("      Start it with: docker compose -f docker-compose.dev.yml up mqtt-broker")
        sys.exit(1)

    client.loop_start()

    # Wait for connection
    for _ in range(20):
        if connected:
            break
        time.sleep(0.1)
    else:
        print("[ERR] Timed out waiting for MQTT connection.")
        sys.exit(1)

    tick = 0
    try:
        while True:
            payload = make_payload(tick, args.project)
            msg = json.dumps(payload)
            result = client.publish(topic, msg, qos=0, retain=False)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[t={tick:04d}] Published: {msg}")
            else:
                print(f"[WARN] Publish failed (rc={result.rc})")

            tick += 1
            if args.oneshot:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[--] Stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
