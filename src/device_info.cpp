/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include "platform_caps.h"
#include "build_timestamp.h"
#include <Arduino.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>

#ifdef __MBED__
#include <platform/mbed_stats.h>
#endif

/* Forward declaration of global driver array */
extern ferqon_driver_t g_drivers[];
extern uint8_t g_driver_count;

static uint16_t append_str_tlv(uint8_t *buf, uint8_t type, const char *s, uint16_t max_len) {
    if (max_len < 2 || !s) return 0;
    uint16_t n = (uint16_t)strlen(s);
    uint16_t max_val = max_len - 2;
    if (n > max_val) n = max_val;
    if (n > 255) n = 255;  /* TLV length field is one byte */
    buf[0] = type;
    buf[1] = (uint8_t)n;
    memcpy(&buf[2], s, n);
    return (uint16_t)(2 + n);
}

static uint16_t append_u32_tlv(uint8_t *buf, uint8_t type, uint32_t v, uint16_t max_len) {
    if (max_len < 6) return 0;
    buf[0] = type;
    buf[1] = 4;
    wr_u32_le(&buf[2], v);
    return 6;
}

static uint16_t append_signature(uint8_t *buf, uint16_t max_len) {
    const uint8_t magic_len = (uint8_t)(sizeof(FERQON_SIGNATURE_MAGIC) - 1);
    const uint8_t vendor_len = (uint8_t)(sizeof(FERQON_SIGNATURE_VENDOR) - 1);
    const uint16_t total_len = (uint16_t)(1 + magic_len + vendor_len + 1);
    if (max_len < 2 + total_len || total_len > 255) return 0;
    buf[0] = TLV_FERQON_SIGNATURE;
    buf[1] = (uint8_t)total_len;
    memcpy(&buf[2], FERQON_SIGNATURE_MAGIC, magic_len);
    memcpy(&buf[2 + magic_len], FERQON_SIGNATURE_VENDOR, vendor_len);
    buf[2 + magic_len + vendor_len] = FERQON_SIGNATURE_CAP_VERSION;
    return (uint16_t)(2 + total_len);
}

static uint32_t get_free_ram(void) {
#ifdef __MBED__
#if MBED_HEAP_STATS_ENABLED
    mbed_stats_heap_t stats;
    mbed_stats_heap_get(&stats);
    uint32_t used = stats.current_size + stats.overhead_size;
    return (stats.reserved_size > used) ? (stats.reserved_size - used) : 0;
#else
    return FERQON_RAM_SIZE_BYTES;
#endif
#elif defined(ESP32) || defined(ESP8266)
    return ESP.getFreeHeap();
#else
    return FERQON_RAM_SIZE_BYTES;
#endif
}

static bool parse_version(const char *version, uint8_t *major, uint8_t *minor, uint8_t *patch) {
    *major = *minor = *patch = 0;
    if (!version) return false;
    unsigned int maj = 0, min = 0, pat = 0;
    if (sscanf(version, "%u.%u.%u", &maj, &min, &pat) != 3) {
        return false;
    }
    if (maj > 255 || min > 255 || pat > 255) {
        return false;
    }
    *major = (uint8_t)maj;
    *minor = (uint8_t)min;
    *patch = (uint8_t)pat;
    return true;
}

static bool device_info_handler(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    (void)seq; (void)cmd_id; (void)params; (void)param_len; (void)already_responded;

    uint16_t i = 0;
    const uint16_t cap = FERQON_MAX_PAYLOAD_BYTES;

    i += append_str_tlv(&response[i], TLV_DEVICE_NAME,      FERQON_BOARD_NAME,       cap - i);
    i += append_str_tlv(&response[i], TLV_MCU_TYPE,         FERQON_MCU_FAMILY,       cap - i);
    i += append_str_tlv(&response[i], TLV_FIRMWARE_VERSION, FERQON_FW_VERSION,       cap - i);
    i += append_str_tlv(&response[i], TLV_PROTOCOL_VERSION, FERQON_PROTOCOL_VERSION, cap - i);
    i += append_u32_tlv(&response[i], TLV_BUILD_TIMESTAMP,  FERQON_BUILD_TIMESTAMP,  cap - i);
    i += append_u32_tlv(&response[i], TLV_FREE_RAM,         get_free_ram(),          cap - i);
    i += append_u32_tlv(&response[i], TLV_UPTIME_MS,        (uint32_t)millis(),      cap - i);

    i += append_signature(&response[i], cap - i);

    *response_len = (uint8_t)i;
    return true;
}

static bool driver_info_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    (void)seq; (void)cmd_id; (void)params; (void)param_len; (void)already_responded;

    uint16_t i = 0;
    const uint16_t cap = FERQON_MAX_PAYLOAD_BYTES;

    /* Enumerate all registered drivers */
    for (uint8_t d = 0; d < g_driver_count; d++) {
        const char *name = g_drivers[d].name;
        if (!name) continue;

        uint16_t name_len = (uint16_t)strlen(name);
        if (name_len > 253) name_len = 253;  /* keep within 1-byte length field */

        uint16_t driver_tlv = (uint16_t)(2 + name_len);
        uint16_t command_tlv = (uint16_t)(3 + name_len);
        if (i + driver_tlv + command_tlv > cap) continue;

        i += append_str_tlv(&response[i], TLV_DRIVER, name, cap - i);

        response[i] = TLV_COMMAND;
        response[i + 1] = (uint8_t)(1 + name_len);
        response[i + 2] = g_drivers[d].id;
        memcpy(&response[i + 3], name, name_len);
        i += command_tlv;
    }

    /* VERSION TLV: type=0x04, len=3, major, minor, patch */
    uint8_t major = 0, minor = 0, patch = 0;
    parse_version(FERQON_PROTOCOL_VERSION, &major, &minor, &patch);
    if (i + 5 <= cap) {
        response[i] = TLV_VERSION;
        response[i + 1] = 3;
        response[i + 2] = major;
        response[i + 3] = minor;
        response[i + 4] = patch;
        i += 5;
    }

    *response_len = (uint8_t)i;
    return true;
}

static bool device_info_dispatch(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    if (cmd_id == FERQON_CMD_DEVICE_INFO) {
        return device_info_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
    }
    return false;
}

static bool driver_info_dispatch(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    if (cmd_id == FERQON_CMD_DRIVER_INFO) {
        return driver_info_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
    }
    return false;
}

extern "C" const ferqon_driver_t device_info_driver = {
    .name = "device_info",
    .id = FERQON_CMD_DEVICE_INFO,
    .handle = device_info_dispatch,
};

extern "C" const ferqon_driver_t driver_info_driver = {
    .name = "driver_info",
    .id = FERQON_CMD_DRIVER_INFO,
    .handle = driver_info_dispatch,
};
