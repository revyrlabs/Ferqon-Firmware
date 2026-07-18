# Protocol

Ferqon devices speak a framed binary protocol over a serial byte stream.

## Frame Format

Each frame consists of a start byte, sequence number, command ID, payload length, payload, and a CRC:

- **START** is always `0xAB`.
- **SEQ** is echoed back in replies; `0` is used for unsolicited frames.
- **CMD** is a command ID defined in the generated protocol constants header.
- **LEN** is the number of payload bytes (0 to 255).
- **Payload** is command-specific; see the PKT_REQUEST requirement below.
- **CRC** is CRC-16/CCITT-FALSE computed over SEQ, CMD, LEN, and payload, stored little-endian (low byte first).

## Multi-byte Integer Encoding

All multi-byte integer fields in the protocol — both in command payloads and responses — are encoded **little-endian** (least significant byte first). This applies to heartbeat uptime, ADC values and timeouts, pulse durations and timeouts, and UART timeouts.

## Packet Types

The first payload byte for request/response frames is the packet type:

| Type | Value | Meaning |
|------|-------|---------|
| REQUEST | 0x01 | Client request |
| ACK | 0x02 | Acknowledgement |
| DONE | 0x03 | Successful response |
| ERROR | 0x04 | Structured error |
| HEARTBEAT | 0x05 | Unsolicited heartbeat |
| EVENT | 0x06 | Unsolicited event |
| LOG | 0x07 | Unsolicited log message |

### PKT_REQUEST Requirement

The dispatcher **requires** the first payload byte to be `PKT_REQUEST` (0x01)
for all commands **except** `DEVICE_INFO` and `DRIVER_INFO`. If the
`PKT_REQUEST` byte is missing, the dispatcher rejects the frame with
`INVALID_PARAMS` before any driver is called.

For the two exempt commands (`DEVICE_INFO` and `DRIVER_INFO`), the payload
may be empty (zero bytes) — no packet-type prefix is needed.

After the dispatcher strips the `PKT_REQUEST` byte, the remaining bytes are
passed to the driver handler as the `params` array. Drivers should never
see the `PKT_REQUEST` byte — it is consumed by the dispatcher.

**Example — PING (requires PKT_REQUEST):**
```
Payload: [0x01]           → params passed to driver: (empty)
```

**Example — GPIO_WRITE (requires PKT_REQUEST):**
```
Payload: [0x01, pin, value] → params passed to driver: [pin, value]
```

**Example — DEVICE_INFO (exempt, no PKT_REQUEST):**
```
Payload: (empty)          → params passed to driver: (empty)
```

## Heartbeat

The device emits a periodic heartbeat containing the current application state, millisecond uptime (32-bit little-endian), and reserved flags. The heartbeat interval is configured at build time via `tools/production_config.json` (default 5000 ms) and can be overridden with the `FERQON_HEARTBEAT_INTERVAL_MS` environment variable.

## Error Frame

Error frames contain an error code, category, retryable flag, command-specific context, and optional human-readable detail. Error codes and categories are defined in the generated protocol constants header.

## Blocking Commands

The following commands block the main loop for up to `timeout_ms` and do not process other commands or send heartbeats during that time: `ADC_EXPECT`, `UART_EXPECT`, `PULSE_MEASURE`, and `DRIVER_CALL` with the `hil.io_expect` method. Keep timeouts short for interactive use.

## UART Driver

`UART_SEND` and `UART_EXPECT` operate on `Serial1` — a secondary hardware UART — not the control serial port. This prevents user data from corrupting the control protocol stream. All currently supported production and in-development boards define `FERQON_HAS_SERIAL1` and expose a secondary UART. The `#ifndef FERQON_HAS_SERIAL1` fallback path returns `FERQON_ERR_NOT_IMPLEMENTED` but is unreachable on any currently configured board; it exists as a safety net for future boards that may lack a second UART.

## Parser

The parser is a state machine that supports inter-byte timeout for resynchronization, frame-assembly timeout for incomplete frames, and CRC validation. It is defined in the portable core's protocol module.
