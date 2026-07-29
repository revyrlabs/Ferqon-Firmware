#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Device-level test: exercise refactored firmware commands on real hardware.

Tests the code paths touched by the refactor:
  - gpio.cpp   : pin_mode, gpio_read, gpio_write (ferqon_check_pin, REPLY_*)
  - adc.cpp    : adc_read (adc_check_channel, adc_raw_to_mv, wr_u16_le)
  - device_info: device_info (wr_u32_le in append_u32_tlv)
  - driver_call: hil.io_set, hil.io_get, hil.io_configure (REQUIRE_ARG, table dispatch)
  - debug.cpp  : set_debug_level (REPLY_INVALID_PARAMS)
  - protocol   : heartbeat parsing (wr_u32_le), DONE frames (memset removed)
"""
import json
import sys
import time
from pathlib import Path

# Add firmware tools to path
FIRMWARE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FIRMWARE_DIR / "tools"))

from ferqonfw.protocol import (
    START_BYTE, PKT_REQUEST, PKT_DONE, PKT_ERROR, PKT_HEARTBEAT, PKT_LOG,
    crc16_ccitt_false, encode_frame, FrameDecoder,
)
from ferqonfw.board_loader import get_ssot_dir

# Load command IDs from SSOT
def load_cmd_ids():
    ssot = get_ssot_dir()
    with open(ssot / "commands.json") as f:
        cmds = json.load(f)["commands"]
    return {name: meta["id"] for name, meta in cmds.items()}

import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
TIMEOUT_S = 3.0

def open_serial():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.5)  # let serial settle
    ser.reset_input_buffer()
    return ser

def send_and_recv(ser, cmd_id, payload, seq=1, expect_pkt=PKT_DONE,
                  no_pkt_request=False):
    """Send a framed request and wait for the response.

    The payload is the raw command params. PKT_REQUEST is prepended
    automatically unless no_pkt_request=True (for device_info/driver_info).
    Returns (pkt_type, body) where body includes the type byte as body[0].
    """
    if no_pkt_request:
        body = payload
    else:
        body = bytes([PKT_REQUEST]) + payload
    frame = encode_frame(seq, cmd_id, body)
    ser.write(frame)
    ser.flush()

    decoder = FrameDecoder()
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        chunk = ser.read(128)
        if not chunk:
            continue
        for r_seq, r_cmd, r_type, r_payload in decoder.feed(chunk):
            # Skip heartbeats and logs
            if r_type in (PKT_HEARTBEAT, PKT_LOG):
                continue
            if r_seq == seq and r_cmd == cmd_id:
                # r_payload already includes the type byte as [0]
                return r_type, r_payload
    return None, None

def test_ping(ser, ids):
    """Ping should return DONE with empty body."""
    rtype, body = send_and_recv(ser, ids["ping"], b"", expect_pkt=PKT_DONE)
    if rtype == PKT_DONE:
        print(f"  ping: PASS (DONE)")
        return True
    print(f"  ping: FAIL (type={rtype}, body={body})")
    return False

def test_echo(ser, ids):
    """Echo should return DONE with the same bytes."""
    msg = b"hello_ferqon"
    rtype, body = send_and_recv(ser, ids["echo"], msg, expect_pkt=PKT_DONE)
    if rtype == PKT_DONE and body[1:] == msg:
        print(f"  echo: PASS (echoed={body[1:].decode()})")
        return True
    print(f"  echo: FAIL (type={rtype}, body={body})")
    return False

def test_gpio_write_read(ser, ids):
    """GPIO write then read on the LED pin (pin 25 on Pico)."""
    pin = 25  # Pico onboard LED
    # Set pin mode to OUTPUT
    payload = bytes([pin, 1])  # pin=25, mode=OUTPUT(1)
    rtype, body = send_and_recv(ser, ids["pin_mode"], payload)
    if rtype != PKT_DONE:
        print(f"  gpio pin_mode: FAIL (type={rtype}, body={body})")
        return False

    # Write HIGH
    payload = bytes([pin, 1])  # pin=25, value=HIGH
    rtype, body = send_and_recv(ser, ids["gpio_write"], payload)
    if rtype != PKT_DONE:
        print(f"  gpio_write HIGH: FAIL (type={rtype}, body={body})")
        return False

    # Read back
    payload = bytes([pin])
    rtype, body = send_and_recv(ser, ids["gpio_read"], payload)
    if rtype == PKT_DONE and len(body) >= 2 and body[1] == 1:
        print(f"  gpio read/write: PASS (pin={pin} read=HIGH)")
        return True
    print(f"  gpio read: FAIL (type={rtype}, body={body})")
    return False

def test_gpio_invalid_pin(ser, ids):
    """GPIO read on invalid pin should return UNSUPPORTED_PIN error."""
    pin = 99  # invalid
    payload = bytes([pin])
    rtype, body = send_and_recv(ser, ids["gpio_read"], payload)
    if rtype == PKT_ERROR and len(body) >= 5 and body[1] == 4:  # code=4=UNSUPPORTED_PIN
        ctx = body[4]
        print(f"  gpio invalid pin: PASS (error code=4, ctx={ctx})")
        return True
    print(f"  gpio invalid pin: FAIL (type={rtype}, body={body})")
    return False

def test_adc_read(ser, ids):
    """ADC read on channel 0 should return DONE with u16 mV."""
    channel = 0
    payload = bytes([channel])
    rtype, body = send_and_recv(ser, ids["adc_read"], payload)
    if rtype == PKT_DONE and len(body) >= 3:
        mv = body[1] | (body[2] << 8)
        print(f"  adc_read ch0: PASS (mv={mv})")
        return True
    print(f"  adc_read ch0: FAIL (type={rtype}, body={body})")
    return False

def test_adc_invalid_channel(ser, ids):
    """ADC read on invalid channel should return UNSUPPORTED_PIN error."""
    channel = 99
    payload = bytes([channel])
    rtype, body = send_and_recv(ser, ids["adc_read"], payload)
    if rtype == PKT_ERROR and len(body) >= 5 and body[1] == 4:
        print(f"  adc invalid channel: PASS (error code=4, ctx={body[4]})")
        return True
    print(f"  adc invalid channel: FAIL (type={rtype}, body={body})")
    return False

def test_device_info(ser, ids):
    """Device info should return DONE with TLV data including firmware version."""
    rtype, body = send_and_recv(ser, ids["device_info"], b"", expect_pkt=PKT_DONE,
                                no_pkt_request=True)
    if rtype != PKT_DONE or not body:
        print(f"  device_info: FAIL (type={rtype}, body={body})")
        return False
    # Parse TLVs: [type][len][data...]
    i = 1  # skip PKT_DONE byte
    found_version = False
    found_name = False
    while i + 1 < len(body):
        tlv_type = body[i]
        tlv_len = body[i+1]
        if i + 2 + tlv_len > len(body):
            break
        tlv_data = body[i+2:i+2+tlv_len]
        if tlv_type == 3:  # TLV_FIRMWARE_VERSION
            ver = tlv_data.decode("utf-8", errors="replace")
            print(f"  device_info fw_version: {ver}")
            found_version = True
        elif tlv_type == 1:  # TLV_DEVICE_NAME
            name = tlv_data.decode("utf-8", errors="replace")
            print(f"  device_info name: {name}")
            found_name = True
        elif tlv_type == 7:  # TLV_UPTIME_MS (u32 LE — tests wr_u32_le)
            uptime = tlv_data[0] | (tlv_data[1]<<8) | (tlv_data[2]<<16) | (tlv_data[3]<<24)
            print(f"  device_info uptime: {uptime}ms")
        elif tlv_type == 6:  # TLV_FREE_RAM (u32 LE — tests wr_u32_le)
            ram = tlv_data[0] | (tlv_data[1]<<8) | (tlv_data[2]<<16) | (tlv_data[3]<<24)
            print(f"  device_info free_ram: {ram}")
        i += 2 + tlv_len
    if found_version and found_name:
        print(f"  device_info: PASS")
        return True
    print(f"  device_info: FAIL (missing TLVs, version={found_version}, name={found_name})")
    return False

def test_driver_call_hil_io(ser, ids):
    """Driver call: hil.io_set then hil.io_get on pin 25."""
    dc_id = ids["driver_call"]

    # Build driver_call payload: [driver_len][driver][method_len][method][args]
    driver = b"hil"
    method = b"io_set"
    args = b"pin=25;level=HIGH"
    payload = bytes([len(driver)]) + driver + bytes([len(method)]) + method + args
    rtype, body = send_and_recv(ser, dc_id, payload)
    # io_set returns DONE with no response data (just return true)
    if rtype != PKT_DONE:
        print(f"  hil.io_set: FAIL (type={rtype}, body={body})")
        return False

    # Now io_get — returns DONE with 1-byte response (the pin value)
    method = b"io_get"
    args = b"pin=25"
    payload = bytes([len(driver)]) + driver + bytes([len(method)]) + method + args
    rtype, body = send_and_recv(ser, dc_id, payload)
    if rtype == PKT_DONE and len(body) >= 2 and body[1] == 1:
        print(f"  hil.io_set/io_get: PASS (pin=25 read=HIGH)")
        return True
    print(f"  hil.io_get: FAIL (type={rtype}, body={body})")
    return False

def test_driver_call_hil_io_configure(ser, ids):
    """Driver call: hil.io_configure pin=25 mode=OUTPUT."""
    dc_id = ids["driver_call"]
    driver = b"hil"
    method = b"io_configure"
    args = b"pin=25;mode=OUTPUT"
    payload = bytes([len(driver)]) + driver + bytes([len(method)]) + method + args
    rtype, body = send_and_recv(ser, dc_id, payload)
    # io_configure returns DONE with no response data
    if rtype == PKT_DONE:
        print(f"  hil.io_configure: PASS")
        return True
    print(f"  hil.io_configure: FAIL (type={rtype}, body={body})")
    return False

def test_driver_call_missing_arg(ser, ids):
    """Driver call: hil.io_set without required 'level' arg → INVALID_PARAMS."""
    dc_id = ids["driver_call"]
    driver = b"hil"
    method = b"io_set"
    args = b"pin=25"  # missing level
    payload = bytes([len(driver)]) + driver + bytes([len(method)]) + method + args
    rtype, body = send_and_recv(ser, dc_id, payload)
    if rtype == PKT_ERROR and len(body) >= 5 and body[1] == 2:  # code=2=INVALID_PARAMS
        detail = body[5:].decode("utf-8", errors="replace") if len(body) > 5 else ""
        print(f"  hil.io_set missing arg: PASS (error code=2, detail='{detail}')")
        return True
    print(f"  hil.io_set missing arg: FAIL (type={rtype}, body={body})")
    return False

def test_driver_call_unknown_method(ser, ids):
    """Driver call: hil.nonexistent → INVALID_METHOD error."""
    dc_id = ids["driver_call"]
    driver = b"hil"
    method = b"nonexistent"
    args = b""
    payload = bytes([len(driver)]) + driver + bytes([len(method)]) + method + args
    rtype, body = send_and_recv(ser, dc_id, payload)
    # INVALID_METHOD is a custom error — check it's an error frame
    if rtype == PKT_ERROR:
        print(f"  hil.unknown_method: PASS (error code={body[1]})")
        return True
    print(f"  hil.unknown_method: FAIL (type={rtype}, body={body})")
    return False

def test_set_debug_level(ser, ids):
    """Set debug level to VERBOSE (2) — should return DONE."""
    payload = bytes([2])  # VERBOSE=2
    rtype, body = send_and_recv(ser, ids["set_debug_level"], payload)
    if rtype == PKT_DONE:
        print(f"  set_debug_level(VERBOSE): PASS")
        # Reset to INFO
        send_and_recv(ser, ids["set_debug_level"], bytes([1]))
        return True
    print(f"  set_debug_level: FAIL (type={rtype}, body={body})")
    return False

def test_heartbeat_received(ser, ids):
    """Listen for heartbeat frames — tests wr_u32_le in heartbeat path."""
    ser.reset_input_buffer()
    decoder = FrameDecoder()
    deadline = time.monotonic() + 12.0  # heartbeat interval is ~10s
    while time.monotonic() < deadline:
        chunk = ser.read(128)
        if not chunk:
            continue
        for r_seq, r_cmd, r_type, r_payload in decoder.feed(chunk):
            if r_type == PKT_HEARTBEAT and len(r_payload) >= 7:
                # r_payload includes type byte: [HEARTBEAT][state][u32 uptime][flags]
                state = r_payload[1]
                uptime = r_payload[2] | (r_payload[3]<<8) | (r_payload[4]<<16) | (r_payload[5]<<24)
                flags = r_payload[6]
                print(f"  heartbeat: PASS (state={state}, uptime={uptime}ms, flags={flags})")
                return True
    print(f"  heartbeat: FAIL (no heartbeat in 12s)")
    return False

def main():
    ids = load_cmd_ids()
    print(f"Connected to {PORT} at {BAUD} baud")
    print()

    ser = open_serial()

    tests = [
        ("Protocol basics", [
            ("ping", lambda: test_ping(ser, ids)),
            ("echo", lambda: test_echo(ser, ids)),
        ]),
        ("GPIO (gpio.cpp — ferqon_check_pin, REPLY macros)", [
            ("gpio write+read", lambda: test_gpio_write_read(ser, ids)),
            ("gpio invalid pin", lambda: test_gpio_invalid_pin(ser, ids)),
        ]),
        ("ADC (adc.cpp — adc_check_channel, adc_raw_to_mv, wr_u16_le)", [
            ("adc_read ch0", lambda: test_adc_read(ser, ids)),
            ("adc invalid channel", lambda: test_adc_invalid_channel(ser, ids)),
        ]),
        ("Device info (device_info.cpp — wr_u32_le in TLV)", [
            ("device_info TLVs", lambda: test_device_info(ser, ids)),
        ]),
        ("Driver call / HIL (driver_call.cpp — table dispatch, REQUIRE_ARG)", [
            ("hil.io_set + io_get", lambda: test_driver_call_hil_io(ser, ids)),
            ("hil.io_configure", lambda: test_driver_call_hil_io_configure(ser, ids)),
            ("hil missing arg", lambda: test_driver_call_missing_arg(ser, ids)),
            ("hil unknown method", lambda: test_driver_call_unknown_method(ser, ids)),
        ]),
        ("Debug (debug.cpp — REPLY_INVALID_PARAMS)", [
            ("set_debug_level", lambda: test_set_debug_level(ser, ids)),
        ]),
        ("Protocol (protocol.cpp — wr_u32_le heartbeat, memset removed)", [
            ("heartbeat received", lambda: test_heartbeat_received(ser, ids)),
        ]),
    ]

    total_pass = 0
    total_fail = 0
    for category, test_list in tests:
        print(f"--- {category} ---")
        for name, fn in test_list:
            if fn():
                total_pass += 1
            else:
                total_fail += 1
        print()

    print("=" * 60)
    print(f"DEVICE TEST SUMMARY: {total_pass}/{total_pass + total_fail} passed")
    print("=" * 60)

    ser.close()
    return 0 if total_fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
