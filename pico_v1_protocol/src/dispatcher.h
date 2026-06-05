#ifndef FERQON_DISPATCHER_H
#define FERQON_DISPATCHER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

// Driver handler function signature
typedef bool (*ferqon_driver_handler_t)(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                                       uint8_t *response, uint8_t *response_len);

// Driver entry
typedef struct {
    const char *name;
    uint8_t id;
    ferqon_driver_handler_t handle;
} ferqon_driver_t;

// Register a driver
void ferqon_register_driver(const ferqon_driver_t *driver);

// Dispatch command to drivers
bool ferqon_dispatch_command(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len);

// Initialize dispatcher
void ferqon_dispatcher_init(void);

#endif
