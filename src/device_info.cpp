/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include "ferqon_hal.h"
#include "platform_caps.h"
#include "build_timestamp.h"
#include <string.h>
#include <stdint.h>

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

static bool device_info_handler(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    (void)seq; (void)params; (void)param_len; (void)already_responded;
    if (cmd_id != FERQON_CMD_DEVICE_INFO) return false;

    uint16_t i = 0;
    const uint16_t cap = FERQON_MAX_PAYLOAD_BYTES;

    i += append_str_tlv(&response[i], TLV_DEVICE_NAME,      FERQON_BOARD_NAME,       cap - i);
    i += append_str_tlv(&response[i], TLV_MCU_TYPE,         FERQON_MCU_FAMILY,       cap - i);
    i += append_str_tlv(&response[i], TLV_FIRMWARE_VERSION, FERQON_FW_VERSION,       cap - i);
    i += append_str_tlv(&response[i], TLV_PROTOCOL_VERSION, FERQON_PROTOCOL_VERSION, cap - i);
    i += append_u32_tlv(&response[i], TLV_BUILD_TIMESTAMP,  FERQON_BUILD_TIMESTAMP,  cap - i);
    i += append_u32_tlv(&response[i], TLV_FREE_RAM,         ferqon_hal_free_ram_bytes(), cap - i);
    i += append_u32_tlv(&response[i], TLV_UPTIME_MS,        ferqon_hal_uptime_ms(),      cap - i);

    i += append_signature(&response[i], cap - i);

    *response_len = (uint8_t)i;
    return true;
}

static bool driver_info_handler(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    (void)seq; (void)params; (void)param_len; (void)already_responded;
    if (cmd_id != FERQON_CMD_DRIVER_INFO) return false;

    uint16_t i = 0;
    const uint16_t cap = FERQON_MAX_PAYLOAD_BYTES;

    /* Enumerate all registered drivers in deterministic command-id order. */
    uint8_t order[FERQON_MAX_DRIVERS];
    for (uint8_t d = 0; d < g_driver_count; d++) {
        order[d] = d;
    }
    for (uint8_t s = 1; s < g_driver_count; s++) {
        uint8_t j = s;
        while (j > 0 && g_drivers[order[j - 1]].id > g_drivers[order[j]].id) {
            uint8_t tmp = order[j];
            order[j] = order[j - 1];
            order[j - 1] = tmp;
            j--;
        }
    }

    for (uint8_t d = 0; d < g_driver_count; d++) {
        const ferqon_driver_t *drv = &g_drivers[order[d]];
        const char *name = drv->name;
        if (!name) continue;

        uint16_t name_len = (uint16_t)strlen(name);
        if (name_len > 253) name_len = 253;  /* keep within 1-byte length field */

        uint16_t driver_tlv = (uint16_t)(2 + name_len);
        uint16_t command_tlv = (uint16_t)(3 + name_len);
        if (i + driver_tlv + command_tlv > cap) continue;

        i += append_str_tlv(&response[i], TLV_DRIVER, name, cap - i);

        response[i] = TLV_COMMAND;
        response[i + 1] = (uint8_t)(1 + name_len);
        response[i + 2] = drv->id;
        memcpy(&response[i + 3], name, name_len);
        i += command_tlv;
    }

    /* VERSION TLV: type=0x04, len=3, major, minor, patch */
    if (i + 5 <= cap) {
        response[i] = TLV_VERSION;
        response[i + 1] = 3;
        response[i + 2] = FERQON_PROTOCOL_VERSION_MAJOR;
        response[i + 3] = FERQON_PROTOCOL_VERSION_MINOR;
        response[i + 4] = FERQON_PROTOCOL_VERSION_PATCH;
        i += 5;
    }

    *response_len = (uint8_t)i;
    return true;
}

extern "C" const ferqon_driver_t device_info_driver = {
    .name = "device_info",
    .id = FERQON_CMD_DEVICE_INFO,
    .cmd_mask = (uint64_t)1 << FERQON_CMD_DEVICE_INFO,
    .handle = device_info_handler,
};
FERQON_REGISTER_DRIVER(device_info);

extern "C" const ferqon_driver_t driver_info_driver = {
    .name = "driver_info",
    .id = FERQON_CMD_DRIVER_INFO,
    .cmd_mask = (uint64_t)1 << FERQON_CMD_DRIVER_INFO,
    .handle = driver_info_handler,
};
FERQON_REGISTER_DRIVER(driver_info);
