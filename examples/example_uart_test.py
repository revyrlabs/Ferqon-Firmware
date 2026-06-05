"""Example HIL test: DUT UART echo verification.

Architecture: SERVER → MCU (slave tester) → DUT

Flow
----
1. Server sends HIL_ENTER  → MCU initialises UART1 for DUT communication.
2. Server sends UART_SEND  → MCU transmits "Hello world!" to DUT over UART1.
3. Server sends Expect.uart → MCU waits on UART1 for DUT echo, returns PASS/FAIL.
4. Server sends HIL_EXIT   → MCU releases UART1.

The server never reads DUT bytes directly — all real-time DUT communication
and response matching is done by the MCU.

Wiring
------
  MCU GPIO 4  (UART1 TX)  →  DUT RX
  MCU GPIO 5  (UART1 RX)  ←  DUT TX

DUT firmware requirement: echo every received byte back on its TX pin.

Run with:
    ferqon hil run example_uart_test --port /dev/ttyACM0
"""

from ferqon_hil.api import HilSession, Command, Expect


def run(session: HilSession) -> None:
    session.log("=== UART echo test: SERVER → MCU → DUT ===")

    mcu = session.connect()

    # ------------------------------------------------------------------
    # 1. Enter HIL mode — MCU initialises UART1 toward the DUT.
    #    GPIO 4 = MCU TX → DUT RX
    #    GPIO 5 = MCU RX ← DUT TX
    # ------------------------------------------------------------------
    session.log("Entering HIL mode (DUT UART: TX=GPIO4, RX=GPIO5, 115200 baud)")
    resp = mcu.send(Command.HIL_ENTER(uart_tx_pin=4, uart_rx_pin=5, uart_baud=115200))
    session.assert_true(resp.ok, "HIL enter should succeed")

    try:
        # ------------------------------------------------------------------
        # 2. Ping the MCU — verify the control link is alive.
        # ------------------------------------------------------------------
        session.log("Pinging MCU")
        resp = mcu.send(Command.PING())
        session.assert_true(resp.ok, "MCU ping should succeed")

        # ------------------------------------------------------------------
        # 3. Send "Hello world!" to DUT via MCU UART1.
        #    The server sends UART_SEND; the MCU transmits each byte to the DUT.
        # ------------------------------------------------------------------
        message = "Hello world!"
        session.log(f'Sending to DUT: "{message}"')
        resp = mcu.send(Command.UART_SEND(message))
        session.assert_true(resp.ok, "UART send to DUT should succeed")

        # ------------------------------------------------------------------
        # 4. Wait for DUT echo — MCU polls UART1 RX until it sees the pattern.
        #    The MCU does the real-time waiting; the server blocks on the
        #    serial response only.
        # ------------------------------------------------------------------
        session.log(f'Waiting for DUT echo: "{message}" (timeout 1.0 s)')
        mcu.expect(Expect.uart(message), timeout=1.0)
        session.assert_true(True, f'DUT echoed "{message}"')

        # ------------------------------------------------------------------
        # 5. Second round-trip with a different message.
        # ------------------------------------------------------------------
        message2 = "HIL OK"
        session.log(f'Sending to DUT: "{message2}"')
        resp = mcu.send(Command.UART_SEND(message2))
        session.assert_true(resp.ok, "Second UART send should succeed")

        session.log(f'Waiting for DUT echo: "{message2}" (timeout 0.5 s)')
        mcu.expect(Expect.uart(message2), timeout=0.5)
        session.assert_true(True, f'DUT echoed "{message2}"')

    except Exception as exc:
        session.log(f"Test error: {exc}", level="error")
        session._errors += 1
    finally:
        # ------------------------------------------------------------------
        # 6. Exit HIL mode — MCU releases UART1.
        # ------------------------------------------------------------------
        session.log("Exiting HIL mode")
        mcu.send(Command.HIL_EXIT())
        session.cleanup()
