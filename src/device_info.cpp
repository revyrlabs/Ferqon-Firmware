#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include <Arduino.h>
#include <string.h>

/* Forward declaration of global driver array */
extern ferqon_driver_t g_drivers[];
extern uint8_t g_driver_count;

static uint8_t append_str_tlv(uint8_t *buf, uint8_t type, const char *s) {
    uint8_t n = (uint8_t)strlen(s);
    buf[0] = type;
    buf[1] = n;
    memcpy(&buf[2], s, n);
    return (uint8_t)(2 + n);
}

static uint8_t append_u32_tlv(uint8_t *buf, uint8_t type, uint32_t v) {
    buf[0] = type;
    buf[1] = 4;
    buf[2] = (uint8_t)(v & 0xFF);
    buf[3] = (uint8_t)((v >> 8) & 0xFF);
    buf[4] = (uint8_t)((v >> 16) & 0xFF);
    buf[5] = (uint8_t)((v >> 24) & 0xFF);
    return 6;
}

static bool device_info_handler(uint8_t seq, uint8_t cmd_id,
                                const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len,
                                bool *already_responded) {
    (void)seq; (void)cmd_id; (void)params; (void)param_len;

    /* Set already_responded to true to prevent dispatcher from calling ferqon_send_done */
    *already_responded = true;

    uint8_t i = 0;
    i += append_str_tlv(&response[i], TLV_DEVICE_NAME,      "pico");
    i += append_str_tlv(&response[i], TLV_MCU_TYPE,         "rp2040");
    i += append_str_tlv(&response[i], TLV_FIRMWARE_VERSION, "1.1.0");
    i += append_str_tlv(&response[i], TLV_PROTOCOL_VERSION, "1.1.0");
    i += append_u32_tlv(&response[i], TLV_BUILD_TIMESTAMP,  0x12345678UL);
    i += append_u32_tlv(&response[i], TLV_FREE_RAM,         (uint32_t)(270336 - 58076));
    i += append_u32_tlv(&response[i], TLV_UPTIME_MS,        (uint32_t)millis());

    /* Ferqon signature TLV: magic + vendor + capability_version */
    /* Format: magic (6) + vendor (9) + cap_version (1) = 16 bytes total */
    response[i] = TLV_FERQON_SIGNATURE;
    response[i + 1] = 16;  /* length */
    memcpy(&response[i + 2], FERQON_SIGNATURE_MAGIC, 6);
    memcpy(&response[i + 8], FERQON_SIGNATURE_VENDOR, 9);
    response[i + 17] = FERQON_SIGNATURE_CAP_VERSION;
    i += 18;

    *response_len = i;
    
    /* Call ferqon_send_done directly with the response */
    ferqon_send_done(seq, cmd_id, response, i);
    
    return true;
}

static bool driver_info_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    (void)seq; (void)cmd_id; (void)params; (void)param_len; (void)already_responded;

    uint8_t i = 0;

    /* Enumerate all registered drivers */
    for (uint8_t d = 0; d < g_driver_count; d++) {
        /* DRIVER TLV: type=0x01, len, null-term driver name */
        i += append_str_tlv(&response[i], TLV_DRIVER, g_drivers[d].name);

        /* COMMAND TLV: type=0x02, len=1+name_len, cmd_id, null-term name */
        response[i] = TLV_COMMAND;
        response[i + 1] = 1 + strlen(g_drivers[d].name);  /* cmd_id + name */
        response[i + 2] = g_drivers[d].id;
        strcpy((char *)&response[i + 3], g_drivers[d].name);
        i += 3 + strlen(g_drivers[d].name);

        /* For now, skip METHOD TLVs - they require metadata not yet available */
    }

    /* VERSION TLV: type=0x04, len=3, major, minor, patch */
    response[i] = TLV_VERSION;
    response[i + 1] = 3;
    response[i + 2] = 1;  /* major */
    response[i + 3] = 1;  /* minor */
    response[i + 4] = 0;  /* patch */
    i += 5;

    *response_len = i;
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
