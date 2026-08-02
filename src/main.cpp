/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Main entry point: initialize the HAL, protocol, and run the loop. */
#include "ferqon_hal.h"
#include "board_config.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "dispatcher.h"
#include "app_state.h"
#include "ferqon_log.h"
#include "production_config.h"

ferqon_parser_t parser;
unsigned long last_heartbeat_ms = 0;
static const unsigned long HEARTBEAT_INTERVAL_MS = FERQON_HEARTBEAT_INTERVAL_MS;

/* setup/loop are the Arduino application entry points and must have C linkage
 * so the framework's weak main() can find them. */
extern "C" void setup() {
#if defined(FERQON_BOARD_NATIVE)
    ferqon_hal_init_host();
#else
    ferqon_hal_init_arduino();
#endif

    ferqon_hal_gpio_set_mode(FERQON_LED_PIN, FERQON_GPIO_OUTPUT);
    ferqon_hal_serial_init(FERQON_SERIAL_BAUD);

    FERQON_LOG_INFO("Ferqon %s firmware starting", FERQON_FW_VERSION);

    ferqon_parser_init(&parser);
    FERQON_LOG_INFO("Protocol initialized");

    app_state_init();
    FERQON_LOG_INFO("App state initialized");

    // Ready
    app_state_set(FERQON_STATE_APP_READY);
    FERQON_LOG_INFO("Ferqon %s ready", FERQON_FW_VERSION);
}

extern "C" void loop() {
    // Handle serial input. Drain the RX buffer each loop so frames are not
    // artificially throttled to one byte per main-loop iteration.
    unsigned long now = ferqon_hal_millis();
    while (ferqon_hal_serial_available() > 0) {
        int c = ferqon_hal_serial_read();
        ferqon_request_t req;
        if (ferqon_parser_feed_with_time(&parser, (uint8_t)c, &req, (uint32_t)now)) {
            // Dispatch command
            ferqon_dispatch_request(&req);
        }
    }

    // Send periodic heartbeat
    if (now - last_heartbeat_ms >= HEARTBEAT_INTERVAL_MS) {
        last_heartbeat_ms = now;
        uint8_t state = app_state_get();
        uint32_t uptime = (uint32_t)now;
        uint8_t flags = 0;  // Could indicate error conditions, etc.
        ferqon_send_heartbeat(state, uptime, flags);
    }
}
