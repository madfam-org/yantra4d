"""
MQTT Telemetry Service for 4D Hyperobjects
Injects continuous temporal data into CadQuery/OpenSCAD 
parametric generation and Real-Time 3D Digital Twins.
"""
import os
import json
import logging
import threading
import paho.mqtt.client as mqtt
from queue import Queue

logger = logging.getLogger(__name__)

# A global queue to pass MQTT events to the Flask API routes (SSE streams)
telemetry_queue = Queue()

class MqttTelemetryService:
    def __init__(self):
        self.connected = False
        self.telemetry_cache = {}
        self.topic_callbacks = {}
        self._lock = threading.Lock()
        
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", "1883"))
        self.enabled = os.getenv("MQTT_ENABLED", "true").lower() == "true"
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_internal_message
        self._thread = None

    def start(self):
        """Start the background MQTT thread loop."""
        if not self.enabled:
            logger.info("MQTT Telemetry is disabled via ENV.")
            return

        logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}...")
        try:
            self.client.connect(self.broker, self.port, 60)
            self._thread = threading.Thread(target=self.client.loop_forever, daemon=True)
            self._thread.start()
        except Exception as e:
            logger.error(f"Failed to start MQTT thread: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info(f"Connected to MQTT broker {self.broker}")
            self.connected = True
            # Re-subscribe to all registered topics
            with self._lock:
                for topic in self.topic_callbacks.keys():
                    self.client.subscribe(topic)
                    logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {reason_code}")
            self.connected = False

    def subscribe(self, topic: str, callback):
        """Subscribe to a specific telemetry topic for a bounded 4D hyperobject."""
        with self._lock:
            if topic not in self.topic_callbacks:
                self.topic_callbacks[topic] = []
                if self.connected:
                    self.client.subscribe(topic)
                    logger.info(f"Subscribed to topic: {topic}")
            self.topic_callbacks[topic].append(callback)

    def _on_internal_message(self, client, userdata, msg):
        """Internal callback for incoming MQTT messages."""
        try:
            payload_str = msg.payload.decode('utf-8')
            topic = msg.topic
            
            # Simple topic matching, payload can be JSON or scalar
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                # If not JSON, try float/int wrapper
                try:
                    if '.' in payload_str:
                        payload = {"value": float(payload_str)}
                    else:
                        payload = {"value": int(payload_str)}
                except ValueError:
                    payload = {"value": payload_str}

            with self._lock:
                self.telemetry_cache[topic] = payload
                callbacks = self.topic_callbacks.get(topic, [])
            
            # Broadcast to internal callbacks
            for cb in callbacks:
                try:
                    cb(topic, payload)
                except Exception as e:
                    logger.error(f"Error in telemetry callback for {topic}: {e}")
            
            # Push payload to the global queue for the SSE routes
            telemetry_queue.put({"topic": topic, "payload": payload})

        except Exception as e:
            logger.error(f"Failed to process incoming MQTT payload: {e}")

    def get_latest_state(self, topic: str) -> dict:
        """Fetch the latest known temporal state for a given hyperobject part."""
        with self._lock:
            return self.telemetry_cache.get(topic, {})

    def inject_telemetry_to_params(self, base_params: dict, topic: str) -> dict:
        """
        Merge continuous MQTT telemetry into static manifest parameters.
        This provides the 'Phased' dimension to the hyperobject right before 
        the generic CadQuery/OpenSCAD compilation phase.
        """
        state = self.get_latest_state(topic)
        if not state:
            return base_params
            
        merged = base_params.copy()
        # Merge key-value pairs from telemetry state directly into the CAD parameters
        for key, value in state.items():
            param_key = f"telemetry_{key}"
            merged[param_key] = value
            
        return merged

# Singleton instance for the platform
telemetry_service = MqttTelemetryService()
