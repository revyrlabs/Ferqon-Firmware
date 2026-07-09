# Protocol

Ferqon devices speak a framed binary protocol over a serial byte stream.

## Frame Format

```
[START=0xAB] [SEQ] [CMD] [LEN] [payload...] [CRC_LO] [CRC_HI]
```

- `START` is always `0xAB`.
- `SEQ` is echoed back in replies; `0` is used for unsolicited frames.
- `CMD` is a command ID from `src/ferqon_commands.h`.
- `LEN` is the number of payload bytes (0 to `FERQON_MAX_PAYLOAD_BYTES`).
- Payload is command-specific; the first byte is usually a packet type.
- CRC-16/CCITT-FALSE is computed over `SEQ`, `CMD`, `LEN`, and `payload`.

## Packet Types

The first payload byte for request/response frames is the packet type:

| Type | Value | Meaning |
|------|-------|---------|
| REQUEST | 0x01 | Client request |
| DONE | 0x02 | Successful response |
| ACK | 0x03 | Acknowledgement |
| ERROR | 0x04 | Structured error |
| HEARTBEAT | 0x05 | Unsolicited heartbeat |
| EVENT | 0x06 | Unsolicited event |
| LOG | 0x07 | Unsolicited log message |

## Heartbeat

The device emits a periodic heartbeat:

```
[HEARTBEAT] [state] [uptime_lo] [uptime_mid_lo] [uptime_mid_hi] [uptime_hi] [flags]
```

- `state` is the current application state from `app_state_get()`.
- `uptime` is the millisecond uptime as a 32-bit little-endian value.
- `flags` is reserved for future error condition flags.

## Error Frame

```
[ERROR] [code] [category] [retryable] [ctx] [detail...]
```

- `code` is a `FERQON_ERR_*` value.
- `category` is a `FERQON_ECAT_*` value.
- `retryable` is `1` if the caller may retry the same command.
- `ctx` is command-specific context.
- `detail` is optional human-readable or structured data.

## Parser

The parser is implemented as a state machine in `src/protocol.cpp`. It supports:

- Inter-byte timeout for resynchronization.
- Frame-assembly timeout for incomplete frames.
- CRC validation.

## Log Framing

Text logs are sent with packet type `LOG` followed by a null-terminated UTF-8 string. Structured binary logs use `LOG` with a subtype byte after the type.
