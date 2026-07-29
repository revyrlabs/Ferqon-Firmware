/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "driver_call.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include "uart.h"
#include "production_config.h"
#include <string.h>
#include <stdlib.h>
#include <Arduino.h>

/* HIL session state — set by hil.enter, cleared by hil.exit.
 * DUT-optional: enter always succeeds even with no DUT connected. */
static bool g_hil_session_active = false;

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
        if (key_len == 0 || key_len > DC_MAX_KEY_LEN) {
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

/* Compute the safe length of a parsed arg value. The parser does not
 * null-terminate individual values, so scan up to the next ';' or '\0'.
 */
static size_t driver_call_value_len(const char *value) {
    if (!value) return 0;
    const char *p = value;
    while (*p != '\0' && *p != ';') {
        p++;
    }
    return (size_t)(p - value);
}

/* Parse an unsigned 16-bit value from a parsed arg string. The value is
 * bounded by the next ';' or null terminator. Returns true on success,
 * false if the value is empty, non-numeric, or out of uint16_t range.
 */
static bool driver_call_parse_u16(const char *value, uint16_t *out) {
    if (!value || !out) return false;
    uint32_t result = 0;
    const char *p = value;
    while (*p != '\0' && *p != ';') {
        if (*p < '0' || *p > '9') {
            return false;
        }
        result = result * 10 + (uint32_t)(*p - '0');
        if (result > 65535) {
            return false;
        }
        p++;
    }
    if (p == value) {
        return false;
    }
    *out = (uint16_t)result;
    return true;
}

/* ------------------------------------------------------------------ */
/* HIL method handlers.                                                */
/* Each returns true if it claimed the command (success or structured  */
/* error already sent); false to fall through to "unknown method".     */
/* ------------------------------------------------------------------ */

typedef bool (*hil_method_fn)(uint8_t seq, uint8_t cmd_id,
                              const dc_arg_t *args, int arg_count,
                              uint8_t *response, uint8_t *response_len,
                              bool *already_responded);

/* Helper: require a single named arg, reply with error if missing.
 * Creates a local variable `name_str` pointing to the arg value. */
#define REQUIRE_ARG(name) \
    const char *name##_str = driver_call_get_arg(args, arg_count, #name); \
    if (!name##_str) { \
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "missing: " #name); \
    }

static bool hil_io_set(uint8_t seq, uint8_t cmd_id,
                       const dc_arg_t *args, int arg_count,
                       uint8_t *response, uint8_t *response_len,
                       bool *already_responded) {
    (void)response; (void)response_len;
    REQUIRE_ARG(pin);
    REQUIRE_ARG(level);

    uint8_t pin = (uint8_t)atoi(pin_str);
    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    digitalWrite(pin, (strcmp(level_str, "HIGH") == 0) ? HIGH : LOW);
    return true;
}

static bool hil_io_get(uint8_t seq, uint8_t cmd_id,
                       const dc_arg_t *args, int arg_count,
                       uint8_t *response, uint8_t *response_len,
                       bool *already_responded) {
    REQUIRE_ARG(pin);

    uint8_t pin = (uint8_t)atoi(pin_str);
    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    response[0] = (uint8_t)digitalRead(pin);
    *response_len = 1;
    return true;
}

static bool hil_io_configure(uint8_t seq, uint8_t cmd_id,
                             const dc_arg_t *args, int arg_count,
                             uint8_t *response, uint8_t *response_len,
                             bool *already_responded) {
    (void)response; (void)response_len;
    REQUIRE_ARG(pin);
    REQUIRE_ARG(mode);

    uint8_t pin = (uint8_t)atoi(pin_str);
    int arduino_mode;
    if (strcmp(mode_str, "INPUT") == 0)           arduino_mode = INPUT;
    else if (strcmp(mode_str, "OUTPUT") == 0)     arduino_mode = OUTPUT;
    else if (strcmp(mode_str, "INPUT_PULLUP") == 0)    arduino_mode = INPUT_PULLUP;
    else if (strcmp(mode_str, "INPUT_PULLDOWN") == 0)  arduino_mode = INPUT_PULLDOWN;
    else {
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_UNSUPPORTED_MODE, FERQON_ECAT_COMMAND,
                    false, 0, NULL, 0);
    }

    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    pinMode(pin, arduino_mode);
    return true;
}

static bool hil_io_expect(uint8_t seq, uint8_t cmd_id,
                          const dc_arg_t *args, int arg_count,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    REQUIRE_ARG(timeout_ms);
    REQUIRE_ARG(pin);
    REQUIRE_ARG(level);

    uint16_t timeout_ms = (uint16_t)atoi(timeout_ms_str);
    uint8_t pin = (uint8_t)atoi(pin_str);
    uint8_t expected_level = (strcmp(level_str, "HIGH") == 0) ? 1 : 0;

    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

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

static bool hil_uart_send(uint8_t seq, uint8_t cmd_id,
                          const dc_arg_t *args, int arg_count,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    (void)response;
    REQUIRE_ARG(data);

    size_t data_len = driver_call_value_len(data_str);
    if (data_len == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "empty data");
    }

    ferqon_uart1_send((const uint8_t *)data_str, data_len);
    *response_len = 0;
    return true;
}

static bool hil_uart_expect(uint8_t seq, uint8_t cmd_id,
                            const dc_arg_t *args, int arg_count,
                            uint8_t *response, uint8_t *response_len,
                            bool *already_responded) {
    (void)response; (void)response_len;
    REQUIRE_ARG(timeout_ms);
    REQUIRE_ARG(pattern);

    uint16_t timeout_ms;
    if (!driver_call_parse_u16(timeout_ms_str, &timeout_ms) || timeout_ms == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid timeout_ms");
    }

    size_t pattern_len = driver_call_value_len(pattern_str);
    if (pattern_len == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "empty pattern");
    }

    bool found = ferqon_uart1_expect(pattern_str, pattern_len, timeout_ms);
    if (!found) {
        REPLY_ERROR_STR(seq, cmd_id, FERQON_ERR_TIMEOUT, FERQON_ECAT_TIMEOUT,
                        false, 0, "uart expect timeout");
    }

    response[0] = 1; /* Success */
    *response_len = 1;
    return true;
}

static bool hil_enter(uint8_t seq, uint8_t cmd_id,
                      const dc_arg_t *args, int arg_count,
                      uint8_t *response, uint8_t *response_len,
                      bool *already_responded) {
    (void)seq; (void)cmd_id; (void)args; (void)arg_count; (void)already_responded;
    /* HIL session handshake — DUT-optional.
     * Optional args: uart_tx, uart_rx, uart_baud.
     * Always succeeds (even with no DUT connected). */
    const char *uart_baud_str = driver_call_get_arg(args, arg_count, "uart_baud");
    uint32_t baud = 0;
    if (uart_baud_str) {
        baud = (uint32_t)strtoul(uart_baud_str, NULL, 10);
    }

    /* Arm Serial1 if a baud was provided; otherwise defer to first use. */
    if (baud != 0) {
        ferqon_uart1_init(baud);
    }

    g_hil_session_active = true;
    FERQON_LOG_DEBUG("hil.enter: session active");

    response[0] = 1; /* Success */
    *response_len = 1;
    return true;
}

static bool hil_exit(uint8_t seq, uint8_t cmd_id,
                     const dc_arg_t *args, int arg_count,
                     uint8_t *response, uint8_t *response_len,
                     bool *already_responded) {
    (void)seq; (void)cmd_id; (void)args; (void)arg_count; (void)already_responded;
    g_hil_session_active = false;
    FERQON_LOG_DEBUG("hil.exit: session cleared");

    response[0] = 1; /* Success */
    *response_len = 1;
    return true;
}

/* Table of implemented HIL methods. adc_read / adc_expect / pulse_measure
 * are intentionally absent: the direct commands (FERQON_CMD_ADC_READ,
 * FERQON_CMD_ADC_EXPECT, FERQON_CMD_PULSE_MEASURE) are the supported path.
 * Adding a method here is now a one-line table entry. */
static const struct {
    const char *name;
    hil_method_fn fn;
} hil_methods[] = {
    {"io_set",        hil_io_set},
    {"io_get",        hil_io_get},
    {"io_configure",  hil_io_configure},
    {"io_expect",     hil_io_expect},
    {"uart_send",     hil_uart_send},
    {"uart_expect",   hil_uart_expect},
    {"enter",         hil_enter},
    {"exit",          hil_exit},
};
static const uint8_t hil_method_count =
    (uint8_t)(sizeof(hil_methods) / sizeof(hil_methods[0]));

/* ------------------------------------------------------------------ */
/* Driver call handler for cmd_id=3                                    */
/* ------------------------------------------------------------------ */

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
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "payload too short");
    }

    const uint8_t *p = params;
    const uint8_t *end = params + param_len;

    /* Read driver name (length-prefixed) */
    uint8_t driver_len = p[0];
    p += 1;
    if (p + driver_len > end) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "driver name truncated");
    }
    char driver_name[DC_MAX_DRIVER_NAME];
    if (driver_len >= sizeof(driver_name)) driver_len = sizeof(driver_name) - 1;
    memcpy(driver_name, p, driver_len);
    driver_name[driver_len] = '\0';
    p += driver_len;

    /* Read method name (length-prefixed) */
    if (p >= end) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "missing method");
    }
    uint8_t method_len = p[0];
    p += 1;
    if (p + method_len > end) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "method name truncated");
    }
    char method_name[DC_MAX_METHOD_NAME];
    if (method_len >= sizeof(method_name)) method_len = sizeof(method_name) - 1;
    memcpy(method_name, p, method_len);
    method_name[method_len] = '\0';
    p += method_len;

    /* Remaining bytes are the args string (key=value;key=value;...) */
    /* The SDK does NOT null-terminate the args, so copy into a local buffer */
    size_t args_len = end - p;
    char args_buf[DC_MAX_ARGS_BUF];
    if (args_len >= sizeof(args_buf)) args_len = sizeof(args_buf) - 1;
    memcpy(args_buf, p, args_len);
    args_buf[args_len] = '\0';
    const char *args = args_buf;

    /* Shared log buffer for the two "not found" paths below. */
    char log_buf[64];

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

        /* Driver not found or didn't handle it.
         * Use "%s" format — driver_name is user-supplied and must not be
         * treated as a format string (format string injection). */
        snprintf(log_buf, sizeof(log_buf), "DRIVER_CALL unknown driver: %s", driver_name);
        FERQON_LOG_DEBUG("%s", log_buf);
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_INVALID_DRIVER, FERQON_ECAT_COMMAND,
                    false, 0, (const uint8_t *)driver_name, (uint8_t)strlen(driver_name));
    }

    /* Parse args */
    dc_arg_t parsed_args[DC_MAX_ARGS];
    int arg_count = driver_call_parse_args(args, parsed_args, DC_MAX_ARGS);
    if (arg_count < 0) {
        char err_detail[64];
        snprintf(err_detail, sizeof(err_detail), "malformed: %.40s", args);
        REPLY_ERROR_STR(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, err_detail);
    }

    /* Dispatch to the HIL method table. */
    for (uint8_t i = 0; i < hil_method_count; i++) {
        if (strcmp(method_name, hil_methods[i].name) == 0) {
            return hil_methods[i].fn(seq, cmd_id, parsed_args, arg_count,
                                     response, response_len, already_responded);
        }
    }

    /* Unknown method — same format-string safety as above. */
    snprintf(log_buf, sizeof(log_buf), "DRIVER_CALL unknown method: %s.%s", driver_name, method_name);
    FERQON_LOG_DEBUG("%s", log_buf);
    REPLY_ERROR(seq, cmd_id, FERQON_ERR_INVALID_METHOD, FERQON_ECAT_COMMAND,
                false, 0, (const uint8_t *)method_name, (uint8_t)strlen(method_name));
}

extern "C" const ferqon_driver_t driver_call_driver = {
    .name = "driver_call",
    .id = FERQON_CMD_DRIVER_CALL,
    .handle = driver_call_handler,
};
