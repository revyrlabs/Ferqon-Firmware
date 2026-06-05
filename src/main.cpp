#include <Arduino.h>
#include "ferqon_commands.h"
#include "protocol.h"
#include "dispatcher.h"
#include "app_state.h"
#include "ferqon_log.h"

// Driver extern declarations (drivers are defined in their .cpp files)
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

// Protocol write function
static void serial_write(const uint8_t *data, size_t len) {
    Serial.write(data, len);
}

ferqon_parser_t parser;
unsigned long last_heartbeat_ms = 0;
const unsigned long HEARTBEAT_INTERVAL_MS = 5000;  // 5 seconds

void setup() {
    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);
    
    FERQON_LOG_INFO("Ferqon v1 firmware starting");
    
    // Initialize dispatcher
    ferqon_dispatcher_init();
    
    // Initialize protocol
    ferqon_set_write_func(serial_write);
    ferqon_parser_init(&parser);
    FERQON_LOG_INFO("Protocol initialized");
    
    // Initialize app state
    app_state_init();
    FERQON_LOG_INFO("App state initialized");
    
    // Register drivers
    ferqon_register_driver(&ping_driver);
    ferqon_register_driver(&echo_driver);
    ferqon_register_driver(&gpio_driver);
    ferqon_register_driver(&reset_driver);
    ferqon_register_driver(&driver_call_driver);
    ferqon_register_driver(&uart_driver);
    ferqon_register_driver(&adc_driver);
    ferqon_register_driver(&pulse_driver);
    ferqon_register_driver(&device_info_driver);
    ferqon_register_driver(&driver_info_driver);
    ferqon_register_driver(&debug_driver);
    FERQON_LOG_INFO("Drivers registered");
    // Test log emission
    ferqon_send_log("FIRMWARE_STARTUP_TEST");
    
    // Ready
    app_state_set(FERQON_STATE_APP_READY);
    FERQON_LOG_INFO("Ferqon v1 - Ready");
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
