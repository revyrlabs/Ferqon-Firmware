/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "driver_call.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include "dispatcher.h"
#include "board_config.h"
#include "pin_macros.h"
#include <string.h>
#include <stdlib.h>
#include <Arduino.h>

#define MAX_KEY_LEN 31
#define MAX_ARGS 8

/* Forward declaration of the global driver array from dispatcher.cpp */
extern ferqon_driver_t g_drivers[];
extern uint8_t g_driver_count;

int driver_call_parse_args(const char *args, dc_arg_t *out, uint8_t max_args) {
    if (!args || !out || max_args == 0) {
        return 0;
    }

    int count = 0;
    const char *start = args;
    const char *end = args;

    while (*end != '\0' && count < max_args) {
        /* Find semicolon or end of string */
        while (*end != '\0' && *end != ';') {
            end++;
        }

        /* Skip empty segments (double semicolon) */
        if (end == start) {
            start = ++end;
            continue;
        }

        /* Check for '=' in segment */
        const char *eq = start;
        while (*eq != '\0' && *eq != '=' && eq < end) {
            eq++;
        }

        if (eq == start || eq >= end || *eq != '=') {
            FERQON_LOG_DEBUG("Malformed arg pair (missing '=')");
            return -1;
        }

        /* Extract key */
        size_t key_len = eq - start;
        if (key_len == 0 || key_len > MAX_KEY_LEN) {
            FERQON_LOG_DEBUG("Malformed arg pair (empty or too long key)");
            return -1;
        }

        /* Extract value */
        const char *val_start = eq + 1;
        size_t val_len = end - val_start;
        if (val_len == 0) {
            FERQON_LOG_DEBUG("Malformed arg pair (empty value)");
            return -1;
        }

        /* Store the pair (point into original string) */
        out[count].key = start;
        out[count].value = val_start;
        count++;

        /* Move to next segment — don't advance past the null terminator */
        if (*end == '\0') {
            break;
        }
        start = ++end;
    }

    return count;
}

const char *driver_call_get_arg(const dc_arg_t *args, int count, const char *key) {
    if (!args || !key) {
        return NULL;
    }

    size_t key_len = strlen(key);
    for (int i = 0; i < count; i++) {
        /* Use strncmp + check that the next char is '=' (key boundary) */
        if (strncmp(args[i].key, key, key_len) == 0 && args[i].key[key_len] == '=') {
            return args[i].value;
        }
    }

    return NULL;
}

/* Driver call handler for cmd_id=3 */
static bool driver_call_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    /* Only handle DRIVER_CALL command */
    if (cmd_id != FERQON_CMD_DRIVER_CALL) {
        return false;
    }
    
    /* Payload format (length-prefixed, matches ferqon_hw SDK):          */
    /*   [driver_len][driver...][method_len][method...][args...]           */
    /* Note: PKT_REQUEST byte is already stripped by dispatcher            */
    if (param_len < 2) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        false, 0, (const uint8_t *)"payload too short", 17);
        *already_responded = true;
        return true;
    }

    const uint8_t *p = params;
    const uint8_t *end = params + param_len;

    /* Read driver name (length-prefixed) */
    uint8_t driver_len = p[0];
    p += 1;
    if (p + driver_len > end) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        false, 0, (const uint8_t *)"driver name truncated", 21);
        *already_responded = true;
        return true;
    }
    char driver_name[32];
    if (driver_len >= sizeof(driver_name)) driver_len = sizeof(driver_name) - 1;
    memcpy(driver_name, p, driver_len);
    driver_name[driver_len] = '\0';
    p += driver_len;

    /* Read method name (length-prefixed) */
    if (p >= end) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        false, 0, (const uint8_t *)"missing method", 14);
        *already_responded = true;
        return true;
    }
    uint8_t method_len = p[0];
    p += 1;
    if (p + method_len > end) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        false, 0, (const uint8_t *)"method name truncated", 21);
        *already_responded = true;
        return true;
    }
    char method_name[32];
    if (method_len >= sizeof(method_name)) method_len = sizeof(method_name) - 1;
    memcpy(method_name, p, method_len);
    method_name[method_len] = '\0';
    p += method_len;

    /* Remaining bytes are the args string (key=value;key=value;...) */
    /* The SDK does NOT null-terminate the args, so copy into a local buffer */
    size_t args_len = end - p;
    char args_buf[128];
    if (args_len >= sizeof(args_buf)) args_len = sizeof(args_buf) - 1;
    memcpy(args_buf, p, args_len);
    args_buf[args_len] = '\0';
    const char *args = args_buf;

    /* For now, only handle "hil" driver */
    if (strcmp(driver_name, "hil") != 0) {
        /* Try to find a registered driver with this name and dispatch to it */
        for (uint8_t i = 0; i < g_driver_count; i++) {
            if (strcmp(g_drivers[i].name, driver_name) == 0) {
                /* Dispatch to the registered driver's handler */
                FERQON_LOG_DEBUG("DRIVER_CALL dispatching to custom driver");
                bool handled = g_drivers[i].handle(seq, cmd_id, params, param_len,
                                                   response, response_len, already_responded);
                if (handled) {
                    return true;
                }
                /* Driver didn't claim it, fall through to error */
                break;
            }
        }

        /* Driver not found or didn't handle it */
        char log_buf[64];
        snprintf(log_buf, sizeof(log_buf), "DRIVER_CALL unknown driver: %s", driver_name);
        FERQON_LOG_DEBUG(log_buf);
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_DRIVER, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)driver_name, strlen(driver_name));
        *already_responded = true;
        return true;
    }

    /* Parse args */
    dc_arg_t parsed_args[MAX_ARGS];
    int arg_count = driver_call_parse_args(args, parsed_args, MAX_ARGS);
    if (arg_count < 0) {
        /* Include the args string in the error for debugging */
        char err_detail[64];
        snprintf(err_detail, sizeof(err_detail), "malformed: %.40s", args);
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)err_detail, strlen(err_detail));
        *already_responded = true;
        return true;
    }

    /* Dispatch to sub-handlers for "hil" driver.
     *
     * The following methods are fully implemented: io_set, io_get,
     * io_configure, io_expect.
     *
     * The following methods are NOT YET IMPLEMENTED and return
     * FERQON_ERR_NOT_IMPLEMENTED: uart_send, uart_expect, adc_read,
     * adc_expect, pulse_measure. Use the direct command interface
     * (FERQON_CMD_UART_SEND, FERQON_CMD_ADC_READ, etc.) instead.
     */
    if (strcmp(method_name, "io_set") == 0) {
        /* Map to gpio_write */
        const char *pin_str = driver_call_get_arg(parsed_args, arg_count, "pin");
        const char *level_str = driver_call_get_arg(parsed_args, arg_count, "level");
        if (!pin_str || !level_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: pin or level", 20);
            *already_responded = true;
            return true;
        }

        uint8_t pin = atoi(pin_str);
        uint8_t value = (strcmp(level_str, "HIGH") == 0) ? 1 : 0;

        /* Reuse gpio_write logic */
        if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                            false, pin, NULL, 0);
            *already_responded = true;
            return true;
        }

        digitalWrite(pin, value ? HIGH : LOW);
        return true;
    }
    else if (strcmp(method_name, "io_get") == 0) {
        /* Map to gpio_read */
        const char *pin_str = driver_call_get_arg(parsed_args, arg_count, "pin");
        if (!pin_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: pin", 11);
            *already_responded = true;
            return true;
        }

        uint8_t pin = atoi(pin_str);
        if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                            false, pin, NULL, 0);
            *already_responded = true;
            return true;
        }

        response[0] = (uint8_t)digitalRead(pin);
        *response_len = 1;
        return true;
    }
    else if (strcmp(method_name, "io_configure") == 0) {
        /* Map to pin_mode */
        const char *pin_str = driver_call_get_arg(parsed_args, arg_count, "pin");
        const char *mode_str = driver_call_get_arg(parsed_args, arg_count, "mode");
        if (!pin_str || !mode_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: pin or mode", 20);
            *already_responded = true;
            return true;
        }

        uint8_t pin = atoi(pin_str);
        int arduino_mode;

        if (strcmp(mode_str, "INPUT") == 0) {
            arduino_mode = INPUT;
        } else if (strcmp(mode_str, "OUTPUT") == 0) {
            arduino_mode = OUTPUT;
        } else if (strcmp(mode_str, "INPUT_PULLUP") == 0) {
            arduino_mode = INPUT_PULLUP;
        } else if (strcmp(mode_str, "INPUT_PULLDOWN") == 0) {
            arduino_mode = INPUT_PULLDOWN;
        } else {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_MODE, FERQON_ECAT_COMMAND,
                            false, 0, NULL, 0);
            *already_responded = true;
            return true;
        }

        if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                            false, pin, NULL, 0);
            *already_responded = true;
            return true;
        }

        pinMode(pin, arduino_mode);
        return true;
    }
    else if (strcmp(method_name, "io_expect") == 0) {
        /* Wait for pin to reach level within timeout */
        const char *timeout_str = driver_call_get_arg(parsed_args, arg_count, "timeout_ms");
        const char *pin_str = driver_call_get_arg(parsed_args, arg_count, "pin");
        const char *level_str = driver_call_get_arg(parsed_args, arg_count, "level");
        if (!timeout_str || !pin_str || !level_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: timeout_ms, pin, or level", 30);
            *already_responded = true;
            return true;
        }

        uint16_t timeout_ms = atoi(timeout_str);
        uint8_t pin = atoi(pin_str);
        uint8_t expected_level = (strcmp(level_str, "HIGH") == 0) ? 1 : 0;

        if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                            false, pin, NULL, 0);
            *already_responded = true;
            return true;
        }

        /* Wait for pin state with timeout */
        unsigned long start = millis();
        while ((millis() - start) < timeout_ms) {
            if (digitalRead(pin) == expected_level) {
                response[0] = 1; /* Success */
                *response_len = 1;
                return true;
            }
            delay(1);
        }

        /* Timeout */
        response[0] = 0; /* Failed */
        *response_len = 1;
        return true;
    }
    else if (strcmp(method_name, "uart_send") == 0) {
        /* Send data via UART - stub for now, delegates to uart driver */
        const char *data_str = driver_call_get_arg(parsed_args, arg_count, "data");
        if (!data_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: data", 12);
            *already_responded = true;
            return true;
        }

        /* Delegate to uart driver */
        ferqon_send_error(seq, cmd_id, FERQON_ERR_NOT_IMPLEMENTED, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"uart_send delegated to uart driver", 35);
        *already_responded = true;
        return true;
    }
    else if (strcmp(method_name, "uart_expect") == 0) {
        /* Wait for pattern in UART RX - stub for now, delegates to uart driver */
        const char *timeout_str = driver_call_get_arg(parsed_args, arg_count, "timeout_ms");
        const char *pattern_str = driver_call_get_arg(parsed_args, arg_count, "pattern");
        if (!timeout_str || !pattern_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: timeout_ms or pattern", 28);
            *already_responded = true;
            return true;
        }

        /* Delegate to uart driver */
        ferqon_send_error(seq, cmd_id, FERQON_ERR_NOT_IMPLEMENTED, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"uart_expect delegated to uart driver", 37);
        *already_responded = true;
        return true;
    }
    else if (strcmp(method_name, "adc_read") == 0) {
        /* Read ADC channel - stub for now, delegates to adc driver */
        const char *channel_str = driver_call_get_arg(parsed_args, arg_count, "channel");
        if (!channel_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: channel", 15);
            *already_responded = true;
            return true;
        }

        /* Delegate to adc driver */
        ferqon_send_error(seq, cmd_id, FERQON_ERR_NOT_IMPLEMENTED, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"adc_read delegated to adc driver", 33);
        *already_responded = true;
        return true;
    }
    else if (strcmp(method_name, "adc_expect") == 0) {
        /* Wait for ADC to be within range - stub for now, delegates to adc driver */
        const char *timeout_str = driver_call_get_arg(parsed_args, arg_count, "timeout_ms");
        const char *channel_str = driver_call_get_arg(parsed_args, arg_count, "channel");
        const char *min_str = driver_call_get_arg(parsed_args, arg_count, "min_mv");
        const char *max_str = driver_call_get_arg(parsed_args, arg_count, "max_mv");
        if (!timeout_str || !channel_str || !min_str || !max_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: timeout_ms, channel, min_mv, or max_mv", 48);
            *already_responded = true;
            return true;
        }

        /* Delegate to adc driver */
        ferqon_send_error(seq, cmd_id, FERQON_ERR_NOT_IMPLEMENTED, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"adc_expect delegated to adc driver", 35);
        *already_responded = true;
        return true;
    }
    else if (strcmp(method_name, "pulse_measure") == 0) {
        /* Measure pulse width - stub for now, delegates to pulse driver */
        const char *timeout_str = driver_call_get_arg(parsed_args, arg_count, "timeout_ms");
        const char *pin_str = driver_call_get_arg(parsed_args, arg_count, "pin");
        const char *min_str = driver_call_get_arg(parsed_args, arg_count, "min_us");
        const char *max_str = driver_call_get_arg(parsed_args, arg_count, "max_us");
        if (!timeout_str || !pin_str || !min_str || !max_str) {
            ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                            false, 0, (const uint8_t *)"missing: timeout_ms, pin, min_us, or max_us", 42);
            *already_responded = true;
            return true;
        }

        /* Delegate to pulse driver */
        ferqon_send_error(seq, cmd_id, FERQON_ERR_NOT_IMPLEMENTED, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"pulse_measure delegated to pulse driver", 39);
        *already_responded = true;
        return true;
    }
    else {
        /* Unknown method */
        char log_buf[64];
        snprintf(log_buf, sizeof(log_buf), "DRIVER_CALL unknown method: %s.%s", driver_name, method_name);
        FERQON_LOG_DEBUG(log_buf);
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_METHOD, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)method_name, strlen(method_name));
        *already_responded = true;
        return true;
    }
}

extern "C" const ferqon_driver_t driver_call_driver = {
    .name = "driver_call",
    .id = FERQON_CMD_DRIVER_CALL,
    .handle = driver_call_handler,
};
