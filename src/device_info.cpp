/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include "platform_caps.h"
#include "build_timestamp.h"
#include <Arduino.h>
#include <string.h>

/* Forward declaration of global driver array */
extern ferqon_driver_t g_drivers[];
extern uint8_t g_driver_count;

static uint16_t append_str_tlv(uint8_t *buf, uint8_t type, const char *s, uint16_t max_len) {
    if (max_len < 2) return 0;
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
    buf[2] = (uint8_t)(v & 0xFF);
    buf[3] = (uint8_t)((v >> 8) & 0xFF);
    buf[4] = (uint8_t)((v >> 16) & 0xFF);
    buf[5] = (uint8_t)((v >> 24) & 0xFF);
    return 6;
}

static uint16_t append_signature(uint8_t *buf, uint16_t max_len) {
    const uint8_t magic_len = (uint8_t)(sizeof(FERQON_SIGNATURE_MAGIC) - 1);
    const uint8_t vendor_len = (uint8_t)(sizeof(FERQON_SIGNATURE_VENDOR) - 1);
    const uint8_t total_len = (uint8_t)(1 + magic_len + vendor_len + 1);
    if (max_len < 2 + total_len) return 0;
    buf[0] = TLV_FERQON_SIGNATURE;
    buf[1] = total_len;
    memcpy(&buf[2], FERQON_SIGNATURE_MAGIC, magic_len);
    memcpy(&buf[2 + magic_len], FERQON_SIGNATURE_VENDOR, vendor_len);
    buf[2 + magic_len + vendor_len] = FERQON_SIGNATURE_CAP_VERSION;
    return (uint16_t)(2 + total_len);
}

static bool device_info_handler(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    (void)seq; (void)cmd_id; (void)params; (void)param_len; (void)already_responded;

    uint16_t i = 0;
    const uint16_t cap = FERQON_MAX_PAYLOAD_BYTES;

    i += append_str_tlv(&response[i], TLV_DEVICE_NAME,      FERQON_BOARD_NAME,     cap - i);
    i += append_str_tlv(&response[i], TLV_MCU_TYPE,         FERQON_MCU_FAMILY,     cap - i);
    i += append_str_tlv(&response[i], TLV_FIRMWARE_VERSION, FERQON_FW_VERSION,     cap - i);
    i += append_str_tlv(&response[i], TLV_PROTOCOL_VERSION, FERQON_PROTOCOL_VERSION, cap - i);
    i += append_u32_tlv(&response[i], TLV_BUILD_TIMESTAMP,  FERQON_BUILD_TIMESTAMP, cap - i);
    i += append_u32_tlv(&response[i], TLV_FREE_RAM,         FERQON_RAM_SIZE_BYTES, cap - i);
    i += append_u32_tlv(&response[i], TLV_UPTIME_MS,        (uint32_t)millis(),    cap - i);

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
        i += append_str_tlv(&response[i], TLV_DRIVER, name, cap - i);

        uint16_t name_len = (uint16_t)strlen(name);
        if (name_len > 254) name_len = 254;  /* cmd_id + name must fit in uint8_t length */
        if (i + 3 + name_len > cap) break;

        response[i] = TLV_COMMAND;
        response[i + 1] = (uint8_t)(1 + name_len);
        response[i + 2] = g_drivers[d].id;
        memcpy(&response[i + 3], name, name_len);
        i += (uint16_t)(3 + name_len);
    }

    /* VERSION TLV: type=0x04, len=3, major, minor, patch */
    if (i + 5 <= cap) {
        response[i] = TLV_VERSION;
        response[i + 1] = 3;
        response[i + 2] = 1;  /* major */
        response[i + 3] = 1;  /* minor */
        response[i + 4] = 0;  /* patch */
        i += 5;
    }

    *response_len = (uint8_t)i;
    return true;
}

static bool device_info_dispatch(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    /* Always return true for DEVICE_INFO command */
    if (cmd_id == FERQON_CMD_DEVICE_INFO) {
        return device_info_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
    }
    return false;
}

static bool driver_info_dispatch(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    /* Always return true for DRIVER_INFO command */
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

/* Combined driver that handles both commands for simpler registration */
static bool info_dispatch(uint8_t seq, uint8_t cmd_id,
                         const uint8_t *params, uint8_t param_len,
                         uint8_t *response, uint8_t *response_len,
                         bool *already_responded) {
    if (cmd_id == FERQON_CMD_DEVICE_INFO) {
        return device_info_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
    } else if (cmd_id == FERQON_CMD_DRIVER_INFO) {
        return driver_info_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
    }
    return false;
}

extern "C" const ferqon_driver_t info_driver = {
    .name = "info",
    .id = FERQON_CMD_DEVICE_INFO,  /* Primary ID (can be either) */
    .handle = info_dispatch,
};
