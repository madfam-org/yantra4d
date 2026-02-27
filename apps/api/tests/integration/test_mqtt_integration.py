"""
apps/api/tests/integration/test_mqtt_integration.py

Integration tests for the MQTT telemetry service.

These tests spin up an actual MQTT broker connection using the real
MqttTelemetryService and verify the full publish → receive → cache → inject
pipeline works end-to-end.

Tests are skipped unless MQTT_TEST_ENABLED=true is set, so they don't block
the normal unit test suite (which runs without a broker).

To run:
    MQTT_TEST_ENABLED=true MQTT_BROKER=localhost pytest tests/integration/test_mqtt_integration.py -v
"""

import json
import os
import time
import threading
import pytest

# Guard: skip this entire file unless explicitly opted in
if os.getenv("MQTT_TEST_ENABLED", "false").lower() != "true":
    pytest.skip(
        "MQTT integration tests skipped. Set MQTT_TEST_ENABLED=true to enable.",
        allow_module_level=True,
    )

try:
    import paho.mqtt.client as mqtt
except ImportError:
    pytest.skip("paho-mqtt not installed", allow_module_level=True)


BROKER_HOST = os.getenv("MQTT_BROKER", "localhost")
BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))
TEST_TOPIC = "yantra4d/telemetry/test/integration"
TEST_PAYLOAD = {
    "simulated_energy": 85.5,
    "ambient_temp_c": 23.1,
    "print_progress_pct": 42,
}


def _publish_to_broker(topic: str, payload: dict, host: str, port: int) -> bool:
    """Helper: publish a single JSON message and disconnect."""
    success_event = threading.Event()

    pub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-publisher")

    def on_connect(c, u, f, rc, p):
        if rc == 0:
            c.publish(topic, json.dumps(payload), qos=1)
            success_event.set()

    pub_client.on_connect = on_connect

    try:
        pub_client.connect(host, port, keepalive=10)
        pub_client.loop_start()
        connected = success_event.wait(timeout=5.0)
        time.sleep(0.2)  # allow publish to complete
        pub_client.loop_stop()
        pub_client.disconnect()
        return connected
    except Exception:
        return False


@pytest.fixture(scope="module")
def telemetry_service():
    """Fixture that returns a fresh MqttTelemetryService connected to the broker."""
    # Import here so tests that skip early don't pull in backend internals
    import sys
    import os as _os

    # Ensure the API app root is on sys.path for direct import
    api_root = _os.path.join(_os.path.dirname(__file__), "../..")
    if api_root not in sys.path:
        sys.path.insert(0, _os.path.abspath(api_root))

    from services.core.mqtt_telemetry import MqttTelemetryService

    _os.environ["MQTT_BROKER"] = BROKER_HOST
    _os.environ["MQTT_PORT"] = str(BROKER_PORT)
    _os.environ["MQTT_ENABLED"] = "true"

    svc = MqttTelemetryService()
    svc.start()
    time.sleep(1.0)  # allow connection to establish
    yield svc
    svc.client.disconnect()


class TestMqttConnection:
    def test_service_connects_to_broker(self, telemetry_service):
        """After start(), the service should report connected=True."""
        assert telemetry_service.connected is True, (
            f"MqttTelemetryService failed to connect to {BROKER_HOST}:{BROKER_PORT}. "
            "Is the broker running?"
        )


class TestTelemetryCache:
    def test_published_payload_enters_cache(self, telemetry_service):
        """Payload published to the subscribed topic must appear in telemetry_cache."""
        received_event = threading.Event()

        def on_receive(topic, payload):
            received_event.set()

        telemetry_service.subscribe(TEST_TOPIC, on_receive)

        ok = _publish_to_broker(TEST_TOPIC, TEST_PAYLOAD, BROKER_HOST, BROKER_PORT)
        assert ok, "Test publisher failed to connect to broker."

        received = received_event.wait(timeout=5.0)
        assert received, "Telemetry service did not receive the published message within 5s."

        cached = telemetry_service.get_latest_state(TEST_TOPIC)
        assert cached.get("simulated_energy") == pytest.approx(TEST_PAYLOAD["simulated_energy"])
        assert cached.get("print_progress_pct") == TEST_PAYLOAD["print_progress_pct"]

    def test_cache_initially_empty_for_unknown_topic(self, telemetry_service):
        """Querying an unpublished topic returns an empty dict."""
        result = telemetry_service.get_latest_state("yantra4d/telemetry/nonexistent")
        assert result == {}


class TestTelemetryParamInjection:
    def test_inject_merges_telemetry_into_params(self, telemetry_service):
        """inject_telemetry_to_params merges cached telemetry into the base params dict."""
        # Seed the cache directly (no need to re-publish just for this test)
        with telemetry_service._lock:
            telemetry_service.telemetry_cache[TEST_TOPIC] = TEST_PAYLOAD

        base_params = {"grid_x": 2, "grid_y": 3, "height": 10}
        merged = telemetry_service.inject_telemetry_to_params(base_params, TEST_TOPIC)

        # Original params preserved
        assert merged["grid_x"] == 2
        assert merged["grid_y"] == 3

        # Telemetry values injected with telemetry_ prefix
        assert merged["telemetry_simulated_energy"] == pytest.approx(TEST_PAYLOAD["simulated_energy"])
        assert merged["telemetry_print_progress_pct"] == TEST_PAYLOAD["print_progress_pct"]

    def test_inject_is_noop_for_empty_cache(self, telemetry_service):
        """inject_telemetry_to_params is a pure pass-through when no telemetry cached."""
        base_params = {"grid_x": 1}
        result = telemetry_service.inject_telemetry_to_params(
            base_params, "yantra4d/telemetry/nonexistent-topic"
        )
        assert result == base_params

    def test_inject_does_not_mutate_original_params(self, telemetry_service):
        """inject_telemetry_to_params must return a new dict, not modify in place."""
        with telemetry_service._lock:
            telemetry_service.telemetry_cache[TEST_TOPIC] = {"val": 42}

        original = {"grid_x": 5}
        original_copy = original.copy()
        _ = telemetry_service.inject_telemetry_to_params(original, TEST_TOPIC)

        assert original == original_copy, "inject_telemetry_to_params mutated the input dict."
