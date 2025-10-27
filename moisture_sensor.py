#!/usr/bin/env python3
# Read ADS1115 A0/A1, average samples, convert to percent with simple linear calibration.

import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# --- CONFIG ---
SAMPLE_COUNT = 10
SAMPLE_DELAY = 0.03    # seconds between samples
ADS_GAIN = 1           # 1 => +/-4.096V range (ok for 3.3V signals)
A0_CAL_DRY = 23000     # replace after calibration (raw or voltage based)
A0_CAL_WET = 11000
A1_CAL_DRY = 31000
A1_CAL_WET = 12000
# ----------------

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
ads.gain = ADS_GAIN

chan0 = AnalogIn(ads, 0)
chan1 = AnalogIn(ads, 1)

def read_avg(channel, count=SAMPLE_COUNT, delay=SAMPLE_DELAY):
    total = 0
    for _ in range(count):
        total += channel.value   # raw ADC counts (0..32767 typically)
        time.sleep(delay)
    return total / count

def raw_to_percent(raw, dry, wet):
    # clamp and scale: dry -> 0%, wet -> 100%
    if dry == wet:
        return 0.0
    # If wet produces smaller raw counts, handle that direction
    if dry > wet:
        pct = (dry - raw) / (dry - wet) * 100.0
    else:
        pct = (raw - dry) / (wet - dry) * 100.0
    return max(0.0, min(100.0, pct))

if __name__ == "__main__":
    print("Starting ADS1115 moisture read (Ctrl-C to stop)")
    try:
        while True:
            r0 = read_avg(chan0)
            # r1 = read_avg(chan1)
            v0 = chan0.voltage
            # v1 = chan1.voltage

            p0 = raw_to_percent(r0, A0_CAL_DRY, A0_CAL_WET)
            # p1 = raw_to_percent(r1, A1_CAL_DRY, A1_CAL_WET)

            print(f"A0 raw={int(r0)} volt={v0:.4f} V pct={p0:.1f}% | ")
                #   f"A1 raw={int(r1)} volt={v1:.4f} V pct={p1:.1f}%")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Exit")