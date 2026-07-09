# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs
"""Simple HIL test: basic echo communication verification.

This is the simplest test to verify MCU communication works.
Server sends ECHO command, MCU echoes back the message.
"""

from ferqon_hil.api import HilSession, Command


def run(session: HilSession):
    session.log("Starting simple echo test")

    # Connect to MCU
    mcu = session.connect()

    # Send echo command with test message
    session.log("Sending ECHO command with message: 'test'")
    resp = mcu.send(Command.ECHO("test"))

    # Verify response
    session.assert_eq(resp.message, "test", "Echo should return the same message")

    session.log("Echo test passed - communication works!")
    session.cleanup()