# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_info.py
-----------
Info command for ferqonfw CLI - show platform capabilities.
"""

import json
from pathlib import Path

from ferqonfw.board_loader import load_board


def _get_caps_data(platform: str) -> dict:
    """Load capabilities from generated JSON or board YAML."""
    board_data = load_board(platform)
    firmware_dir = Path(__file__).resolve().parent.parent.parent

    # Prefer generated capabilities JSON if available.
    caps_path = (
        firmware_dir / "platforms" / platform / "generated" / "capabilities.json"
    )
    if not caps_path.exists():
        in_dev = (
            firmware_dir
            / "platforms"
            / "in_development"
            / platform
            / "generated"
            / "capabilities.json"
        )
        if in_dev.exists():
            caps_path = in_dev

    if caps_path.exists():
        with open(caps_path, encoding="utf-8") as f:
            return json.load(f)

    if board_data:
        return {
            "mcu": board_data.get("mcu", "unknown"),
            "device_name": board_data.get("device_name", platform),
            "protocol_version": board_data.get("protocol_version", "unknown"),
            "firmware_version": board_data.get("firmware_version", "unknown"),
            "max_gpio": board_data.get("max_gpio", "unknown"),
            "reserved_pins": board_data.get("reserved_pins", []),
            "peripherals": board_data.get("peripherals", {}),
        }

    return {}


def cmd_info(args) -> int:
    """Show platform capabilities."""
    platform = args.platform
    caps_data = _get_caps_data(platform)

    if not caps_data:
        print(f"Error: no capabilities found for platform '{platform}'")
        return 1

    print(f"MCU: {caps_data.get('mcu', 'unknown')}")
    print(f"Device: {caps_data.get('device_name', 'unknown')}")
    print(f"Protocol version: {caps_data.get('protocol_version', 'unknown')}")
    print(f"Firmware version: {caps_data.get('firmware_version', 'unknown')}")
    print(f"Max GPIO: {caps_data.get('max_gpio', 'unknown')}")
    print(f"Reserved pins: {caps_data.get('reserved_pins', [])}")

    peripherals = caps_data.get("peripherals", {})

    # UART
    uart = peripherals.get("uart", [])
    if uart:
        print(f"\nUART: {len(uart)} instance(s)")
        for inst in uart:
            print(f"  Instance {inst['instance']}: TX {inst['tx']}, RX {inst['rx']}")

    # SPI
    spi = peripherals.get("spi", [])
    if spi:
        print(f"\nSPI: {len(spi)} instance(s)")
        for inst in spi:
            print(
                f"  Instance {inst['instance']}: SCK {inst['sck']}, "
                f"MOSI {inst['mosi']}, MISO {inst['miso']}, CS {inst['cs']}"
            )

    # I2C
    i2c = peripherals.get("i2c", [])
    if i2c:
        print(f"\nI2C: {len(i2c)} instance(s)")
        for inst in i2c:
            print(
                f"  Instance {inst['instance']}: SDA {inst['sda']}, SCL {inst['scl']}"
            )

    # ADC
    adc = peripherals.get("adc", {})
    if adc:
        print(
            f"\nADC: {adc.get('resolution', 'unknown')}-bit, "
            f"{adc.get('vref_mv', 'unknown')}mV"
        )
        print(f"  Channels: {adc.get('channels', [])}")

    # PWM
    pwm = peripherals.get("pwm", {})
    if pwm:
        print(f"\nPWM: {pwm.get('channels', 'unknown')} channels")
        pins = pwm.get("pins", [])
        if pins:
            print(f"  Pins: {len(pins)} pin(s) (0-{max(pins)})")

    return 0
