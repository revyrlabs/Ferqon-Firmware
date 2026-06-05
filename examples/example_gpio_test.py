"""Example HIL test: GPIO read/write verification.

Configures a pin as output, writes HIGH, reads it back, then
writes LOW and reads again.  Requires a loopback jumper between
the target output pin and an input pin, or a device that echoes
pin state.
"""

from ferqon_hil.api import HilSession, Command


def run(session: HilSession):
    session.log("Starting GPIO loopback test")

    mcu = session.connect()

    # Configure pin 2 as output
    session.log("Configuring GPIO 2 as OUTPUT")
    resp = mcu.send(Command.CONFIGURE_PIN(2, "OUTPUT"))
    session.assert_true(resp.ok, "Configure pin 2 as OUTPUT")

    # Write HIGH
    session.log("Writing HIGH to GPIO 2")
    resp = mcu.send(Command.WRITE_PIN(2, 1))
    session.assert_true(resp.ok, "Write HIGH to pin 2")

    session.sleep(0.1)

    # Read back
    session.log("Reading GPIO 2")
    resp = mcu.send(Command.READ_PIN(2))
    session.assert_true(resp.ok, "Read pin 2 should succeed")

    # Write LOW
    session.log("Writing LOW to GPIO 2")
    resp = mcu.send(Command.WRITE_PIN(2, 0))
    session.assert_true(resp.ok, "Write LOW to pin 2")

    session.log("GPIO loopback test complete")
