#include <Arduino.h>
#include "protocol.h"
#include "dispatcher.h"

// Include driver implementations
#include "echo.cpp"
#include "ping.cpp"
#include "reset.cpp"
#include "device_info.cpp"
#include "capabilities.cpp"
#include "gpio.cpp"

// Forward declarations of drivers
extern const ferqon_driver_t echo_driver;
extern const ferqon_driver_t ping_driver;
extern const ferqon_driver_t reset_driver;
extern const ferqon_driver_t device_info_driver;
extern const ferqon_driver_t capabilities_driver;
extern const ferqon_driver_t gpio_driver;

// Parser instance
static ferqon_parser_t g_parser;

void setup() {
    // Initialize serial (USB CDC)
    Serial.begin(115200);

    // Wait for serial to be ready
    while (!Serial) {
        delay(10);
    }

    Serial.println("Ferqon v1 Protocol Firmware Starting...");

    // Set write function for protocol output
    ferqon_set_write_func([](const uint8_t *data, size_t len) {
        Serial.write(data, len);
    });

    // Initialize parser
    ferqon_parser_init(&g_parser, 5000);  // 5 second timeout

    // Initialize dispatcher
    ferqon_dispatcher_init();

    // Register built-in drivers
    ferqon_register_driver(&echo_driver);
    ferqon_register_driver(&ping_driver);
    ferqon_register_driver(&reset_driver);
    ferqon_register_driver(&device_info_driver);
    ferqon_register_driver(&capabilities_driver);

    // Register optional drivers
    ferqon_register_driver(&gpio_driver);
}

void loop() {
    // Check for incoming data
    while (Serial.available() > 0) {
        uint8_t byte = Serial.read();

        uint8_t cmd_id;
        uint8_t params[256];
        uint8_t param_len;

        if (ferqon_parser_feed(&g_parser, byte, &cmd_id, params, &param_len)) {
            // Command successfully parsed, dispatch it
            uint8_t response[256];
            uint8_t response_len = 0;

            if (ferqon_dispatch_command(cmd_id, params, param_len, response, &response_len)) {
                // Command handled, send response
                ferqon_send_ok(response, response_len);
            }
            // If command not handled, error response is sent by dispatcher
        }
    }
}
