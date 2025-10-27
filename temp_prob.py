import time
import os
import glob

W1_BASE = "/sys/bus/w1/devices"
SLEEP_SECONDS = 5

def list_ds18b20_ids():
    """Return list of DS18B20 device ids found on the w1 bus (e.g. ['28-00000xxxxxxx'])."""
    try:
        ids = [os.path.basename(p) for p in glob.glob(f"{W1_BASE}/28-*")]
        ids.sort()
        return ids
    except Exception:
        return []

def read_ds18b20_temp_c(sensor_id):
    """Read temperature in Celsius from a DS18B20 by id. Returns float or None."""
    path = f"{W1_BASE}/{sensor_id}/w1_slave"
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        if len(lines) < 2 or "YES" not in lines[0]:
            return None
        parts = lines[1].split("t=")
        if len(parts) != 2:
            return None
        temp_milli = int(parts[1].strip())
        return temp_milli / 1000.0
    except Exception:
        return None

def c_to_f(celsius: float) -> float:
    return celsius * 9.0 / 5.0 + 32.0

def main():
    ds_ids = list_ds18b20_ids()
    if not ds_ids:
        print("No DS18B20 sensors found on 1-Wire bus. Ensure w1-gpio and w1-therm are loaded and /boot/config.txt has dtoverlay=w1-gpio.")
        return

    print("Found DS18B20 sensors:", ", ".join(ds_ids))
    try:
        while True:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            for sid in ds_ids:
                temp_c = read_ds18b20_temp_c(sid)
                if temp_c is None:
                    print(f"[{ts}] {sid}: read failed")
                    continue
                temp_f = c_to_f(temp_c)
                print(f"[{ts}] {sid}: {temp_c:.3f}°C / {temp_f:.3f}°F")
            time.sleep(SLEEP_SECONDS)
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()