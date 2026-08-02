/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include "uart.h"
#include "production_config.h"
#include "ferqon_hal.h"
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

/* Canonical string literals for the bool_high_low arg type. Not in the
 * SSOT because the type is generic; centralised here so the two places
 * that parse a level string cannot drift apart. */
#define HIL_LEVEL_HIGH  "HIGH"
#define HIL_LEVEL_LOW   "LOW"

/* Buffer-size limits for driver_call argument parsing. */
#define DC_MAX_KEY_LEN        31
#define DC_MAX_ARGS           8
#define DC_MAX_DRIVER_NAME    32
#define DC_MAX_METHOD_NAME    32
#define DC_MAX_ARGS_BUF       128

/* Parse a semicolon-delimited key=value string in-place.
 * Empty segments between ';' are skipped, but empty keys or values,
 * missing '=', and out-of-range values are rejected.
 * Returns the number of pairs found, or -1 on malformed input. */
static int parse_args(char *args, const char **keys, const char **values, uint8_t max_args) {
    int count = 0;
    char *p = args;

    while (*p != '\0' && count < max_args) {
        /* Skip empty segments (leading, trailing, or consecutive ';'). */
        while (*p == ';') p++;
        if (*p == '\0') break;

        char *eq = strchr(p, '=');
        if (!eq) return -1;

        *eq = '\0';
        char *key = p;
        char *value = eq + 1;

        if (*key == '\0' || strlen(key) > DC_MAX_KEY_LEN) return -1;

        char *semi = strchr(value, ';');
        if (semi) {
            *semi = '\0';
            p = semi + 1;
        } else {
            p = value + strlen(value);
        }

        if (*value == '\0') return -1;

        keys[count] = key;
        values[count] = value;
        count++;
    }

    return count;
}

/* Look up an argument by key in the parsed args arrays. */
static const char *get_arg(const char **keys, const char **values, int count, const char *key) {
    for (int i = 0; i < count; i++) {
        if (strcmp(keys[i], key) == 0) {
            return values[i];
        }
    }
    return NULL;
}

/* Parse an unsigned 16-bit value from a null-terminated string. */
static bool parse_u16(const char *value, uint16_t *out) {
    if (!value || *value == '\0') return false;

    char *end = NULL;
    unsigned long v = strtoul(value, &end, 10);
    if (end == value || *end != '\0' || v > 65535) return false;

    *out = (uint16_t)v;
    return true;
}

/* Parse an unsigned 8-bit value from a null-terminated string. */
static bool parse_u8(const char *value, uint8_t *out) {
    if (!value || *value == '\0') return false;

    char *end = NULL;
    unsigned long v = strtoul(value, &end, 10);
    if (end == value || *end != '\0' || v > 255) return false;

    *out = (uint8_t)v;
    return true;
}

/* ------------------------------------------------------------------ */
/* HIL method handlers.                                                */
/* Each returns true if it claimed the command (success or structured  */
/* error already sent); false to fall through to "unknown method".     */
/* ------------------------------------------------------------------ */

typedef bool (*hil_method_fn)(uint8_t seq, uint8_t cmd_id,
                              const char **keys, const char **values, int arg_count,
                              uint8_t *response, uint8_t *response_len,
                              bool *already_responded);

/* Require a single named arg, reply with an error if missing. */
#define REQUIRE_ARG(name) \
    const char *name##_str = get_arg(keys, values, arg_count, #name); \
    if (!name##_str) { \
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "missing: " #name); \
    }

static bool hil_io_set(uint8_t seq, uint8_t cmd_id,
                       const char **keys, const char **values, int arg_count,
                       uint8_t *response, uint8_t *response_len,
                       bool *already_responded) {
    (void)response; (void)response_len;
    REQUIRE_ARG(pin);
    REQUIRE_ARG(level);

    uint8_t pin;
    if (!parse_u8(pin_str, &pin)) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid pin");
    }
    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    ferqon_hal_gpio_write(pin, (strcmp(level_str, HIL_LEVEL_HIGH) == 0) ? 1 : 0);
    return true;
}

static bool hil_io_get(uint8_t seq, uint8_t cmd_id,
                       const char **keys, const char **values, int arg_count,
                       uint8_t *response, uint8_t *response_len,
                       bool *already_responded) {
    REQUIRE_ARG(pin);

    uint8_t pin;
    if (!parse_u8(pin_str, &pin)) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid pin");
    }
    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    response[0] = (uint8_t)ferqon_hal_gpio_read(pin);
    *response_len = 1;
    return true;
}

static bool hil_io_configure(uint8_t seq, uint8_t cmd_id,
                             const char **keys, const char **values, int arg_count,
                             uint8_t *response, uint8_t *response_len,
                             bool *already_responded) {
    (void)response; (void)response_len;
    REQUIRE_ARG(pin);
    REQUIRE_ARG(mode);

    uint8_t pin;
    if (!parse_u8(pin_str, &pin)) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid pin");
    }
    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    uint8_t ferqon_mode;
    if (strcmp(mode_str, FERQON_GPIO_MODE_NAME_INPUT) == 0)                ferqon_mode = FERQON_GPIO_INPUT;
    else if (strcmp(mode_str, FERQON_GPIO_MODE_NAME_OUTPUT) == 0)          ferqon_mode = FERQON_GPIO_OUTPUT;
    else if (strcmp(mode_str, FERQON_GPIO_MODE_NAME_INPUT_PULLUP) == 0)   ferqon_mode = FERQON_GPIO_INPUT_PULLUP;
    else if (strcmp(mode_str, FERQON_GPIO_MODE_NAME_INPUT_PULLDOWN) == 0) ferqon_mode = FERQON_GPIO_INPUT_PULLDOWN;
    else {
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_UNSUPPORTED_MODE, FERQON_ECAT_COMMAND,
                    false, 0, NULL, 0);
    }

    ferqon_hal_gpio_set_mode(pin, ferqon_mode);
    return true;
}

static bool hil_io_expect(uint8_t seq, uint8_t cmd_id,
                          const char **keys, const char **values, int arg_count,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    REQUIRE_ARG(timeout_ms);
    REQUIRE_ARG(pin);
    REQUIRE_ARG(level);

    uint16_t timeout_ms;
    if (!parse_u16(timeout_ms_str, &timeout_ms) || timeout_ms == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid timeout_ms");
    }

    uint8_t pin;
    if (!parse_u8(pin_str, &pin)) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid pin");
    }
    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;

    uint8_t expected_level = (strcmp(level_str, HIL_LEVEL_HIGH) == 0) ? 1 : 0;

    unsigned long start = ferqon_hal_millis();
    while ((ferqon_hal_millis() - start) < timeout_ms) {
        if (ferqon_hal_gpio_read(pin) == expected_level) {
            response[0] = 1; /* Success */
            *response_len = 1;
            return true;
        }
        ferqon_hal_delay_ms(1);
    }

    /* Timeout */
    response[0] = 0; /* Failed */
    *response_len = 1;
    return true;
}

static bool hil_uart_send(uint8_t seq, uint8_t cmd_id,
                          const char **keys, const char **values, int arg_count,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    (void)response; (void)response_len; (void)already_responded;
    REQUIRE_ARG(data);

    size_t data_len = strlen(data_str);
    if (data_len == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "empty data");
    }

    ferqon_uart1_send((const uint8_t *)data_str, data_len);
    *response_len = 0;
    return true;
}

static bool hil_uart_expect(uint8_t seq, uint8_t cmd_id,
                            const char **keys, const char **values, int arg_count,
                            uint8_t *response, uint8_t *response_len,
                            bool *already_responded) {
    (void)response; (void)response_len; (void)already_responded;
    REQUIRE_ARG(timeout_ms);
    REQUIRE_ARG(pattern);

    uint16_t timeout_ms;
    if (!parse_u16(timeout_ms_str, &timeout_ms) || timeout_ms == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid timeout_ms");
    }

    size_t pattern_len = strlen(pattern_str);
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
                      const char **keys, const char **values, int arg_count,
                      uint8_t *response, uint8_t *response_len,
                      bool *already_responded) {
    (void)seq; (void)cmd_id; (void)keys; (void)values; (void)arg_count; (void)already_responded;
    /* HIL session handshake — DUT-optional.
     * Optional args: uart_tx, uart_rx, uart_baud.
     * Always succeeds (even with no DUT connected). */
    const char *uart_baud_str = get_arg(keys, values, arg_count, "uart_baud");
    if (uart_baud_str) {
        char *end = NULL;
        unsigned long baud = strtoul(uart_baud_str, &end, 10);
        if (*uart_baud_str != '\0' && *end == '\0' && baud > 0 && baud <= UINT32_MAX) {
            ferqon_uart1_init((uint32_t)baud);
        }
    }

    FERQON_LOG_DEBUG("hil.enter: session active");

    response[0] = 1; /* Success */
    *response_len = 1;
    return true;
}

static bool hil_exit(uint8_t seq, uint8_t cmd_id,
                     const char **keys, const char **values, int arg_count,
                     uint8_t *response, uint8_t *response_len,
                     bool *already_responded) {
    (void)seq; (void)cmd_id; (void)keys; (void)values; (void)arg_count; (void)already_responded;
    FERQON_LOG_DEBUG("hil.exit: session cleared");

    response[0] = 1; /* Success */
    *response_len = 1;
    return true;
}

/* Backend/SSOT still lists adc_read, adc_expect, and pulse_measure as HIL
 * driver methods.  They are intentionally delegated to dedicated native
 * commands on the MCU, so reply NOT_IMPLEMENTED and let the caller fall back
 * to the command IDs for adc_read (20), adc_expect (21), pulse_measure (22). */
static bool hil_not_implemented(uint8_t seq, uint8_t cmd_id,
                                bool *already_responded) {
    (void)already_responded;
    REPLY_ERROR_STR(seq, cmd_id, FERQON_ERR_NOT_IMPLEMENTED, FERQON_ECAT_COMMAND,
                    false, 0, "driver method not implemented");
}

static bool hil_adc_read(uint8_t seq, uint8_t cmd_id,
                         const char **keys, const char **values, int arg_count,
                         uint8_t *response, uint8_t *response_len,
                         bool *already_responded) {
    (void)keys; (void)values; (void)arg_count; (void)response; (void)response_len;
    return hil_not_implemented(seq, cmd_id, already_responded);
}

static bool hil_adc_expect(uint8_t seq, uint8_t cmd_id,
                           const char **keys, const char **values, int arg_count,
                           uint8_t *response, uint8_t *response_len,
                           bool *already_responded) {
    (void)keys; (void)values; (void)arg_count; (void)response; (void)response_len;
    return hil_not_implemented(seq, cmd_id, already_responded);
}

static bool hil_pulse_measure(uint8_t seq, uint8_t cmd_id,
                              const char **keys, const char **values, int arg_count,
                              uint8_t *response, uint8_t *response_len,
                              bool *already_responded) {
    (void)keys; (void)values; (void)arg_count; (void)response; (void)response_len;
    return hil_not_implemented(seq, cmd_id, already_responded);
}

static const struct {
    const char *name;
    hil_method_fn fn;
} hil_methods[] = {
#define FERQON_HIL_METHOD_ENTRY(METHOD, FN) { FERQON_DRIVER_METHOD_HIL_##METHOD, FN },
    FERQON_DRIVER_METHODS_HIL(FERQON_HIL_METHOD_ENTRY)
#undef FERQON_HIL_METHOD_ENTRY
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
    (void)response; (void)response_len;
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
    if (p + driver_len > end || driver_len >= DC_MAX_DRIVER_NAME) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "driver name truncated");
    }
    char driver_name[DC_MAX_DRIVER_NAME];
    memcpy(driver_name, p, driver_len);
    driver_name[driver_len] = '\0';
    p += driver_len;

    /* Read method name (length-prefixed) */
    if (p >= end) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "missing method");
    }
    uint8_t method_len = p[0];
    p += 1;
    if (p + method_len > end || method_len >= DC_MAX_METHOD_NAME) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "method name truncated");
    }
    char method_name[DC_MAX_METHOD_NAME];
    memcpy(method_name, p, method_len);
    method_name[method_len] = '\0';
    p += method_len;

    /* Remaining bytes are the args string (key=value;key=value;...) */
    size_t args_len = (size_t)(end - p);
    char args_buf[DC_MAX_ARGS_BUF];
    if (args_len >= sizeof(args_buf)) args_len = sizeof(args_buf) - 1;
    memcpy(args_buf, p, args_len);
    args_buf[args_len] = '\0';

    /* For now, only handle "hil" driver */
    if (strcmp(driver_name, FERQON_DRIVER_NAME_HIL) != 0) {
        FERQON_LOG_DEBUG("DRIVER_CALL unknown driver: %s", driver_name);
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_INVALID_DRIVER, FERQON_ECAT_COMMAND,
                    false, 0, (const uint8_t *)driver_name, (uint8_t)strlen(driver_name));
    }

    const char *keys[DC_MAX_ARGS];
    const char *values[DC_MAX_ARGS];
    int arg_count = parse_args(args_buf, keys, values, DC_MAX_ARGS);
    if (arg_count < 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "malformed args");
    }

    /* Dispatch to the HIL method table. */
    for (uint8_t i = 0; i < hil_method_count; i++) {
        if (strcmp(method_name, hil_methods[i].name) == 0) {
            return hil_methods[i].fn(seq, cmd_id, keys, values, arg_count,
                                     response, response_len, already_responded);
        }
    }

    /* Unknown method. */
    FERQON_LOG_DEBUG("DRIVER_CALL unknown method: %s.%s", driver_name, method_name);
    REPLY_ERROR(seq, cmd_id, FERQON_ERR_INVALID_METHOD, FERQON_ECAT_COMMAND,
                false, 0, (const uint8_t *)method_name, (uint8_t)strlen(method_name));
}

extern "C" const ferqon_driver_t driver_call_driver = {
    .name = "driver_call",
    .id = FERQON_CMD_DRIVER_CALL,
    .cmd_mask = FERQON_DRIVER_CMD_MASK_DRIVER_CALL,
    .handle = driver_call_handler,
};
FERQON_REGISTER_DRIVER(driver_call);
