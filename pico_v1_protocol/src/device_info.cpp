#include "dispatcher.h"
#include "protocol.h"
#include <Arduino.h>
#include <string.h>

// Command IDs (from commands.json)
#define FERQON_CMD_DEVICE_INFO 0x0B

// TLV types
#define TLV_TYPE_DEVICE_NAME 0x01
#define TLV_TYPE_MCU_TYPE 0x02
#define TLV_TYPE_FIRMWARE_VERSION 0x03
#define TLV_TYPE_PROTOCOL_VERSION 0x04
#define TLV_TYPE_BUILD_TIMESTAMP 0x05
#define TLV_TYPE_ENABLED_DRIVERS 0x06
#define TLV_TYPE_SUPPORTED_COMMANDS 0x07
#define TLV_TYPE_FREE_RAM 0x08
#define TLV_TYPE_UPTIME_MS 0x09

static bool device_info_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_DEVICE_INFO) {
        return false;
    }

    uint8_t idx = 0;

    // Device name
    const char *device_name = "pico";
    uint8_t name_len = strlen(device_name);
    response[idx++] = TLV_TYPE_DEVICE_NAME;
    response[idx++] = name_len;
    memcpy(&response[idx], device_name, name_len);
    idx += name_len;

    // MCU type
    const char *mcu_type = "rp2040";
    uint8_t mcu_len = strlen(mcu_type);
    response[idx++] = TLV_TYPE_MCU_TYPE;
    response[idx++] = mcu_len;
    memcpy(&response[idx], mcu_type, mcu_len);
    idx += mcu_len;

    // Firmware version
    const char *fw_version = "1.0.0";
    uint8_t fw_len = strlen(fw_version);
    response[idx++] = TLV_TYPE_FIRMWARE_VERSION;
    response[idx++] = fw_len;
    memcpy(&response[idx], fw_version, fw_len);
    idx += fw_len;

    // Protocol version
    const char *proto_version = "1.0.0";
    uint8_t proto_len = strlen(proto_version);
    response[idx++] = TLV_TYPE_PROTOCOL_VERSION;
    response[idx++] = proto_len;
    memcpy(&response[idx], proto_version, proto_len);
    idx += proto_len;

    // Build timestamp (Unix time - simplified)
    uint32_t timestamp = 0x12345678;  // Placeholder
    response[idx++] = TLV_TYPE_BUILD_TIMESTAMP;
    response[idx++] = 4;
    response[idx++] = timestamp & 0xFF;
    response[idx++] = (timestamp >> 8) & 0xFF;
    response[idx++] = (timestamp >> 16) & 0xFF;
    response[idx++] = (timestamp >> 24) & 0xFF;

    // Free RAM
    uint32_t free_ram = 270336 - 58076;  // Total - used (from build output)
    response[idx++] = TLV_TYPE_FREE_RAM;
    response[idx++] = 4;
    response[idx++] = free_ram & 0xFF;
    response[idx++] = (free_ram >> 8) & 0xFF;
    response[idx++] = (free_ram >> 16) & 0xFF;
    response[idx++] = (free_ram >> 24) & 0xFF;

    // Uptime in ms
    uint32_t uptime = millis();
    response[idx++] = TLV_TYPE_UPTIME_MS;
    response[idx++] = 4;
    response[idx++] = uptime & 0xFF;
    response[idx++] = (uptime >> 8) & 0xFF;
    response[idx++] = (uptime >> 16) & 0xFF;
    response[idx++] = (uptime >> 24) & 0xFF;

    *response_len = idx;
    return true;
}

const ferqon_driver_t device_info_driver = {
    .name = "device_info",
    .id = FERQON_CMD_DEVICE_INFO,
    .handle = device_info_handler
};
