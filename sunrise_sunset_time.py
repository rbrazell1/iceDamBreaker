#!/usr/bin/env python3
"""
read_temp_mqtt.py
Reads DS18B20 via 1-Wire (preferred). If none found, reads ADS1115 A0.
Publishes JSON to MQTT broker.
"""

import time
import json
import os
import glob
import sys

import paho.mqtt.client as mqtt

# ---- CONFIG ----
MQTT_BROKER = "192.168.1.50"    # <--- change to your broker IP/hostname
MQTT_PORT = 1883
MQTT_USER = "piuser"            # or None
MQTT_PASS = "password"          # or None
MQTT_TOPIC = "ice_dam/temperature"  # topic to publish JSON messages
CLIENT_ID = "pi-zero2w-temp-01"

PUBLISH_INTERVAL = 5.0  # seconds

# If you want ADS1115 fallback, set USE_ADS1115 = True and ensure library installed
USE_ADS1115 = True

# ADS1115 options (if used)
ADS_CHANNEL = 0  # 0..3 -> A0..A3
ADS_GAIN = 1     # 1 = +/-4.096V (choose appropriately)
# ----------------

def read_ds18b20():
    """Return temperature in °C or None if no DS18B20 present."""
    base_dir = "/sys/bus/w1/devices/"
    # ds18b20 devices start with 28-
    devices = glob.glob(os.path.join(base_dir, "28-*"))
    if not devices:
        return None
    # pick first device
    devfile = os.path.join(devices[0], "w1_slave")
    try:
        with open(devfile, "r") as f:
            lines = f.readlines()
        # Example last line: "t=23125"
        if lines[0].strip()[-3:] != "YES":
            # sensor not ready; try again next time
            return None
        for line in lines:
            if "t=" in line:
                tstr = line.split("t=")[1].strip()
                temp_c = float(tstr) / 1000.0
                return temp_c
    except Exception:
        return None

# ADS1115 fallback
ads = None
ads_chan = None
def setup_ads1115():
    global ads, ads_chan
    try:
        import board
        import busio
        from adafruit_ads1x15.ads1115 import ADS1115
        from adafruit_ads1x15.analog_in import AnalogIn
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS1115(i2c)
        ads.gain = ADS_GAIN
        ads_chan = AnalogIn(ads, getattr(__import__("adafruit_ads1x15.ads1115", fromlist=["ADS"]).__dict__['ADS'], f"P{ADS_CHANNEL}"))
        return True
    except Exception as e:
        print("ADS1115 init failed:", e)
        return False

def read_ads1115_voltage():
    """Return tuple (voltage, raw) or None on failure"""
    global ads_chan
    if ads_chan is None:
        return None
    try:
        v = ads_chan.voltage
        raw = ads_chan.value
        return v, raw
    except Exception:
        return None

def mqtt_connect():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client

def main():
    # If using ds18b20 via 1-wire, ensure the kernel overlay is enabled on Pi:
    # dtoverlay=w1-gpio in /boot/config.txt (raspi-config -> Interfacing Options -> 1-Wire)
    # Try ADS1115 setup if configured
    if USE_ADS1115:
        ok = setup_ads1115()
        if not ok:
            print("ADS1115 not available; will only attempt DS18B20 readings.")

    client = mqtt_connect()
    print("Connected to MQTT broker", MQTT_BROKER)

    try:
        while True:
            timestamp = int(time.time())
            temp_c = read_ds18b20()
            payload = {"ts": timestamp}

            if temp_c is not None:
                payload.update({"sensor": "ds18b20", "temperature_c": round(temp_c, 3)})
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DS18B20: {temp_c:.3f} °C")
            else:
                # fallback to ADS1115 analog read
                if USE_ADS1115 and ads_chan is not None:
                    read = read_ads1115_voltage()
                    if read:
                        v, raw = read
                        payload.update({"sensor": "ads1115_a0", "voltage_v": round(v, 6), "raw": int(raw)})
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ADS1115 A0: {v:.6f} V (raw {raw})")
                    else:
                        payload.update({"sensor": "none", "error": "no_sensor"})
                        print("No sensor read")
                else:
                    payload.update({"sensor": "none", "error": "no_sensor"})
                    print("No sensor read")

            # publish as JSON
            try:
                client.publish(MQTT_TOPIC, json.dumps(payload), qos=0, retain=False)
            except Exception as e:
                print("MQTT publish error:", e)

            time.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()
