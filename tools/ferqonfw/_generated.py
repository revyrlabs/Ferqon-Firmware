# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
# Auto-generated from firmware/protocol/ssot/commands.json (v0.1.0).
# DO NOT EDIT -- regenerate with: python3 tools/gen_backend_commands.py
"""Generated Ferqon protocol constants and metadata."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

PROTOCOL_VERSION = "0.1.0"

# Frame layer
START_BYTE = 171
CRC_POLY = 4129
CRC_INIT = 65535
MAX_PAYLOAD_BYTES = 255
MAX_FRAME_BYTES = 261
INTER_BYTE_TIMEOUT_MS = 50
FRAME_ASSEMBLY_TIMEOUT_MS = 200
HEARTBEAT_INTERVAL_MS = 1000
FRAME_OVERHEAD = 6  # start + seq + cmd + len + crc_lo + crc_hi
SEQ_UNSOLICITED = 0

# Packet types
class PacketType(IntEnum):
    """Ferqon protocol packet types."""
    REQUEST = 1
    ACK = 2
    DONE = 3
    ERROR = 4
    HEARTBEAT = 5
    EVENT = 6
    LOG = 7

PKT_REQUEST = 1
PKT_ACK = 2
PKT_DONE = 3
PKT_ERROR = 4
PKT_HEARTBEAT = 5
PKT_EVENT = 6
PKT_LOG = 7
PACKET_TYPES = { "ACK": 2, "DONE": 3, "ERROR": 4, "EVENT": 6, "HEARTBEAT": 5, "LOG": 7, "REQUEST": 1 }

# Commands
class FerqonCommand(IntEnum):
    """Ferqon protocol command IDs."""
    PIN_MODE = 1
    DRIVER_INFO = 2
    DRIVER_CALL = 3
    ECHO = 8
    PING = 9
    RESET = 10
    DEVICE_INFO = 11
    CAPABILITIES = 12
    GPIO_READ = 16
    GPIO_WRITE = 17
    UART_SEND = 18
    UART_EXPECT = 19
    ADC_READ = 20
    ADC_EXPECT = 21
    PULSE_MEASURE = 22
    SET_DEBUG_LEVEL = 23

COMMANDS: dict[str, int] = {
    "pin_mode": 1,
    "driver_info": 2,
    "driver_call": 3,
    "echo": 8,
    "ping": 9,
    "reset": 10,
    "device_info": 11,
    "capabilities": 12,
    "gpio_read": 16,
    "gpio_write": 17,
    "uart_send": 18,
    "uart_expect": 19,
    "adc_read": 20,
    "adc_expect": 21,
    "pulse_measure": 22,
    "set_debug_level": 23,
}

CMD_PIN_MODE = 1
CMD_DRIVER_INFO = 2
CMD_DRIVER_CALL = 3
CMD_ECHO = 8
CMD_PING = 9
CMD_RESET = 10
CMD_DEVICE_INFO = 11
CMD_CAPABILITIES = 12
CMD_GPIO_READ = 16
CMD_GPIO_WRITE = 17
CMD_UART_SEND = 18
CMD_UART_EXPECT = 19
CMD_ADC_READ = 20
CMD_ADC_EXPECT = 21
CMD_PULSE_MEASURE = 22
CMD_SET_DEBUG_LEVEL = 23

COMMAND_PARAMS: dict[str, list[dict[str, Any]]] = {
    "pin_mode": [
        {"description": "Pin number (0\u2013max_gpio)", "name": "pin", "type": "u8"},
        {"description": "Mode ID (see pin_modes.json)", "name": "mode", "type": "u8"},
    ],
    "driver_call": [
        {"description": "Driver name (e.g., 'hil')", "name": "driver_name", "type": "string"},
        {"description": "Method name (e.g., 'io_set')", "name": "method", "type": "string"},
        {"description": "Semicolon-delimited key=value arguments", "name": "args", "type": "string"},
    ],
    "echo": [
        {"description": "Arbitrary bytes to echo back", "name": "payload", "type": "bytes"},
    ],
    "gpio_read": [
        {"description": "Pin number", "name": "pin", "type": "u8"},
    ],
    "gpio_write": [
        {"description": "Pin number", "name": "pin", "type": "u8"},
        {"description": "Pin value (0 or 1)", "name": "value", "type": "u8"},
    ],
    "uart_send": [
        {"description": "Data to send", "name": "data", "type": "bytes"},
    ],
    "uart_expect": [
        {"description": "Timeout in milliseconds", "name": "timeout_ms", "type": "u16"},
        {"description": "Pattern to match", "name": "pattern", "type": "string"},
    ],
    "adc_read": [
        {"description": "ADC channel number", "name": "channel", "type": "u8"},
    ],
    "adc_expect": [
        {"description": "Timeout in milliseconds", "name": "timeout_ms", "type": "u16"},
        {"description": "ADC channel number", "name": "channel", "type": "u8"},
        {"description": "Minimum voltage in mV", "name": "min_mv", "type": "u16"},
        {"description": "Maximum voltage in mV", "name": "max_mv", "type": "u16"},
    ],
    "pulse_measure": [
        {"description": "Timeout in milliseconds", "name": "timeout_ms", "type": "u16"},
        {"description": "Pin number", "name": "pin", "type": "u8"},
        {"description": "Minimum pulse width in microseconds", "name": "min_us", "type": "u32"},
        {"description": "Maximum pulse width in microseconds", "name": "max_us", "type": "u32"},
    ],
    "set_debug_level": [
        {"description": "Debug level (0=off, 1=info, 2=verbose)", "name": "level", "type": "u8"},
    ],
}

# GPIO modes
class GpioMode(IntEnum):
    """Ferqon GPIO pin modes."""
    INPUT = 0
    OUTPUT = 1
    INPUT_PULLUP = 2
    INPUT_PULLDOWN = 3

GPIO_MODES: dict[str, int] = { "INPUT": 0, "INPUT_PULLDOWN": 3, "INPUT_PULLUP": 2, "OUTPUT": 1 }
GPIO_MODE_INPUT = 0
GPIO_MODE_OUTPUT = 1
GPIO_MODE_INPUT_PULLUP = 2
GPIO_MODE_INPUT_PULLDOWN = 3

# Application states
class AppState(IntEnum):
    """Ferqon application state IDs."""
    APP_BOOT = 0
    APP_READY = 1
    APP_BUSY = 2
    APP_FAULT = 3
    APP_UPDATE = 4

APP_STATES: dict[str, int] = { "APP_BOOT": 0, "APP_BUSY": 2, "APP_FAULT": 3, "APP_READY": 1, "APP_UPDATE": 4 }
APP_STATE_APP_BOOT = 0
APP_STATE_APP_READY = 1
APP_STATE_APP_BUSY = 2
APP_STATE_APP_FAULT = 3
APP_STATE_APP_UPDATE = 4

# Error categories
class ErrorCategory(IntEnum):
    """Ferqon error category IDs."""
    NONE = 0
    PROTOCOL = 1
    COMMAND = 2
    DEVICE = 3
    INTERNAL = 4
    TIMEOUT = 5

ERROR_CATEGORIES: dict[str, int] = { "COMMAND": 2, "DEVICE": 3, "INTERNAL": 4, "NONE": 0, "PROTOCOL": 1, "TIMEOUT": 5 }
ERROR_CATEGORY_NONE = 0
ERROR_CATEGORY_PROTOCOL = 1
ERROR_CATEGORY_COMMAND = 2
ERROR_CATEGORY_DEVICE = 3
ERROR_CATEGORY_INTERNAL = 4
ERROR_CATEGORY_TIMEOUT = 5

# Error codes
class ErrorCode(IntEnum):
    """Ferqon protocol error codes."""
    OK = 0
    INVALID_COMMAND = 1
    INVALID_PARAMS = 2
    UNSUPPORTED_MODE = 3
    UNSUPPORTED_PIN = 4
    BUSY = 5
    INTERNAL = 6
    CHECKSUM_FAIL = 7
    PAYLOAD_TOO_LARGE = 9
    TIMEOUT = 10
    INVALID_DRIVER = 11
    INVALID_METHOD = 12
    NOT_IMPLEMENTED = 13

ERROR_CODES: dict[str, dict[str, Any]] = {
    "OK": {"category": "NONE", "code": 0, "description": "Success", "retryable": False},
    "INVALID_COMMAND": {"category": "COMMAND", "code": 1, "description": "Unknown command ID", "retryable": False},
    "INVALID_PARAMS": {"category": "PROTOCOL", "code": 2, "description": "Invalid parameters", "retryable": False},
    "UNSUPPORTED_MODE": {"category": "DEVICE", "code": 3, "description": "Unsupported mode", "retryable": False},
    "UNSUPPORTED_PIN": {"category": "DEVICE", "code": 4, "description": "Unsupported pin", "retryable": False},
    "BUSY": {"category": "DEVICE", "code": 5, "description": "Device busy", "retryable": True},
    "INTERNAL": {"category": "INTERNAL", "code": 6, "description": "Internal error", "retryable": False},
    "CHECKSUM_FAIL": {"category": "PROTOCOL", "code": 7, "description": "Checksum mismatch", "retryable": False},
    "PAYLOAD_TOO_LARGE": {"category": "PROTOCOL", "code": 9, "description": "Payload exceeds max size", "retryable": False},
    "TIMEOUT": {"category": "TIMEOUT", "code": 10, "description": "Operation timeout", "retryable": True},
    "INVALID_DRIVER": {"category": "COMMAND", "code": 11, "description": "No driver registered with that name", "retryable": False},
    "INVALID_METHOD": {"category": "COMMAND", "code": 12, "description": "Driver exists but method unknown", "retryable": False},
    "NOT_IMPLEMENTED": {"category": "COMMAND", "code": 13, "description": "Driver/method known but hardware not ready", "retryable": False},
}
ERR_OK = 0
ERR_INVALID_COMMAND = 1
ERR_INVALID_PARAMS = 2
ERR_UNSUPPORTED_MODE = 3
ERR_UNSUPPORTED_PIN = 4
ERR_BUSY = 5
ERR_INTERNAL = 6
ERR_CHECKSUM_FAIL = 7
ERR_PAYLOAD_TOO_LARGE = 9
ERR_TIMEOUT = 10
ERR_INVALID_DRIVER = 11
ERR_INVALID_METHOD = 12
ERR_NOT_IMPLEMENTED = 13

# TLV types
class TlvType(IntEnum):
    """Ferqon TLV tag IDs."""
    DEVICE_NAME = 1
    DRIVER = 1
    MCU_TYPE = 2
    COMMAND = 2
    FIRMWARE_VERSION = 3
    METHOD = 3
    PROTOCOL_VERSION = 4
    VERSION = 4
    BUILD_TIMESTAMP = 5
    FREE_RAM = 8
    UPTIME_MS = 9
    FERQON_SIGNATURE = 16

TLV_TYPES: dict[str, int] = { "BUILD_TIMESTAMP": 5, "COMMAND": 2, "DEVICE_NAME": 1, "DRIVER": 1, "FERQON_SIGNATURE": 16, "FIRMWARE_VERSION": 3, "FREE_RAM": 8, "MCU_TYPE": 2, "METHOD": 3, "PROTOCOL_VERSION": 4, "UPTIME_MS": 9, "VERSION": 4 }
TLV_DEVICE_NAME = 1
TLV_DRIVER = 1
TLV_MCU_TYPE = 2
TLV_COMMAND = 2
TLV_FIRMWARE_VERSION = 3
TLV_METHOD = 3
TLV_PROTOCOL_VERSION = 4
TLV_VERSION = 4
TLV_BUILD_TIMESTAMP = 5
TLV_FREE_RAM = 8
TLV_UPTIME_MS = 9
TLV_FERQON_SIGNATURE = 16

# IO actions
class IoAction(IntEnum):
    """Ferqon IO action IDs."""
    CONFIGURE = 0
    READ = 1
    WRITE = 2
    RELEASE = 3
    SET_TEST_MODE = 4

IO_ACTIONS: dict[str, int] = { "CONFIGURE": 0, "READ": 1, "RELEASE": 3, "SET_TEST_MODE": 4, "WRITE": 2 }
IO_ACTION_CONFIGURE = 0
IO_ACTION_READ = 1
IO_ACTION_WRITE = 2
IO_ACTION_RELEASE = 3
IO_ACTION_SET_TEST_MODE = 4

# Ferqon signature
FERQON_SIGNATURE_MAGIC = "FERQON"
FERQON_SIGNATURE_VENDOR = "revyrlabs"
FERQON_SIGNATURE_CAPABILITY_VERSION = 1
FERQON_SIGNATURE = { "capability_version": 1, "magic": "FERQON", "vendor": "revyrlabs" }

INFO_COMMAND_IDS: set[int] = {2, 11}

# Driver method map
DRIVER_METHOD_MAP: dict[tuple[str, str], dict[str, Any]] = {
    ("hil", "adc_expect"): {
        "native_cmd": "driver_call",
        "arg_map": {"channel": "u8", "max_mv": "u16_le", "min_mv": "u16_le", "timeout_ms": "u16_le"},
        "sub_handler": "adc_expect",
    },
    ("hil", "adc_read"): {
        "native_cmd": "adc_read",
        "arg_map": {"channel": "u8"},
    },
    ("hil", "enter"): {
        "native_cmd": "driver_call",
        "arg_map": {"uart_baud": "u32_optional", "uart_rx": "u8_optional", "uart_tx": "u8_optional"},
    },
    ("hil", "exit"): {
        "native_cmd": "driver_call",
        "arg_map": {},
    },
    ("hil", "io_configure"): {
        "native_cmd": "pin_mode",
        "arg_map": {"mode": "gpio_mode", "pin": "u8"},
    },
    ("hil", "io_expect"): {
        "native_cmd": "driver_call",
        "arg_map": {"level": "bool_high_low", "pin": "u8", "timeout_ms": "u16_le"},
        "sub_handler": "io_expect",
    },
    ("hil", "io_get"): {
        "native_cmd": "gpio_read",
        "arg_map": {"pin": "u8"},
    },
    ("hil", "io_set"): {
        "native_cmd": "gpio_write",
        "arg_map": {"level": "bool_high_low", "pin": "u8"},
    },
    ("hil", "pulse_measure"): {
        "native_cmd": "driver_call",
        "arg_map": {"max_us": "u32_le", "min_us": "u32_le", "pin": "u8", "timeout_ms": "u16_le"},
        "sub_handler": "pulse_measure",
    },
    ("hil", "uart_expect"): {
        "native_cmd": "uart_expect",
        "arg_map": {"pattern": "utf8_tail", "timeout_ms": "u16_le"},
    },
    ("hil", "uart_send"): {
        "native_cmd": "uart_send",
        "arg_map": {"data": "utf8_tail"},
    },
}

# Pinmap
PICO_PINMAP: dict[str, Any] = {
    "board": "Raspberry Pi Pico",
    "chip": "RP2040",
    "ground_pins": [3, 8, 13, 18, 23, 28, 38],
    "io_peripherals": {
        "ADC": 5,
        "GPIO": 0,
        "I2C": 2,
        "PWM": 4,
        "SPI": 1,
        "UART": 3,
    },
    "peripheral_constraints": {
        "ADC": {"channels": {
                "ADC0": 26,
                "ADC1": 27,
                "ADC2": 28,
                "ADC3_VSYS": None,
                "ADC4_TEMP": None,
            }},
        "I2C": {"I2C0": {
                "SCL": [1, 5, 9, 13, 17, 21],
                "SDA": [0, 4, 8, 12, 16, 20],
                "common_addresses": [80, 81, 104, 105],
                "default_pins": {"SCL": 5, "SDA": 4},
                "max_address": 127,
                "min_address": 0,
            }, "I2C1": {
                "SCL": [3, 7, 11, 15, 19, 23, 27],
                "SDA": [2, 6, 10, 14, 18, 22, 26],
                "common_addresses": [80, 81, 104, 105],
                "default_pins": {"SCL": 3, "SDA": 2},
                "max_address": 127,
                "min_address": 0,
            }},
        "PWM": {"notes": "8 slices \u00d7 2 channels (A/B). Each GPIO has a fixed PWM slice assignment: slice = gpio >> 1, channel = gpio & 1."},
        "SPI": {"SPI0": {
                "CS": [1, 5, 17, 21],
                "RX": [0, 4, 16, 20],
                "SCK": [2, 6, 18, 22],
                "TX": [3, 7, 19, 23],
                "addresses": [0, 1, 2, 3],
                "default_pins": {"CS": 5, "RX": 4, "SCK": 6, "TX": 7},
                "max_address": 3,
                "min_address": 0,
            }, "SPI1": {
                "CS": [9, 13],
                "RX": [8, 12, 28],
                "SCK": [10, 14, 26],
                "TX": [11, 15, 27],
                "addresses": [0, 1, 2, 3],
                "default_pins": {"CS": 9, "RX": 8, "SCK": 10, "TX": 11},
                "max_address": 3,
                "min_address": 0,
            }},
        "UART": {"UART0": {
                "CTS": [2, 14, 18],
                "RTS": [3, 15, 19],
                "RX": [1, 13, 17],
                "TX": [0, 12, 16],
                "default_pins": {"RX": 1, "TX": 0},
            }, "UART1": {
                "CTS": [6, 10, 22, 26],
                "RTS": [7, 11, 23, 27],
                "RX": [5, 9, 21],
                "TX": [4, 8, 20],
                "default_pins": {"RX": 5, "TX": 4},
            }},
    },
    "pins": {
        "GP0": {"adc": None, "capabilities": ["GPIO", "UART0_TX", "I2C0_SDA", "SPI0_RX", "PWM0A"], "gpio": 0, "physical": 1},
        "GP1": {"adc": None, "capabilities": ["GPIO", "UART0_RX", "I2C0_SCL", "SPI0_CS", "PWM0B"], "gpio": 1, "physical": 2},
        "GP10": {"adc": None, "capabilities": ["GPIO", "UART1_CTS", "I2C1_SDA", "SPI1_SCK", "PWM5A"], "gpio": 10, "physical": 14},
        "GP11": {"adc": None, "capabilities": ["GPIO", "UART1_RTS", "I2C1_SCL", "SPI1_TX", "PWM5B"], "gpio": 11, "physical": 15},
        "GP12": {"adc": None, "capabilities": ["GPIO", "UART0_TX", "I2C0_SDA", "SPI1_RX", "PWM6A"], "gpio": 12, "physical": 16},
        "GP13": {"adc": None, "capabilities": ["GPIO", "UART0_RX", "I2C0_SCL", "SPI1_CS", "PWM6B"], "gpio": 13, "physical": 17},
        "GP14": {"adc": None, "capabilities": ["GPIO", "UART0_CTS", "I2C1_SDA", "SPI1_SCK", "PWM7A"], "gpio": 14, "physical": 19},
        "GP15": {"adc": None, "capabilities": ["GPIO", "UART0_RTS", "I2C1_SCL", "SPI1_TX", "PWM7B"], "gpio": 15, "physical": 20},
        "GP16": {"adc": None, "capabilities": ["GPIO", "UART0_TX", "I2C0_SDA", "SPI0_RX", "PWM0A"], "gpio": 16, "physical": 21},
        "GP17": {"adc": None, "capabilities": ["GPIO", "UART0_RX", "I2C0_SCL", "SPI0_CS", "PWM0B"], "gpio": 17, "physical": 22},
        "GP18": {"adc": None, "capabilities": ["GPIO", "UART0_CTS", "I2C1_SDA", "SPI0_SCK", "PWM1A"], "gpio": 18, "physical": 24},
        "GP19": {"adc": None, "capabilities": ["GPIO", "UART0_RTS", "I2C1_SCL", "SPI0_TX", "PWM1B"], "gpio": 19, "physical": 25},
        "GP2": {"adc": None, "capabilities": ["GPIO", "UART0_CTS", "I2C1_SDA", "SPI0_SCK", "PWM1A"], "gpio": 2, "physical": 4},
        "GP20": {"adc": None, "capabilities": ["GPIO", "UART1_TX", "I2C0_SDA", "SPI0_RX", "PWM2A"], "gpio": 20, "physical": 26},
        "GP21": {"adc": None, "capabilities": ["GPIO", "UART1_RX", "I2C0_SCL", "SPI0_CS", "PWM2B"], "gpio": 21, "physical": 27},
        "GP22": {"adc": None, "capabilities": ["GPIO", "UART1_CTS", "I2C1_SDA", "SPI0_SCK", "PWM3A"], "gpio": 22, "physical": 29},
        "GP25": {
            "adc": None,
            "capabilities": ["GPIO", "PWM4B"],
            "gpio": 25,
            "note": "Onboard LED",
            "physical": None,
        },
        "GP26": {"adc": 0, "capabilities": ["GPIO", "UART1_CTS", "I2C1_SDA", "SPI1_SCK", "PWM5A", "ADC0"], "gpio": 26, "physical": 31},
        "GP27": {"adc": 1, "capabilities": ["GPIO", "UART1_RTS", "I2C1_SCL", "SPI1_TX", "PWM5B", "ADC1"], "gpio": 27, "physical": 32},
        "GP28": {"adc": 2, "capabilities": ["GPIO", "UART0_TX", "I2C0_SDA", "SPI1_RX", "PWM6A", "ADC2"], "gpio": 28, "physical": 34},
        "GP3": {"adc": None, "capabilities": ["GPIO", "UART0_RTS", "I2C1_SCL", "SPI0_TX", "PWM1B"], "gpio": 3, "physical": 5},
        "GP4": {"adc": None, "capabilities": ["GPIO", "UART1_TX", "I2C0_SDA", "SPI0_RX", "PWM2A"], "gpio": 4, "physical": 6},
        "GP5": {"adc": None, "capabilities": ["GPIO", "UART1_RX", "I2C0_SCL", "SPI0_CS", "PWM2B"], "gpio": 5, "physical": 7},
        "GP6": {"adc": None, "capabilities": ["GPIO", "UART1_CTS", "I2C1_SDA", "SPI0_SCK", "PWM3A"], "gpio": 6, "physical": 9},
        "GP7": {"adc": None, "capabilities": ["GPIO", "UART1_RTS", "I2C1_SCL", "SPI0_TX", "PWM3B"], "gpio": 7, "physical": 10},
        "GP8": {"adc": None, "capabilities": ["GPIO", "UART1_TX", "I2C0_SDA", "SPI1_RX", "PWM4A"], "gpio": 8, "physical": 11},
        "GP9": {"adc": None, "capabilities": ["GPIO", "UART1_RX", "I2C0_SCL", "SPI1_CS", "PWM4B"], "gpio": 9, "physical": 12},
    },
    "power_pins": {
        "3V3": {"description": "3.3 V output (300 mA max)", "physical": 36},
        "3V3_EN": {"description": "Enable pin for 3.3 V regulator", "physical": 37},
        "ADC_VREF": {"description": "ADC reference voltage", "physical": 35},
        "AGND": {"description": "Analog ground", "physical": 33},
        "VBUS": {"description": "USB 5 V (when powered via USB)", "physical": 40},
        "VSYS": {"description": "System input voltage (1.8 V \u2013 5.5 V)", "physical": 39},
    },
    "total_gpio": 30,
}
TOTAL_GPIO = 30

__all__ = [
    "PROTOCOL_VERSION",
    "START_BYTE",
    "CRC_POLY",
    "CRC_INIT",
    "MAX_PAYLOAD_BYTES",
    "MAX_FRAME_BYTES",
    "INTER_BYTE_TIMEOUT_MS",
    "FRAME_ASSEMBLY_TIMEOUT_MS",
    "HEARTBEAT_INTERVAL_MS",
    "FRAME_OVERHEAD",
    "SEQ_UNSOLICITED",
    "PacketType",
    "PACKET_TYPES",
    "PKT_REQUEST",
    "PKT_ACK",
    "PKT_DONE",
    "PKT_ERROR",
    "PKT_HEARTBEAT",
    "PKT_EVENT",
    "PKT_LOG",
    "FerqonCommand",
    "COMMANDS",
    "CMD_PIN_MODE",
    "CMD_DRIVER_INFO",
    "CMD_DRIVER_CALL",
    "CMD_ECHO",
    "CMD_PING",
    "CMD_RESET",
    "CMD_DEVICE_INFO",
    "CMD_CAPABILITIES",
    "CMD_GPIO_READ",
    "CMD_GPIO_WRITE",
    "CMD_UART_SEND",
    "CMD_UART_EXPECT",
    "CMD_ADC_READ",
    "CMD_ADC_EXPECT",
    "CMD_PULSE_MEASURE",
    "CMD_SET_DEBUG_LEVEL",
    "COMMAND_PARAMS",
    "GpioMode",
    "GPIO_MODES",
    "GPIO_MODE_INPUT",
    "GPIO_MODE_OUTPUT",
    "GPIO_MODE_INPUT_PULLUP",
    "GPIO_MODE_INPUT_PULLDOWN",
    "AppState",
    "APP_STATES",
    "APP_STATE_APP_BOOT",
    "APP_STATE_APP_READY",
    "APP_STATE_APP_BUSY",
    "APP_STATE_APP_FAULT",
    "APP_STATE_APP_UPDATE",
    "ErrorCategory",
    "ERROR_CATEGORIES",
    "ERROR_CATEGORY_NONE",
    "ERROR_CATEGORY_PROTOCOL",
    "ERROR_CATEGORY_COMMAND",
    "ERROR_CATEGORY_DEVICE",
    "ERROR_CATEGORY_INTERNAL",
    "ERROR_CATEGORY_TIMEOUT",
    "ErrorCode",
    "ERROR_CODES",
    "ERR_OK",
    "ERR_INVALID_COMMAND",
    "ERR_INVALID_PARAMS",
    "ERR_UNSUPPORTED_MODE",
    "ERR_UNSUPPORTED_PIN",
    "ERR_BUSY",
    "ERR_INTERNAL",
    "ERR_CHECKSUM_FAIL",
    "ERR_PAYLOAD_TOO_LARGE",
    "ERR_TIMEOUT",
    "ERR_INVALID_DRIVER",
    "ERR_INVALID_METHOD",
    "ERR_NOT_IMPLEMENTED",
    "TlvType",
    "TLV_TYPES",
    "TLV_DEVICE_NAME",
    "TLV_DRIVER",
    "TLV_MCU_TYPE",
    "TLV_COMMAND",
    "TLV_FIRMWARE_VERSION",
    "TLV_METHOD",
    "TLV_PROTOCOL_VERSION",
    "TLV_VERSION",
    "TLV_BUILD_TIMESTAMP",
    "TLV_FREE_RAM",
    "TLV_UPTIME_MS",
    "TLV_FERQON_SIGNATURE",
    "IoAction",
    "IO_ACTIONS",
    "IO_ACTION_CONFIGURE",
    "IO_ACTION_READ",
    "IO_ACTION_WRITE",
    "IO_ACTION_RELEASE",
    "IO_ACTION_SET_TEST_MODE",
    "FERQON_SIGNATURE_MAGIC",
    "FERQON_SIGNATURE_VENDOR",
    "FERQON_SIGNATURE_CAPABILITY_VERSION",
    "FERQON_SIGNATURE",
    "INFO_COMMAND_IDS",
    "DRIVER_METHOD_MAP",
    "PICO_PINMAP",
    "TOTAL_GPIO",
]

