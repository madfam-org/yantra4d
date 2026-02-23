"""Unit tests for MQTT Telemetry Service."""
import json

from unittest.mock import MagicMock, patch


class TestMqttTelemetryServiceInit:
    """Tests for MqttTelemetryService.__init__ and environment variable handling."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_init_defaults(self, MockClient, monkeypatch):
        monkeypatch.delenv("MQTT_BROKER", raising=False)
        monkeypatch.delenv("MQTT_PORT", raising=False)
        monkeypatch.setenv("MQTT_ENABLED", "true")
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        assert svc.broker == "localhost"
        assert svc.port == 1883
        assert svc.enabled is True
        assert svc.connected is False
        assert svc.telemetry_cache == {}
        assert svc.topic_callbacks == {}

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_init_custom_env(self, MockClient, monkeypatch):
        monkeypatch.setenv("MQTT_BROKER", "broker.example.com")
        monkeypatch.setenv("MQTT_PORT", "8883")
        monkeypatch.setenv("MQTT_ENABLED", "false")
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        assert svc.broker == "broker.example.com"
        assert svc.port == 8883
        assert svc.enabled is False


class TestMqttTelemetryServiceStart:
    """Tests for start() method — connection lifecycle."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_disabled_start_noop(self, MockClient, monkeypatch):
        monkeypatch.setenv("MQTT_ENABLED", "false")
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.start()
        svc.client.connect.assert_not_called()

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_start_connects_and_spawns_thread(self, MockClient, monkeypatch):
        monkeypatch.setenv("MQTT_ENABLED", "true")
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.start()
        svc.client.connect.assert_called_once_with("localhost", 1883, 60)

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_start_connection_failure_does_not_raise(self, MockClient, monkeypatch):
        monkeypatch.setenv("MQTT_ENABLED", "true")
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.client.connect.side_effect = Exception("Connection refused")
        svc.start()  # should not propagate
        assert svc.connected is False


class TestSubscribe:
    """Tests for subscribe() method — topic registration."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_subscribe_stores_callback_in_list(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        cb = MagicMock()
        svc.subscribe("sensors/temp", cb)
        assert "sensors/temp" in svc.topic_callbacks
        assert cb in svc.topic_callbacks["sensors/temp"]

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_subscribe_multiple_callbacks_same_topic(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        cb1 = MagicMock()
        cb2 = MagicMock()
        svc.subscribe("sensors/temp", cb1)
        svc.subscribe("sensors/temp", cb2)
        assert len(svc.topic_callbacks["sensors/temp"]) == 2

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_subscribe_when_connected_sends_mqtt_subscribe(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.connected = True
        cb = MagicMock()
        svc.subscribe("sensors/temp", cb)
        svc.client.subscribe.assert_called_once_with("sensors/temp")


class TestOnConnect:
    """Tests for _on_connect callback."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_on_connect_success_resubscribes_all_topics(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.topic_callbacks = {"a": [lambda t, p: None], "b": [lambda t, p: None]}
        svc._on_connect(svc.client, None, None, 0, None)
        assert svc.connected is True
        assert svc.client.subscribe.call_count == 2

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_on_connect_failure_sets_disconnected(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc._on_connect(svc.client, None, None, 5, None)
        assert svc.connected is False


class TestOnInternalMessage:
    """Tests for _on_internal_message callback — payload parsing and dispatch."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_json_payload_cached(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        msg = MagicMock()
        msg.topic = "sensors/temp"
        msg.payload = json.dumps({"temp": 22.5}).encode("utf-8")
        svc._on_internal_message(svc.client, None, msg)
        assert svc.telemetry_cache["sensors/temp"] == {"temp": 22.5}

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_bare_int_string_parsed_as_json(self, MockClient):
        """Bare integers are valid JSON, so json.loads succeeds directly."""
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        msg = MagicMock()
        msg.topic = "sensors/count"
        msg.payload = b"42"
        svc._on_internal_message(svc.client, None, msg)
        assert svc.telemetry_cache["sensors/count"] == 42

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_bare_float_string_parsed_as_json(self, MockClient):
        """Bare floats are valid JSON, so json.loads succeeds directly."""
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        msg = MagicMock()
        msg.topic = "sensors/voltage"
        msg.payload = b"3.14"
        svc._on_internal_message(svc.client, None, msg)
        assert svc.telemetry_cache["sensors/voltage"] == 3.14

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_plain_string_payload_wrapped(self, MockClient):
        """Non-JSON, non-numeric strings are wrapped as {'value': str}."""
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        msg = MagicMock()
        msg.topic = "sensors/status"
        msg.payload = b"hello"
        svc._on_internal_message(svc.client, None, msg)
        assert svc.telemetry_cache["sensors/status"] == {"value": "hello"}

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_callback_fired_on_message(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        cb = MagicMock()
        svc.topic_callbacks["sensors/temp"] = [cb]
        msg = MagicMock()
        msg.topic = "sensors/temp"
        msg.payload = json.dumps({"temp": 22}).encode("utf-8")
        svc._on_internal_message(svc.client, None, msg)
        cb.assert_called_once_with("sensors/temp", {"temp": 22})

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_callback_error_does_not_propagate(self, MockClient):
        """A broken callback must not crash message processing."""
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        bad_cb = MagicMock(side_effect=RuntimeError("boom"))
        svc.topic_callbacks["t"] = [bad_cb]
        msg = MagicMock()
        msg.topic = "t"
        msg.payload = json.dumps({"x": 1}).encode("utf-8")
        svc._on_internal_message(svc.client, None, msg)
        # Cache should still be updated
        assert svc.telemetry_cache["t"] == {"x": 1}

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_message_pushed_to_telemetry_queue(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService, telemetry_queue

        # Drain any leftover items
        while not telemetry_queue.empty():
            telemetry_queue.get_nowait()

        svc = MqttTelemetryService()
        msg = MagicMock()
        msg.topic = "q/test"
        msg.payload = json.dumps({"val": 99}).encode("utf-8")
        svc._on_internal_message(svc.client, None, msg)

        item = telemetry_queue.get_nowait()
        assert item["topic"] == "q/test"
        assert item["payload"] == {"val": 99}


class TestGetLatestState:
    """Tests for get_latest_state() — cache retrieval."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_returns_cached_value(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.telemetry_cache["t"] = {"val": 1}
        assert svc.get_latest_state("t") == {"val": 1}

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_returns_empty_dict_for_missing_topic(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        assert svc.get_latest_state("missing") == {}


class TestInjectTelemetryToParams:
    """Tests for inject_telemetry_to_params() — parameter merging."""

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_merges_telemetry_with_prefix(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.telemetry_cache["t"] = {"temp": 22, "humidity": 50}
        result = svc.inject_telemetry_to_params({"width": 10}, "t")
        assert result["width"] == 10
        assert result["telemetry_temp"] == 22
        assert result["telemetry_humidity"] == 50

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_no_state_returns_base_params(self, MockClient):
        """Missing topic returns empty dict which is falsy, so base_params returned."""
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        result = svc.inject_telemetry_to_params({"width": 10}, "missing")
        assert result == {"width": 10}

    @patch("services.core.mqtt_telemetry.mqtt.Client")
    def test_does_not_mutate_original_params(self, MockClient):
        from services.core.mqtt_telemetry import MqttTelemetryService

        svc = MqttTelemetryService()
        svc.telemetry_cache["t"] = {"x": 1}
        original = {"width": 10}
        result = svc.inject_telemetry_to_params(original, "t")
        assert "telemetry_x" not in original
        assert "telemetry_x" in result
