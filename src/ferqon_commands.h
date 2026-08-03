/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Ferqon serial protocol constants.
 *
 * Auto-generated from protocol/ssot/commands.json (v0.1.0).
 * DO NOT EDIT — regenerate with: python3 tools/gen_protocol.py
 */

#ifndef FERQON_COMMANDS_H
#define FERQON_COMMANDS_H

#include <stdint.h>

/* ------------------------------------------------------------------ Frame */

#define FERQON_START_BYTE               0xAB
#define FERQON_MAX_PAYLOAD_BYTES        255
#define FERQON_FRAME_OVERHEAD           6   /* start + seq + cmd + len + crc_lo + crc_hi */
#define FERQON_INTER_BYTE_TIMEOUT_MS    50
#define FERQON_FRAME_ASSEMBLY_TIMEOUT_MS 200

/* CRC-16/CCITT-FALSE */
#define FERQON_CRC_POLY                 0x1021
#define FERQON_CRC_INIT                 0xFFFF

/* Seq=0 is reserved for unsolicited MCU pushes (heartbeat, event, log). */
#define FERQON_SEQ_UNSOLICITED          0

/* Protocol version (from SSOT) */
#define FERQON_PROTOCOL_VERSION         "0.1.0"
#define FERQON_PROTOCOL_VERSION_MAJOR   0
#define FERQON_PROTOCOL_VERSION_MINOR   1
#define FERQON_PROTOCOL_VERSION_PATCH   0

/* --------------------------------------------------------- Packet types */

#define FERQON_PKT_REQUEST              1
#define FERQON_PKT_ACK                  2
#define FERQON_PKT_DONE                 3
#define FERQON_PKT_ERROR                4
#define FERQON_PKT_HEARTBEAT            5
#define FERQON_PKT_EVENT                6
#define FERQON_PKT_LOG                  7

/* ----------------------------------------------------------- Commands */

#define FERQON_CMD_PIN_MODE            1
#define FERQON_CMD_DRIVER_INFO         2
#define FERQON_CMD_DRIVER_CALL         3
#define FERQON_CMD_ECHO                8
#define FERQON_CMD_PING                9
#define FERQON_CMD_RESET               10
#define FERQON_CMD_DEVICE_INFO         11
#define FERQON_CMD_CAPABILITIES        12
#define FERQON_CMD_GPIO_READ           16
#define FERQON_CMD_GPIO_WRITE          17
#define FERQON_CMD_UART_SEND           18
#define FERQON_CMD_UART_EXPECT         19
#define FERQON_CMD_ADC_READ            20
#define FERQON_CMD_ADC_EXPECT          21
#define FERQON_CMD_PULSE_MEASURE       22
#define FERQON_CMD_SET_DEBUG_LEVEL     23

/* ------------------------------------------------ Dispatcher sizing */
#define FERQON_MAX_COMMAND_ID           23
#define FERQON_COMMAND_ID_COUNT         24
#define FERQON_MAX_DRIVERS              12

/* --------------------------------------- Driver command masks (from SSOT) */
/* One bit per command id handled by the named driver.                    */
/* Update the 'driver' field in commands.json, regenerate, and the driver   */
/* definitions automatically claim the right command ids.                   */

#define FERQON_DRIVER_CMD_MASK_ADC             (((uint64_t)1 << FERQON_CMD_ADC_READ) | ((uint64_t)1 << FERQON_CMD_ADC_EXPECT))
#define FERQON_DRIVER_CMD_MASK_CAPABILITIES    ((uint64_t)1 << FERQON_CMD_CAPABILITIES)
#define FERQON_DRIVER_CMD_MASK_DEBUG           ((uint64_t)1 << FERQON_CMD_SET_DEBUG_LEVEL)
#define FERQON_DRIVER_CMD_MASK_DEVICE_INFO     ((uint64_t)1 << FERQON_CMD_DEVICE_INFO)
#define FERQON_DRIVER_CMD_MASK_DRIVER_CALL     ((uint64_t)1 << FERQON_CMD_DRIVER_CALL)
#define FERQON_DRIVER_CMD_MASK_DRIVER_INFO     ((uint64_t)1 << FERQON_CMD_DRIVER_INFO)
#define FERQON_DRIVER_CMD_MASK_ECHO            ((uint64_t)1 << FERQON_CMD_ECHO)
#define FERQON_DRIVER_CMD_MASK_GPIO            (((uint64_t)1 << FERQON_CMD_PIN_MODE) | ((uint64_t)1 << FERQON_CMD_GPIO_READ) | ((uint64_t)1 << FERQON_CMD_GPIO_WRITE))
#define FERQON_DRIVER_CMD_MASK_PING            ((uint64_t)1 << FERQON_CMD_PING)
#define FERQON_DRIVER_CMD_MASK_PULSE           ((uint64_t)1 << FERQON_CMD_PULSE_MEASURE)
#define FERQON_DRIVER_CMD_MASK_RESET           ((uint64_t)1 << FERQON_CMD_RESET)
#define FERQON_DRIVER_CMD_MASK_UART            (((uint64_t)1 << FERQON_CMD_UART_SEND) | ((uint64_t)1 << FERQON_CMD_UART_EXPECT))

/* ------------------------------------------- Driver / method name strings */
/* These match the SSOT so firmware string compares do not drift from the   */
/* protocol spec.  Only drivers/methods declared in commands.json are emitted. */

#define FERQON_DRIVER_NAME_HIL                  "hil"
#define FERQON_DRIVER_METHOD_HIL_ADC_EXPECT           "adc_expect"
#define FERQON_DRIVER_METHOD_HIL_ADC_READ             "adc_read"
#define FERQON_DRIVER_METHOD_HIL_ENTER                "enter"
#define FERQON_DRIVER_METHOD_HIL_EXIT                 "exit"
#define FERQON_DRIVER_METHOD_HIL_IO_CONFIGURE         "io_configure"
#define FERQON_DRIVER_METHOD_HIL_IO_EXPECT            "io_expect"
#define FERQON_DRIVER_METHOD_HIL_IO_GET               "io_get"
#define FERQON_DRIVER_METHOD_HIL_IO_SET               "io_set"
#define FERQON_DRIVER_METHOD_HIL_PULSE_MEASURE        "pulse_measure"
#define FERQON_DRIVER_METHOD_HIL_UART_EXPECT          "uart_expect"
#define FERQON_DRIVER_METHOD_HIL_UART_SEND            "uart_send"


/* ----------------------------------------------- Driver method dispatch tables */
/* X-macros for building the per-driver method dispatch table in driver_call.cpp. */
/* Convention: the C handler for driver 'foo' method 'bar' is named foo_bar.     */

#define FERQON_DRIVER_METHODS_HIL(X)     X(ADC_EXPECT, hil_not_implemented) \
    X(ADC_READ, hil_not_implemented) \
    X(ENTER, hil_enter) \
    X(EXIT, hil_exit) \
    X(IO_CONFIGURE, hil_io_configure) \
    X(IO_EXPECT, hil_io_expect) \
    X(IO_GET, hil_io_get) \
    X(IO_SET, hil_io_set) \
    X(PULSE_MEASURE, hil_not_implemented) \
    X(UART_EXPECT, hil_uart_expect) \
    X(UART_SEND, hil_uart_send)


/* ----------------------------------------------------------- TLV types */
/* NOTE: TLV type IDs are context-dependent. DEVICE_NAME, MCU_TYPE,
 * FIRMWARE_VERSION, PROTOCOL_VERSION, BUILD_TIMESTAMP, FREE_RAM, and
 * UPTIME_MS appear in DEVICE_INFO responses. DRIVER, COMMAND, METHOD,
 * and VERSION appear in DRIVER_INFO responses. Some IDs overlap
 * (e.g. DEVICE_NAME=DRIVER=1) — always use the correct constant for
 * the response context.
 */

#define TLV_DEVICE_NAME                1
#define TLV_DRIVER                     1
#define TLV_MCU_TYPE                   2
#define TLV_COMMAND                    2
#define TLV_FIRMWARE_VERSION           3
#define TLV_METHOD                     3
#define TLV_PROTOCOL_VERSION           4
#define TLV_VERSION                    4
#define TLV_BUILD_TIMESTAMP            5
#define TLV_FREE_RAM                   8
#define TLV_UPTIME_MS                  9
#define TLV_FERQON_SIGNATURE           16

/* -------------------------------------------------- Ferqon signature */

#define FERQON_SIGNATURE_MAGIC         "FERQON"
#define FERQON_SIGNATURE_VENDOR        "revyrlabs"
#define FERQON_SIGNATURE_CAP_VERSION    1

/* ---------------------------------------------------------- GPIO modes */

#define FERQON_GPIO_INPUT                  0
#define FERQON_GPIO_OUTPUT                 1
#define FERQON_GPIO_INPUT_PULLUP           2
#define FERQON_GPIO_INPUT_PULLDOWN         3

#define FERQON_GPIO_MODE_NAME_INPUT      "INPUT"
#define FERQON_GPIO_MODE_NAME_OUTPUT     "OUTPUT"
#define FERQON_GPIO_MODE_NAME_INPUT_PULLUP "INPUT_PULLUP"
#define FERQON_GPIO_MODE_NAME_INPUT_PULLDOWN "INPUT_PULLDOWN"

/* -------------------------------------------------------- App states */

#define FERQON_STATE_APP_BOOT             0
#define FERQON_STATE_APP_READY            1
#define FERQON_STATE_APP_BUSY             2
#define FERQON_STATE_APP_FAULT            3
#define FERQON_STATE_APP_UPDATE           4

/* -------------------------------------------------- Error categories */

#define FERQON_ECAT_NONE                  0
#define FERQON_ECAT_PROTOCOL              1
#define FERQON_ECAT_COMMAND               2
#define FERQON_ECAT_DEVICE                3
#define FERQON_ECAT_INTERNAL              4
#define FERQON_ECAT_TIMEOUT               5

/* ---------------------------------------------------- Error codes */

#define FERQON_ERR_OK                      0  /* Success */
#define FERQON_ERR_INVALID_COMMAND         1  /* Unknown command ID */
#define FERQON_ERR_INVALID_PARAMS          2  /* Invalid parameters */
#define FERQON_ERR_UNSUPPORTED_MODE        3  /* Unsupported mode */
#define FERQON_ERR_UNSUPPORTED_PIN         4  /* Unsupported pin */
#define FERQON_ERR_BUSY                    5  /* Device busy */
#define FERQON_ERR_INTERNAL                6  /* Internal error */
#define FERQON_ERR_CHECKSUM_FAIL           7  /* Checksum mismatch */
#define FERQON_ERR_PAYLOAD_TOO_LARGE       9  /* Payload exceeds max size */
#define FERQON_ERR_TIMEOUT                 10  /* Operation timeout */
#define FERQON_ERR_INVALID_DRIVER          11  /* No driver registered with that name */
#define FERQON_ERR_INVALID_METHOD          12  /* Driver exists but method unknown */
#define FERQON_ERR_NOT_IMPLEMENTED         13  /* Driver/method known but hardware not ready */

#endif /* FERQON_COMMANDS_H */
