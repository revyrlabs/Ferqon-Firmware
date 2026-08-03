/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * host_main.cpp
 * -----------
 * Desktop host entry point for the Ferqon firmware SIL build.
 *
 * This file is the only source that is unique to the native target. It
 * provides the standard C main() function that the Arduino framework
 * normally supplies on microcontrollers, then drives the firmware's
 * setup()/loop() functions.
 *
 * The control UART (Serial) is exposed as a TCP server on localhost so
 * that Python or other host tools can connect and speak the same binary
 * protocol that would be used over a physical USB/serial link.
 */
#include "Arduino.h"

#include <csignal>
#include <cstdlib>
#include <cstring>
#include <iostream>

/* Defined in src/main.cpp (C linkage so the same binary works with the
 * Arduino framework's weak main() on microcontrollers). */
extern "C" {
    extern void setup(void);
    extern void loop(void);
}

static void usage(const char *prog) {
    std::cerr << "Usage: " << prog << " [PORT]" << std::endl;
    std::cerr << "If PORT is omitted, FERQON_SIL_PORT or " << FERQON_SIL_DEFAULT_PORT << " is used." << std::endl;
}

int main(int argc, char *argv[]) {
    /* Ignore SIGPIPE so a disconnected TCP client does not kill the process. */
    std::signal(SIGPIPE, SIG_IGN);

    uint16_t port = 0;
    if (argc > 1) {
        if (std::strcmp(argv[1], "-h") == 0 || std::strcmp(argv[1], "--help") == 0) {
            usage(argv[0]);
            return 0;
        }
        port = static_cast<uint16_t>(std::atoi(argv[1]));
    }
    if (port == 0) {
        const char *env_port = std::getenv("FERQON_SIL_PORT");
        if (env_port) {
            port = static_cast<uint16_t>(std::atoi(env_port));
        }
    }
    if (port == 0) {
        port = FERQON_SIL_DEFAULT_PORT;
    }

    Serial.set_port(port);
    std::cerr << "[SIL] Ferqon firmware desktop build" << std::endl;
    std::cerr << "[SIL] Listening on TCP port " << port << std::endl;

    setup();

    for (;;) {
        loop();
        /* Drain any buffered TCP bytes quickly; sleep only when idle so the
         * parser does not time out on large frames. */
        if (Serial.available() == 0) {
            delay(1);
        }
    }
    return 0;
}
