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
from bleak import BleakClient, BleakScanner
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Argument parser for optional MAC address as argument 1
parser = argparse.ArgumentParser(description="BLE Scanner / Reader")
parser.add_argument(
    "mac",
    nargs="?",
    help="Target MAC address (optional, otherwise read from 'mac_addr' file)",
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
        f"{Fore.RED}Error: No MAC address provided as argument and the 'mac_addr' file"
        f" was not found.{Style.RESET_ALL}"
    )
    exit(1)

async def main():
  # An event triggered as soon as the device sends a signal
  device_spotted = asyncio.Event()

  def detection_callback(device, advertisement_data):
    if device.address.lower() == TARGET_MAC.lower():
      print(
          f"\n{Fore.GREEN}[!] Device {device.address} discovered! (RSSI:"
          f" {advertisement_data.rssi} dBm){Style.RESET_ALL}"
      )
      device_spotted.set()

  # 1. Start scanner in the background
  scanner = BleakScanner(detection_callback)
  await scanner.start()
  print(
      f"{Fore.CYAN}Listening for signals from {TARGET_MAC} (please turn on/activate the"
      f" device if necessary)...{Style.RESET_ALL}"
  )

  # Wait until the device sends a packet (timeout after 60 seconds)
  try:
    await asyncio.wait_for(device_spotted.wait(), timeout=60.0)
  except asyncio.TimeoutError:
    print(f"{Fore.YELLOW}Timeout: The device did not respond within 60 seconds.{Style.RESET_ALL}")
    await scanner.stop()
    return

  # 2. Stop scanner since we now need to connect exclusively
  await scanner.stop()
  print(f"{Fore.CYAN}Scanner stopped. Establishing GATT connection...{Style.RESET_ALL}")

  # 3. Establish connection to the device
  async with BleakClient(TARGET_MAC) as client:
    if client.is_connected:
      print(f"{Fore.GREEN}Successfully connected to {TARGET_MAC}!\n{Style.RESET_ALL}")

      # 4. Explore all services and characteristics
      print(f"{Fore.YELLOW}--- Available Data Channels (GATT Structure) ---{Style.RESET_ALL}")
      for service in client.services:
        print(f"{Fore.MAGENTA}[Service] {service.uuid} ({service.description}){Style.RESET_ALL}")
        for char in service.characteristics:
          print(f"  {Fore.CYAN}└─ [Characteristic] {char.uuid}{Style.RESET_ALL}")
          print(f"     Properties: {char.properties}")

          # If the value can be read, try to read it directly
          if "read" in char.properties:
            try:
              value = await client.read_gatt_char(char.uuid)
              print(f"     {Fore.GREEN}-> Value (Hex): {value.hex()} | Raw data: {value}{Style.RESET_ALL}")
            except Exception as e:
              print(f"     {Fore.RED}-> Could not read value: {e}{Style.RESET_ALL}")
      print(f"{Fore.YELLOW}---------------------------------------------{Style.RESET_ALL}")
    else:
      print(f"{Fore.RED}Connection could not be established.{Style.RESET_ALL}")


if __name__ == "__main__":
  asyncio.run(main())
