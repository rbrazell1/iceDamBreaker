import warnings
import time
import board
import adafruit_ahtx0
import json
import socket
import paho.mqtt.client as mqtt

# silence paho-mqtt DeprecationWarning from older callback API (if present)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="paho.mqtt.client")

# try to import RPi.GPIO; provide a safe fallback when not on a Raspberry Pi
try:
    import RPi.GPIO as GPIO
except Exception:
    class _FakeGPIO:
        BCM = 'BCM'
        OUT = 'OUT'
        HIGH = 1
        LOW = 0
        def setmode(self, m): pass
        def setup(self, pin, mode, initial=None): pass
        def output(self, pin, val): pass
        def cleanup(self): pass
    GPIO = _FakeGPIO()

i2c = board.I2C()
sensor = adafruit_ahtx0.AHTx0(i2c)


def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9.0 / 5.0 + 32.0



# MQTT configuration
MQTT_BROKER = "192.168.1.202"
MQTT_PORT = 1883
MQTT_TOPIC = "sensors/aht20"


# Relay configuration - BCM pin numbers; adjust to match your wiring
RELAY_PINS = [17, 27, 22, 23]  # channels 1..4 -> GPIO pins
GPIO.setmode(GPIO.BCM)
# Set to GPIO.LOW if your relay board is active-low
RELAY_ACTIVE = GPIO.HIGH
RELAY_INACTIVE = GPIO.LOW if RELAY_ACTIVE == GPIO.HIGH else GPIO.HIGH
for p in RELAY_PINS:
    GPIO.setup(p, GPIO.OUT, initial=RELAY_INACTIVE)


def _relay_on(index: int) -> None:
    """Turn on relay channel by index 0..3."""
    GPIO.output(RELAY_PINS[index], RELAY_ACTIVE)


def _relay_off(index: int) -> None:
    """Turn off relay channel by index 0..3."""
    GPIO.output(RELAY_PINS[index], RELAY_INACTIVE)


def set_relays_for_temp(temp_f: float) -> None:
    """Control relays: channels 1&2 when temp > 72.5F, channels 3&4 when temp <= 72.5F."""
    if temp_f > 72.5:
        # Turn on relays 1 & 2, turn off 3 & 4
        _relay_on(0)
        _relay_on(1)
        _relay_off(2)
        _relay_off(3)
    else:
        # Turn on relays 3 & 4, turn off 1 & 2
        _relay_off(0)
        _relay_off(1)
        _relay_on(2)
        _relay_on(3)


def on_connect(client, userdata, flags, rc, properties=None):
    """MQTT on_connect handler.

    Accepts an optional `properties` argument (MQTT v5) so the callback works
    whether the client is using MQTT v3.1.1 or MQTT v5.
    """
    if rc == 0:
        print(f"Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"Failed to connect to MQTT broker, rc={rc}")


def on_disconnect(client, userdata, rc, properties=None):
    """MQTT on_disconnect handler compatible with MQTT v5 callback signature."""
    print(f"Disconnected from MQTT broker (rc={rc})")


def on_publish(client, userdata, mid, properties=None):
    """MQTT on_publish handler compatible with MQTT v5 signature."""
    # keep this lightweight
    return


def on_message(client, userdata, msg):
    """MQTT on_message handler (message object used for both v3 and v5)."""
    print(f"Received message on {msg.topic}: {msg.payload!r}")


def safe_publish(client: mqtt.Client, topic: str, payload: str):
    try:
        client.publish(topic, payload)
    except Exception as e:
        print(f"MQTT publish error: {e}")
def main():
    client_id = f"aht20-{socket.gethostname()}"