# Architecture

Ferqon firmware is designed as a portable command processor that can run on many MCUs with minimal platform-specific code.

## Layout

```
src/                       Portable core code
  protocol.cpp             Frame parsing, CRC, response emission
  dispatcher.cpp           Command dispatch to registered drivers
  ping.cpp / echo.cpp      Command handlers (one per driver)
  gpio.cpp / adc.cpp       Hardware-agnostic driver implementations
  app_state.cpp            Runtime state and last-error tracking
  ferqon_log.cpp           Debug logging

platforms/<device>/        Board-specific implementation
  board.yml                Single source of truth for capabilities
  generated/               Auto-generated headers from board.yml
  <device>_io.cpp          Hardware access, gated by capability macros
  <device>_backend.cpp     Vtable registration

generated/                 Build-time generated artifacts (ignored by git)
```

## Invariants

1. `src/` builds on the `native` environment with stub platform ops.
2. Every hardware access in `platforms/` goes through `ferqon_cap_*()` helpers.
3. `board.yml` is the single source of truth; `generated/` is produced by `tools/gen_platform_caps.py`.

## Data Flow

```
Serial/UART bytes → protocol parser → dispatcher → driver handler → platform IO
```

The protocol layer is frame-based:

```
[START=0xAB] [SEQ] [CMD] [LEN] [payload...] [CRC_LO] [CRC_HI]
```

See [protocol.md](protocol.md) for full protocol details.
