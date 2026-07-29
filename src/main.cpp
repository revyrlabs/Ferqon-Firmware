/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Main entry point: register drivers, initialize protocol, and run the loop. */
#include <Arduino.h>
#include "board_config.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "dispatcher.h"
#include "app_state.h"
#include "ferqon_log.h"
#include "production_config.h"

/* Not every Arduino board package defines LED_BUILTIN; fall back to the board
 * definition in board_config.h. */
#ifndef LED_BUILTIN
#ifdef FERQON_LED_PIN
#define LED_BUILTIN FERQON_LED_PIN
#else
#error "LED_BUILTIN not defined and FERQON_LED_PIN not set for this board"
#endif
#endif

/* Driver extern declarations (defined in their .cpp files). Adding a new
 * driver is a single entry in this array — no separate extern + register
 * call needed. */
extern "C" const ferqon_driver_t ping_driver;
extern "C" const ferqon_driver_t echo_driver;
extern "C" const ferqon_driver_t gpio_driver;
extern "C" const ferqon_driver_t reset_driver;
extern "C" const ferqon_driver_t driver_call_driver;
extern "C" const ferqon_driver_t uart_driver;
extern "C" const ferqon_driver_t adc_driver;
extern "C" const ferqon_driver_t pulse_driver;
extern "C" const ferqon_driver_t device_info_driver;
extern "C" const ferqon_driver_t driver_info_driver;
extern "C" const ferqon_driver_t debug_driver;
extern "C" const ferqon_driver_t capabilities_driver;

static const ferqon_driver_t *const g_all_drivers[] = {
    &ping_driver,
    &echo_driver,
    &gpio_driver,
    &reset_driver,
    &driver_call_driver,
    &uart_driver,
    &adc_driver,
    &pulse_driver,
    &device_info_driver,
    &driver_info_driver,
    &capabilities_driver,
    &debug_driver,
};
static const uint8_t g_driver_count =
    (uint8_t)(sizeof(g_all_drivers) / sizeof(g_all_drivers[0]));

static void serial_write(const uint8_t *data, size_t len) {
    Serial.write(data, len);
}

ferqon_parser_t parser;
unsigned long last_heartbeat_ms = 0;
static const unsigned long HEARTBEAT_INTERVAL_MS = FERQON_HEARTBEAT_INTERVAL_MS;

void setup() {
    Serial.begin(FERQON_SERIAL_BAUD);
    pinMode(LED_BUILTIN, OUTPUT);

    FERQON_LOG_INFO("Ferqon %s firmware starting", FERQON_FW_VERSION);

    ferqon_dispatcher_init();

    ferqon_set_write_func(serial_write);
    ferqon_parser_init(&parser);
    FERQON_LOG_INFO("Protocol initialized");

    app_state_init();
    FERQON_LOG_INFO("App state initialized");

    for (uint8_t i = 0; i < g_driver_count; i++) {
        ferqon_register_driver(g_all_drivers[i]);
    }
    FERQON_LOG_INFO("Drivers registered");

    // Ready
    app_state_set(FERQON_STATE_APP_READY);
    FERQON_LOG_INFO("Ferqon %s ready", FERQON_FW_VERSION);
}

void loop() {
    // Handle serial input
    if (Serial.available() > 0) {
        int c = Serial.read();
        ferqon_request_t req;
        if (ferqon_parser_feed(&parser, (uint8_t)c, &req)) {
            // Dispatch command
            ferqon_dispatch_request(&req);
        }
    }

    // Send periodic heartbeat
    unsigned long now = millis();
    if (now - last_heartbeat_ms >= HEARTBEAT_INTERVAL_MS) {
        last_heartbeat_ms = now;
        uint8_t state = app_state_get();
        uint32_t uptime = now;
        uint8_t flags = 0;  // Could indicate error conditions, etc.
        ferqon_send_heartbeat(state, uptime, flags);
    }
}
