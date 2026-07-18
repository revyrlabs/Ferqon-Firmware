<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs -->

# Roadmap

This document outlines the planned direction for Ferqon Firmware. It is
a living document — items may be reprioritized based on community feedback
and contributor interest.

## Current State (v1.1.0)

- Serial protocol with CRC-16/CCITT-FALSE framing
- Command dispatcher with sealed source allowlist
- Production platforms: RP2040 (Pico), ESP32, ESP32-S3, Teensy 4.0/4.1
- Community platforms (in development): Mega 2560, ESP8266, STM32 Blue Pill
- Drivers: ping, echo, GPIO, ADC, UART, pulse, reset, device_info,
  driver_info, capabilities, debug
- Generated capability headers from `board.yml`
- `ferqonfw` CLI (production) and `ferqonfw-dev` CLI (development)
- In-process emulator for no-hardware testing
- Native unit tests (Unity framework)
- DCO + SPDX/REUSE compliance

## Near-Term Goals

- **Platform abstraction layer (PAL):** Decouple the portable core from
  Arduino-specific APIs to support non-Arduino backends (e.g., Pico SDK
  bare-metal, Zephyr).
- **STM32 production support:** Promote STM32 Blue Pill and STM32F4/F7
  from in-development to production.
- **Expanded test coverage:** More round-trip tests binding CLI frame
  builders to emulator dispatch semantics; HIL test automation.
- **I2C and SPI drivers:** Add I2C_READ, I2C_WRITE, SPI_TRANSFER commands
  for sensor and peripheral integration.

## Medium-Term Goals

- **OTA update mechanism:** Signed firmware update over serial or
  network, with Ed25519 signature verification.
- **Networking support (ESP32/Pico-W):** WiFi, MQTT, and TLS for
  network-connected deployments.
- **Provisioning flows:** SoftAP and BLE first-boot provisioning for
  field deployment.
- **Async UART_EXPECT:** Non-blocking variant of UART_EXPECT that
  continues processing commands and heartbeats during the wait.

## Long-Term Goals

- **Multi-transport support:** Allow the control protocol to run over
  USB CDC, hardware UART, or network (TCP/TLS) without code changes.
- **Formal protocol specification:** Machine-readable protocol schema
  with automatic conformance testing.
- **Community platform contributions:** Streamline the process for
  community members to add and maintain new board support.

## How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow and
[MAINTAINERS.md](MAINTAINERS.md) for the current maintainer team. Open
a GitHub issue to discuss any roadmap item before starting work.
