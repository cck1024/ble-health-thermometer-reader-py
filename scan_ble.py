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
import uuid

from bleak import BleakScanner
from colorama import Fore, Style, just_fix_windows_console


BLUETOOTH_BASE_UUID = "-0000-1000-8000-00805f9b34fb"


def format_bytes(value: bytes) -> str:
    return value.hex(" ")


def normalize_uuid(value: str) -> str:
    """Normalize full and short Bluetooth UUIDs to a common format."""
    value = value.strip().lower()

    if len(value) == 4:
        value = f"0000{value}{BLUETOOTH_BASE_UUID}"
    elif len(value) == 8:
        value = f"{value}{BLUETOOTH_BASE_UUID}"

    return str(uuid.UUID(value))


def parse_uuid_filter(value: str) -> set[str]:
    """Parse and validate a comma-separated list of UUIDs."""
    try:
        values = {normalize_uuid(item) for item in value.split(",") if item.strip()}
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"Invalid UUID: {error}") from error

    if not values:
        raise argparse.ArgumentTypeError("Provide at least one UUID.")

    return values


def print_device_details(device, advertisement_data, matching_uuids) -> None:
    name = advertisement_data.local_name or device.name or "Unknown"

    print(f"\n{Fore.GREEN}{Style.BRIGHT}NEW DEVICE{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Name:{Style.RESET_ALL} {name}")
    print(f"  {Fore.RED}MAC:{Style.RESET_ALL} {device.address}")
    print(
        f"  {Fore.CYAN}RSSI:{Style.RESET_ALL} "
        f"{advertisement_data.rssi} dBm"
    )

    if advertisement_data.tx_power is not None:
        print(
            f"  {Fore.CYAN}TX power:{Style.RESET_ALL} "
            f"{advertisement_data.tx_power} dBm"
        )

    if advertisement_data.service_uuids:
        print(f"  {Fore.CYAN}Service UUIDs:{Style.RESET_ALL}")
        for service_uuid in advertisement_data.service_uuids:
            if normalize_uuid(service_uuid) in matching_uuids:
                print(
                    f"    {Fore.GREEN}{Style.BRIGHT}{service_uuid}"
                    f"{Style.RESET_ALL}"
                )
            else:
                print(f"    {service_uuid}")

    if advertisement_data.manufacturer_data:
        print(f"  {Fore.CYAN}Manufacturer data:{Style.RESET_ALL}")
        for company_id, data in advertisement_data.manufacturer_data.items():
            print(f"    0x{company_id:04X}: {format_bytes(data)}")

    if advertisement_data.service_data:
        print(f"  {Fore.CYAN}Service data:{Style.RESET_ALL}")
        for service_uuid, data in advertisement_data.service_data.items():
            if normalize_uuid(service_uuid) in matching_uuids:
                print(
                    f"    {Fore.GREEN}{Style.BRIGHT}{service_uuid}"
                    f"{Style.RESET_ALL}: {format_bytes(data)}"
                )
            else:
                print(f"    {service_uuid}: {format_bytes(data)}")

    connectable = getattr(advertisement_data, "connectable", None)
    if connectable is not None:
        print(f"  {Fore.CYAN}Connectable:{Style.RESET_ALL} {connectable}")

    print(flush=True)


async def scan(
    duration: float,
    name_filter: str | None,
    uuid_filter: set[str] | None,
) -> None:
    devices = set()

    def on_advertisement(device, advertisement_data):
        name = advertisement_data.local_name or device.name or "Unknown"

        if name_filter and name_filter.casefold() not in name.casefold():
            return

        advertised_uuids = {
            normalize_uuid(service_uuid)
            for service_uuid in (advertisement_data.service_uuids or [])
        }
        advertised_uuids.update(
            normalize_uuid(service_uuid)
            for service_uuid in (advertisement_data.service_data or {})
        )

        matching_uuids = advertised_uuids & uuid_filter if uuid_filter else set()
        if uuid_filter and not matching_uuids:
            return

        if device.address in devices:
            return

        devices.add(device.address)
        print_device_details(device, advertisement_data, matching_uuids)

    print(
        f"{Fore.MAGENTA}Scanning for {duration:g} seconds...{Style.RESET_ALL}\n",
        flush=True,
    )

    async with BleakScanner(detection_callback=on_advertisement):
        await asyncio.sleep(duration)

    print(
        f"\n{Fore.MAGENTA}Scan complete. "
        f"Found {len(devices)} device(s).{Style.RESET_ALL}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live scan for Bluetooth LE devices.",
        add_help=False,
    )
    parser.add_argument(
        "seconds",
        nargs="?",
        type=float,
        default=10,
        help="Scan duration in seconds (default: 10).",
    )
    parser.add_argument(
        "-f",
        "--filter",
        metavar="NAME",
        help="Show devices whose name contains NAME (case-insensitive).",
    )
    parser.add_argument(
        "-u",
        "--uuid",
        type=parse_uuid_filter,
        metavar="UUID[,UUID...]",
        help="Show devices advertising at least one listed service UUID.",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help message and exit.",
    )

    args = parser.parse_args()

    if args.seconds <= 0:
        parser.error("seconds must be greater than zero")

    just_fix_windows_console()
    asyncio.run(scan(args.seconds, args.filter, args.uuid))


if __name__ == "__main__":
    main()
