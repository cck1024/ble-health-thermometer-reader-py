# OpenTemp: Connect to a Health Thermometer using Bluetooth LE without proprietary Apps

This guide will show you how to **connect** to a health thermometer **and read** its temperature measurements on any computer (Windows, Linux, MacOS) via *Bluetooth Low Energy* (LE) using Python. It has been tested with a *Beurer FT95* and may or may not work with other devices.

## TL;DR:

1. Find your device's MAC address and create a file named `mac_addr`.
2. Take a measurement with your thermometer (make sure the Bluetooth symbol is visible and not turned off).
3. Start `read_temp.py --export` to see all measurements and save them to a file.

## Relevant UUIDs

### 📂 Service UUID:

```sh
00001809-0000-1000-8000-00805f9b34fb
```

### 🔑 Characteristic UUID:

```sh
00002a1c-0000-1000-8000-00805f9b34fb
```

## Provided Scripts

This repository contains 3 Python scripts. To use them, you need Python 3.

### Requirements:

First create a virtual environment and enter it, then install the requirements: 

```bash
$ python3 -m venv .venv # create a venv
$ source .venv/bin/activate # enter the venv
(.venv) $ python3 -m pip install bleak colorama # install the requirements
```

##### Note: All 3 Scripts have a help page: `<script> -h`

## Schematic:

Scan for Bluetooth LE devices -> Filter by Service UUID -> Connect to device to explore -> Find out Characteristic UUID -> Connect to device again using characteristic UUID -> Receive all measurements

## 1. scan_ble.py: Find your Device's MAC Address

```bash
$ source .venv/bin/activate # enter the venv, if you're not in it yet
(.venv) $ python3 scan_ble.py
```

If you have a *Beurer FT95* for example, you can use the flag `-f` to filter for its name:

While scanning **TURN ON** the device and start a temperature scan. The device is only discoverable while scanning.

```bash
(.venv) $ python3 scan_ble.py 20 -f ft95
Scanning for 20 seconds...


NEW DEVICE
  Name: FT95
  MAC: FF:00:00:XX:XX:XX
  RSSI: -72 dBm
  Service UUIDs:
    00001800-0000-1000-8000-00805f9b34fb
    00001801-0000-1000-8000-00805f9b34fb
    00001809-0000-1000-8000-00805f9b34fb # <- This is the Service UUID your device needs to be able to communicate with the PC
    0000180a-0000-1000-8000-00805f9b34fb
    0000180f-0000-1000-8000-00805f9b34fb
  Manufacturer data:
    0x0611: 01


Scan complete. Found 1 device(s).
```

Now that we know the MAC address of the device, we create a plain text file named mac_addr to save it:

```bash
$ echo "FF:00:00:XX:XX:XX" > mac_addr
```

## 2. list_gatt_services.py: Finding the characteristic UUID

This step is optional, but interesting to discover every service your device provides.

```bash
(.venv) $ python3 list_gatt_services.py 
Listening for signals from FF:00:00:XX:XX:XX (please turn on/activate the device if necessary)...

[!] Device FF:00:00:XX:XX:XX discovered! (RSSI: -65 dBm)
Scanner stopped. Establishing GATT connection...
Successfully connected to FF:00:00:XX:XX:XX!

--- Available Data Channels (GATT Structure) ---
...
[Service] 00001809-0000-1000-8000-00805f9b34fb (Health Thermometer)
  └─ [Characteristic] 00002a21-0000-1000-8000-00805f9b34fb
     Properties: ['read']
     -> Value (Hex): 0000 | Raw data: bytearray(b'\x00\x00')
  └─ [Characteristic] 00002a1c-0000-1000-8000-00805f9b34fb # <- This is the characteristic UUID we are searching for!
     Properties: ['indicate']
...
```

## 3. read_temp.py: Actually Reading the Measurements

Turn ON your Thermometer, take a measurement, and then start the script. 

```bash
(.venv) $ python3 read_temp.py 
Waiting for the thermometer (turn it on or start a measurement)...
[!] Device discovered! RSSI: -66 dBm
Connecting to the thermometer...
Connected! Enabling notifications for temperature data...

Listening for measurements... (Will automatically stop 5 seconds after the last measurement)
>>> NEW TEMPERATURE MEASUREMENT: 36.10 °C (RAW: 06690100ffe207010101000c02)
...
>>> NEW TEMPERATURE MEASUREMENT: 36.40 °C (RAW: 066c0100ffe207011b03301c02)

[i] No new measurements received for 5 seconds. Finishing session...
```

The *Beurer FT95* can save up to 60 measurements, your current measurement is the last one received.

To store the measurements, use the `--export` flag. It will create a file in your current working directory.

```bash
$ python3 read_temp.py --export
[!] Device discovered! RSSI: -73 dBm
Waiting for the thermometer (turn it on or start a measurement)...
Connecting to the thermometer...
Connected! Enabling notifications for temperature data...

Listening for measurements... (Will automatically stop 5 seconds after the last measurement)
>>> NEW TEMPERATURE MEASUREMENT: 36.10 °C (RAW: 06690100ffe207010f01213302) # oldest measurement
... # up to 58 other measurements
>>> NEW TEMPERATURE MEASUREMENT: 36.40 °C (RAW: 066c0100ffe207011b03340402) # current measurement

[i] No new measurements received for 5 seconds. Finishing session...
Measurements successfully exported to 'measurements_2026-11-10T20:20:27.txt'.
```

##### Note: Whether it displays values in Fahrenheit or Celsius is determined by your thermometer's own settings.


