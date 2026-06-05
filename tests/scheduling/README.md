# Scheduling Layer Unit Tests

Native host tests for `core/scheduling/`. No hardware required.

## Test suites

| Environment | File | What it tests |
|---|---|---|
| `native_ringbuf` | `test_ringbuf.c` | `ferqon_ringbuf.h` — push/pop, wrap-around, full/empty edge cases |
| `native_multicore` | `test_sched_multicore.c` | `ferqon_sched_multicore.c` — SPSC queue submit/dispatch, drop-when-full |
| `native_singlecore` | `test_sched_singlecore.c` | `ferqon_sched_singlecore.c` — ISR ring buffer → frame parser → dispatch |

## Running

```bash
cd firmware

# Ring buffer only
pio test -e native_ringbuf

# Multicore queue
pio test -e native_multicore

# Single-core ISR path
pio test -e native_singlecore

# All three at once
pio test -e native_ringbuf -e native_multicore -e native_singlecore
```

## How it works

- **`native_ringbuf`** — header-only, no stubs needed. Tests the raw byte ring buffer in isolation.
- **`native_multicore`** — compiles `ferqon_sched_multicore.c` with `FERQON_SCHED_MULTICORE=1` and `FERQON_SCHED_QUEUE_DEPTH=8`. Uses `--wrap=FERQON_Drivers_HandleRequest` to spy on dispatch calls.
- **`native_singlecore`** — compiles `ferqon_sched_singlecore.c` with `FERQON_SCHED_UART_ISR=1`. Wraps both `FERQON_Protocol_FrameFeedByte` (to control when frames complete) and `FERQON_Drivers_HandleRequest` (to count dispatches).

Protocol/driver symbols that are not under test are satisfied by `stubs.c`.
