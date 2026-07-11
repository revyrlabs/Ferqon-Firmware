# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Example HIL test: full GPIO + UART + ADC verification.

Architecture: SERVER → MCU (slave tester) → DUT

This test exercises the complete HIL command set:
  - IO_SET / IO_GET / IO_CONFIGURE    GPIO drive + read
  - Expect.pin                        MCU-side GPIO level wait
  - UART_SEND / Expect.uart           DUT UART round-trip
  - ADC_READ / Expect.voltage         Analogue voltage measurement
  - Expect.pulse_ms                   Pulse width measurement

Flow overview
-------------
  Step 1  Enter HIL mode 
  Step 2  Configure MCU GPIO as output, drive DUT reset pin LOW
  Step 3  Release DUT reset (HIGH) — MCU waits for DUT ready pin to go HIGH
  Step 4  DUT UART handshake — MCU sends "READY?" and expects "OK" back
  Step 5  Read supply voltage via ADC — MCU validates 3.0–3.6 V
  Step 6  Measure PWM pulse from DUT — MCU times one pulse on GPIO 10
  Step 7  Verify DUT LED GPIO state
  Step 8  Exit HIL mode

Wiring
------
  MCU GPIO 2  → DUT RESET (active LOW)
  MCU GPIO 3  ← DUT READY (HIGH when booted)
  MCU GPIO 4  (UART1 TX) → DUT RX
  MCU GPIO 5  (UART1 RX) ← DUT TX
  MCU GPIO 10 ← DUT PWM output
  MCU GPIO 26 (ADC0)     ← DUT 3.3 V supply rail
  MCU GPIO 6  ← DUT LED output pin

Run with:
    ferqon hil run example_full_hil_test --port /dev/ttyACM0
"""

from ferqon_hil.api import HilSession, Command, Expect


def run(session: HilSession) -> None:
    session.log("=== Full HIL test: GPIO + UART + ADC + Pulse ===")

    mcu = session.connect()

    # ------------------------------------------------------------------
    # Step 1: Enter HIL mode — initialise DUT UART on UART1
    # ------------------------------------------------------------------
    session.log("Step 1: Entering HIL mode")
    resp = mcu.send(Command.HIL_ENTER(uart_tx_pin=4, uart_rx_pin=5, uart_baud=115200))
    session.assert_true(resp.ok, "HIL enter")

    try:
        # ------------------------------------------------------------------
        # Step 2: Assert DUT RESET (pull GPIO 2 LOW)
        # ------------------------------------------------------------------
        session.log("Step 2: Asserting DUT RESET (GPIO 2 LOW)")
        resp = mcu.send(Command.IO_SET("D2", "LOW"))
        session.assert_true(resp.ok, "Drive RESET LOW")
        session.sleep(0.05)  # hold reset for 50 ms

        # ------------------------------------------------------------------
        # Step 3: Release DUT RESET — wait for DUT READY pin (GPIO 3) to go HIGH
        #         MCU polls GPIO 3 in real time; server blocks on the response.
        # ------------------------------------------------------------------
        session.log("Step 3: Releasing RESET, waiting for DUT READY (GPIO 3 HIGH)")
        resp = mcu.send(Command.IO_SET("D2", "HIGH"))
        session.assert_true(resp.ok, "Release RESET HIGH")

        # MCU-side: poll GPIO 3 for up to 500 ms
        mcu.expect(Expect.pin("D3", "HIGH"), timeout=0.5)
        session.assert_true(True, "DUT READY pin went HIGH")

        # ------------------------------------------------------------------
        # Step 4: UART handshake — MCU sends "READY?" and waits for "OK"
        # ------------------------------------------------------------------
        session.log('Step 4: UART handshake — sending "READY?"')
        resp = mcu.send(Command.UART_SEND("READY?"))
        session.assert_true(resp.ok, "Send READY? to DUT")

        # MCU waits on UART1 RX for "OK" for up to 1 s
        mcu.expect(Expect.uart("OK"), timeout=1.0)
        session.assert_true(True, "DUT responded OK")

        # ------------------------------------------------------------------
        # Step 5: ADC voltage check — MCU reads GPIO 26 (ADC channel 0)
        #         and validates that the DUT 3.3 V rail is in [3.0, 3.6] V
        # ------------------------------------------------------------------
        session.log("Step 5: Checking DUT 3.3 V supply (ADC ch0, GPIO 26)")

        # Direct read (value logged for diagnostics)
        resp = mcu.send(Command.ADC_READ(channel=0))
        session.assert_true(resp.ok, "ADC read succeeded")
        session.log(f"  ADC result: {resp.message}")

        # Range validation on the MCU — returns FAIL if out of bounds
        mcu.expect(Expect.voltage(3.0, 3.6, channel=0), timeout=0.1)
        session.assert_true(True, "3.3 V rail in [3.0, 3.6] V")

        # ------------------------------------------------------------------
        # Step 6: Pulse width measurement — DUT PWM output on GPIO 10
        #         Expect 1 kHz square wave → 500 µs half-period →
        #         full pulse width ≈ 1 000 µs = 1.0 ms.  Accept [0.8, 1.2] ms.
        # ------------------------------------------------------------------
        session.log("Step 6: Measuring DUT PWM pulse on GPIO 10")
        mcu.expect(Expect.pulse_ms(0.8, 1.2, pin="D10"), timeout=0.5)
        session.assert_true(True, "DUT PWM pulse in [0.8, 1.2] ms")

        # ------------------------------------------------------------------
        # Step 7: Verify DUT LED GPIO state (MCU reads GPIO 6)
        # ------------------------------------------------------------------
        session.log("Step 7: Reading DUT LED pin (GPIO 6)")
        resp = mcu.send(Command.IO_GET("D6"))
        session.assert_true(resp.ok, "IO_GET GPIO 6 succeeded")
        session.log(f"  LED state: {resp.message}")
        # LED should be HIGH (DUT blinks LED on boot)
        session.assert_true("HIGH" in resp.message, "DUT LED is HIGH after boot")

        session.log("=== All HIL checks passed ===")

    except Exception as exc:
        session.log(f"Test error: {exc}", level="error")
        session._errors += 1
    finally:
        # ------------------------------------------------------------------
        # Step 8: Exit HIL mode
        # ------------------------------------------------------------------
        session.log("Step 8: Exiting HIL mode")
        mcu.send(Command.HIL_EXIT())
        session.cleanup()