import time
import board
import adafruit_ahtx0
import json
import socket
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

i2c = board.I2C()
sensor = adafruit_ahtx0.AHTx0(i2c)

# MQTT configuration
MQTT_BROKER = "192.168.1.204"
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

def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9.0 / 5.0 + 32.0

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


def on_publish(client, userdata, mid):
    """MQTT on_publish handler (no properties for v5)."""
    # mid is the message id for the published message
    # keep this lightweight to avoid side effects
    # print(f"Published message id: {mid}")
    return


def on_message(client, userdata, msg):
    """MQTT on_message handler (message object used for both v3 and v5)."""
    # If you subscribe to topics later, this will be called.
    # Keep minimal to avoid interfering with main loop.
    print(f"Received message on {msg.topic}: {msg.payload!r}")


def safe_publish(client: mqtt.Client, topic: str, payload: str):
    try:
        client.publish(topic, payload)
    except Exception as e:
        print(f"MQTT publish error: {e}")
# ...existing code...
def main():
    client_id = f"aht20-{socket.gethostname()}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)

    # register callbacks using the MQTT v5-compatible signatures
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"Could not connect to MQTT broker {MQTT_BROKER}:{MQTT_PORT} - {e}")
        client = None
    else:
        client.loop_start()

    try:
        while True:
            c = sensor.temperature
            f = c_to_f(c)
            h = sensor.relative_humidity
            ts = int(time.time())
            print(f"T={c:.1f}°C/{f:.1f}°F  H={h:.1f}%")

            payload = json.dumps({
                "timestamp": ts,
                "temperature_c": round(c, 2),
                "temperature_f": round(f, 2),
                "humidity": round(h, 2)
            })

            if client is not None:
                safe_publish(client, MQTT_TOPIC, payload)

            time.sleep(2)
    except KeyboardInterrupt:
        print('\nExiting')
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()


if __name__ == "__main__":
    main()
