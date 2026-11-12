#
# OpenTemp: Connect to a Health Thermometer using Bluetooth LE without proprietary Apps
# Copyright (C) 2026 by cck1024
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import argparse
import asyncio
import datetime
import struct
from bleak import BleakClient, BleakScanner

# Argument parser for optional MAC address and export flag
parser = argparse.ArgumentParser(
    description="BLE Health Thermometer Reader & Exporter"
)
parser.add_argument(
    "mac",
    nargs="?",
    help="Target MAC address (optional, otherwise read from 'mac_addr' file)",
)
parser.add_argument(
    "--export",
    action="store_true",
    help="Export measurements to a timestamped text file",
)
args = parser.parse_args()

if args.mac:
  TARGET_MAC = args.mac
else:
  try:
    with open("mac_addr", "r") as file:
      TARGET_MAC = file.read().strip()
  except FileNotFoundError:
    print(
        "Error: No MAC address provided as argument and the 'mac_addr' file"
        " was not found."
    )
    exit(1)

THERMOMETER_MEASUREMENT_UUID = "00002a1c-0000-1000-8000-00805f9b34fb"


def parse_health_thermometer_data(data):
  """Parses the IEEE-11073 32-bit floating point number of the Health

  Thermometer Profile.
  """
  if len(data) < 5:
    return None, "Too few data"

  flags = data[0]
  unit_fahrenheit = bool(flags & 0x01)  # Bit 0: 0 = Celsius, 1 = Fahrenheit

  # The next 4 bytes are the IEEE-11073 Float
  raw_val = struct.unpack("<I", data[1:5])[0]

  # Mantissa (lower 24 bits, signed)
  mantissa = raw_val & 0x00FFFFFF
  if mantissa & 0x800000:
    mantissa -= 0x1000000

  # Exponent (upper 8 bits, signed)
  exponent = (raw_val >> 24) & 0xFF
  if exponent & 0x80:
    exponent -= 0x100

  temperature = mantissa * (10 ** exponent)
  unit = "°F" if unit_fahrenheit else "°C"
  return temperature, unit


async def main():
  device_spotted = asyncio.Event()

  def detection_callback(device, advertisement_data):
    if device.address.lower() == TARGET_MAC.lower():
      print(f"[!] Device discovered! RSSI: {advertisement_data.rssi} dBm")
      device_spotted.set()

  scanner = BleakScanner(detection_callback)
  await scanner.start()
  print("Waiting for the thermometer (turn it on or start a measurement)...")

  try:
    await asyncio.wait_for(device_spotted.wait(), timeout=60.0)
  except asyncio.TimeoutError:
    print("Timeout: Thermometer not found within 60 seconds.")
    await scanner.stop()
    return

  await scanner.stop()

  print("Connecting to the thermometer...")
  async with BleakClient(TARGET_MAC) as client:
    if not client.is_connected:
      print("Connection failed.")
      return

    print("Connected! Enabling notifications for temperature data...\n")

    queue = asyncio.Queue()

    # Callback triggered when the thermometer sends data
    def handle_indication(sender, data):
      temp, unit = parse_health_thermometer_data(data)
      if temp is not None:
        queue.put_nowait((temp, unit, data))

    # Subscribe to indications
    await client.start_notify(THERMOMETER_MEASUREMENT_UUID, handle_indication)

    print(
        "Listening for measurements... (Will automatically stop 5 seconds after"
        " the last measurement)"
    )

    measurements = []
    recorded_unit = "°C"

    try:
      # Wait indefinitely for the FIRST measurement to arrive
      temp, unit, data = await queue.get()
      recorded_unit = unit
      measurements.append(temp)
      print(
          f">>> NEW TEMPERATURE MEASUREMENT: {temp:.2f} {unit} (RAW:"
          f" {data.hex()})"
      )

      # Subsequent measurements: timeout starts fresh with each new item (5 seconds inactivity)
      while True:
        temp, unit, data = await asyncio.wait_for(queue.get(), timeout=5.0)
        measurements.append(temp)
        print(
            f">>> NEW TEMPERATURE MEASUREMENT: {temp:.2f} {unit} (RAW:"
            f" {data.hex()})"
        )

    except asyncio.TimeoutError:
      print(
          "\n[i] No new measurements received for 5 seconds. Finishing session..."
      )
    except asyncio.CancelledError:
      pass
    finally:
      # Safely attempt to stop notifications without throwing tracebacks if disconnected/cached out
      try:
        if client.is_connected:
          await client.stop_notify(THERMOMETER_MEASUREMENT_UUID)
      except Exception:
        pass

    # Export measurements if flag was provided
    if args.export and measurements:
      timestamp_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
      filename = f"measurements_{timestamp_str}.txt"
      unit_name = "Celsius" if recorded_unit == "°C" else "Fahrenheit"

      try:
        with open(filename, "w") as f:
          f.write(f"{unit_name}\n")
          for m in measurements:
            f.write(f"{m:.2f}\n")
        print(f"Measurements successfully exported to '{filename}'.")
      except Exception as e:
        print(f"Error writing export file: {e}")


if __name__ == "__main__":
  asyncio.run(main())
