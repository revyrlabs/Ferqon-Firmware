"""Example HIL test: verify MCU connectivity.

This test pings the device, runs an echo round-trip, and queries
the driver list.  It demonstrates the HilSession API.
"""

from ferqon_hil.api import HilSession, Command, Expect


def run(session: HilSession):
    session.log("Starting connectivity test")

    mcu = session.connect()

    # 1. Ping
    session.log("Sending PING")
    resp = mcu.send(Command.PING())
    session.assert_true(resp.ok, "Ping response should be OK")
    session.assert_true(resp.ack, "Ping response should be ACKed")

    # 2. Echo round-trip
    session.log("Sending ECHO")
    resp = mcu.send(Command.ECHO("hello"))
    session.assert_eq(resp.message, "hello", "Echo should return same message")

    # 3. Driver info
    session.log("Querying driver info")
    resp = mcu.send(Command.DRIVER_INFO())
    session.assert_true(resp.ok, "Driver info should succeed")

    session.log("All connectivity checks complete")
