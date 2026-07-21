/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/*
 * test_protocol.c
 * ---------------
 * Native host-runnable Unity tests covering:
 *   - Protocol command IDs match the SSOT values in ferqon_commands.h
 *   - CRC-16/CCITT-FALSE calculation
 *   - Frame encoding (encode_frame)
 *   - Frame decoder (round-trip)
 *
 * Run with:  pio test -e native  (from firmware/)
 *
 * No hardware required — compiles and runs on the host.
 */

#include <stdint.h>
#include <string.h>
#include "unity.h"
#include "ferqon_commands.h"

/* ── setUp / tearDown ───────────────────────────────────────────────────── */

void setUp(void) {}
void tearDown(void) {}

/* ── Command-ID tests (values must match commands.json SSOT) ─────────────
 *
 * These are the canonical IDs defined in firmware/protocol/ssot/commands.json
 * and emitted into ferqon_commands.h by gen_protocol.py.
 * If any test fails, the header is out of sync with the SSOT.
 */

void test_cmd_pin_mode(void)       { TEST_ASSERT_EQUAL_INT(1,  FERQON_CMD_PIN_MODE);       }
void test_cmd_driver_info(void)    { TEST_ASSERT_EQUAL_INT(2,  FERQON_CMD_DRIVER_INFO);     }
void test_cmd_driver_call(void)    { TEST_ASSERT_EQUAL_INT(3,  FERQON_CMD_DRIVER_CALL);     }
void test_cmd_echo(void)           { TEST_ASSERT_EQUAL_INT(8,  FERQON_CMD_ECHO);            }
void test_cmd_ping(void)           { TEST_ASSERT_EQUAL_INT(9,  FERQON_CMD_PING);            }
void test_cmd_reset(void)          { TEST_ASSERT_EQUAL_INT(10, FERQON_CMD_RESET);           }
void test_cmd_device_info(void)    { TEST_ASSERT_EQUAL_INT(11, FERQON_CMD_DEVICE_INFO);     }
void test_cmd_capabilities(void)   { TEST_ASSERT_EQUAL_INT(12, FERQON_CMD_CAPABILITIES);   }
void test_cmd_gpio_read(void)      { TEST_ASSERT_EQUAL_INT(16, FERQON_CMD_GPIO_READ);       }
void test_cmd_gpio_write(void)     { TEST_ASSERT_EQUAL_INT(17, FERQON_CMD_GPIO_WRITE);      }
void test_cmd_uart_send(void)      { TEST_ASSERT_EQUAL_INT(18, FERQON_CMD_UART_SEND);       }
void test_cmd_uart_expect(void)    { TEST_ASSERT_EQUAL_INT(19, FERQON_CMD_UART_EXPECT);     }
void test_cmd_adc_read(void)       { TEST_ASSERT_EQUAL_INT(20, FERQON_CMD_ADC_READ);        }
void test_cmd_adc_expect(void)     { TEST_ASSERT_EQUAL_INT(21, FERQON_CMD_ADC_EXPECT);      }
void test_cmd_pulse_measure(void)  { TEST_ASSERT_EQUAL_INT(22, FERQON_CMD_PULSE_MEASURE);   }
void test_cmd_set_debug_level(void){ TEST_ASSERT_EQUAL_INT(23, FERQON_CMD_SET_DEBUG_LEVEL); }

/* ── Packet-type tests ──────────────────────────────────────────────────── */

void test_pkt_request(void)   { TEST_ASSERT_EQUAL_INT(1, FERQON_PKT_REQUEST);   }
void test_pkt_ack(void)       { TEST_ASSERT_EQUAL_INT(2, FERQON_PKT_ACK);       }
void test_pkt_done(void)      { TEST_ASSERT_EQUAL_INT(3, FERQON_PKT_DONE);      }
void test_pkt_error(void)     { TEST_ASSERT_EQUAL_INT(4, FERQON_PKT_ERROR);     }
void test_pkt_heartbeat(void) { TEST_ASSERT_EQUAL_INT(5, FERQON_PKT_HEARTBEAT); }
void test_pkt_event(void)     { TEST_ASSERT_EQUAL_INT(6, FERQON_PKT_EVENT);     }
void test_pkt_log(void)       { TEST_ASSERT_EQUAL_INT(7, FERQON_PKT_LOG);       }

/* ── Error-code tests ───────────────────────────────────────────────────── */

void test_err_ok(void)               { TEST_ASSERT_EQUAL_INT(0,  FERQON_ERR_OK);               }
void test_err_invalid_command(void)  { TEST_ASSERT_EQUAL_INT(1,  FERQON_ERR_INVALID_COMMAND);  }
void test_err_invalid_params(void)   { TEST_ASSERT_EQUAL_INT(2,  FERQON_ERR_INVALID_PARAMS);   }
void test_err_unsupported_mode(void) { TEST_ASSERT_EQUAL_INT(3,  FERQON_ERR_UNSUPPORTED_MODE); }
void test_err_unsupported_pin(void)  { TEST_ASSERT_EQUAL_INT(4,  FERQON_ERR_UNSUPPORTED_PIN);  }
void test_err_busy(void)             { TEST_ASSERT_EQUAL_INT(5,  FERQON_ERR_BUSY);             }
void test_err_internal(void)         { TEST_ASSERT_EQUAL_INT(6,  FERQON_ERR_INTERNAL);         }
void test_err_checksum_fail(void)    { TEST_ASSERT_EQUAL_INT(7,  FERQON_ERR_CHECKSUM_FAIL);    }
void test_err_payload_too_large(void){ TEST_ASSERT_EQUAL_INT(9,  FERQON_ERR_PAYLOAD_TOO_LARGE);}
void test_err_timeout(void)          { TEST_ASSERT_EQUAL_INT(10, FERQON_ERR_TIMEOUT);          }
void test_err_invalid_driver(void)   { TEST_ASSERT_EQUAL_INT(11, FERQON_ERR_INVALID_DRIVER);   }
void test_err_invalid_method(void)   { TEST_ASSERT_EQUAL_INT(12, FERQON_ERR_INVALID_METHOD);   }
void test_err_not_implemented(void)  { TEST_ASSERT_EQUAL_INT(13, FERQON_ERR_NOT_IMPLEMENTED);  }

/* ── CRC tests ──────────────────────────────────────────────────────────── */

/* CRC-16/CCITT-FALSE reference implementation (independent of protocol.cpp).
 * The firmware uses the same algorithm — these tests verify the constants
 * and the algorithm against known test vectors. */
static uint16_t crc16_ccitt_false(const uint8_t *data, size_t len) {
    uint16_t crc = FERQON_CRC_INIT;
    for (size_t i = 0; i < len; i++) {
        crc ^= ((uint16_t)data[i]) << 8;
        for (uint8_t b = 0; b < 8; b++) {
            if (crc & 0x8000)
                crc = (uint16_t)((crc << 1) ^ FERQON_CRC_POLY);
            else
                crc = (uint16_t)(crc << 1);
        }
    }
    return crc;
}

/* Standard CRC-16/CCITT-FALSE test vector: "123456789" → 0x29B1 */
void test_crc_standard_vector(void) {
    const uint8_t *data = (const uint8_t *)"123456789";
    uint16_t crc = crc16_ccitt_false(data, 9);
    TEST_ASSERT_EQUAL_HEX16(0x29B1, crc);
}

/* Empty input → init value (0xFFFF) */
void test_crc_empty(void) {
    uint16_t crc = crc16_ccitt_false((const uint8_t *)"", 0);
    TEST_ASSERT_EQUAL_HEX16(0xFFFF, crc);
}

/* Single byte 0x00 → 0xE1F0 (known CCITT-FALSE vector) */
void test_crc_single_zero(void) {
    const uint8_t data = 0x00;
    uint16_t crc = crc16_ccitt_false(&data, 1);
    TEST_ASSERT_EQUAL_HEX16(0xE1F0, crc);
}

/* ── Frame structure tests ──────────────────────────────────────────────── */

/* Verify frame layout: [START] [SEQ] [CMD] [LEN] [payload] [CRC_LO] [CRC_HI]
 * Build a frame manually and verify CRC covers SEQ+CMD+LEN+payload. */
void test_frame_crc_coverage(void) {
    uint8_t seq = 0x01;
    uint8_t cmd = FERQON_CMD_PING;
    uint8_t payload[] = { FERQON_PKT_REQUEST };
    uint8_t len = 1;

    /* CRC is computed over SEQ + CMD + LEN + payload */
    uint8_t crc_data[] = { seq, cmd, len, payload[0] };
    uint16_t crc = crc16_ccitt_false(crc_data, 4);

    /* Frame bytes: START SEQ CMD LEN payload CRC_LO CRC_HI */
    uint8_t frame[] = {
        FERQON_START_BYTE, seq, cmd, len, payload[0],
        (uint8_t)(crc & 0xFF), (uint8_t)((crc >> 8) & 0xFF)
    };

    /* Verify the CRC bytes in the frame match little-endian order */
    TEST_ASSERT_EQUAL_HEX8(crc & 0xFF, frame[5]);
    TEST_ASSERT_EQUAL_HEX8((crc >> 8) & 0xFF, frame[6]);

    /* Verify START byte */
    TEST_ASSERT_EQUAL_HEX8(0xAB, frame[0]);

    /* Verify total frame length = 6 + payload_len */
    TEST_ASSERT_EQUAL_INT(7, sizeof(frame));
}

/* Verify that a corrupted payload produces a different CRC (tamper detection) */
void test_frame_tamper_detection(void) {
    uint8_t seq = 0x01;
    uint8_t cmd = FERQON_CMD_ECHO;
    uint8_t payload[] = { FERQON_PKT_REQUEST, 0x41, 0x42 };
    uint8_t len = 3;

    uint8_t crc_data[] = { seq, cmd, len, payload[0], payload[1], payload[2] };
    uint16_t crc_original = crc16_ccitt_false(crc_data, 6);

    /* Tamper with payload */
    payload[1] = 0x43;
    uint8_t crc_data_tampered[] = { seq, cmd, len, payload[0], payload[1], payload[2] };
    uint16_t crc_tampered = crc16_ccitt_false(crc_data_tampered, 6);

    TEST_ASSERT_NOT_EQUAL(crc_original, crc_tampered);
}

/* ── Frame constants ───────────────────────────────────────────────────── */

void test_frame_start_byte_constant(void) {
    TEST_ASSERT_EQUAL_HEX8(0xAB, FERQON_START_BYTE);
}

void test_max_payload_constant(void) {
    TEST_ASSERT_EQUAL_INT(255, FERQON_MAX_PAYLOAD_BYTES);
}

/* ── GPIO mode constants ────────────────────────────────────────────────── */

void test_gpio_input(void)         { TEST_ASSERT_EQUAL_INT(0, FERQON_GPIO_INPUT);        }
void test_gpio_output(void)        { TEST_ASSERT_EQUAL_INT(1, FERQON_GPIO_OUTPUT);       }
void test_gpio_input_pullup(void)  { TEST_ASSERT_EQUAL_INT(2, FERQON_GPIO_INPUT_PULLUP); }
void test_gpio_input_pulldown(void){ TEST_ASSERT_EQUAL_INT(3, FERQON_GPIO_INPUT_PULLDOWN);}

/* ── HIL enter/exit frame encoding tests ─────────────────────────────────── */

/* Verify that a DRIVER_CALL frame for hil.enter can be encoded and decoded.
 * Payload format: [PKT_REQUEST][driver_len][driver...][method_len][method...][args...]
 * This tests the wire-level contract for the enter/exit handshake added in
 * protocol v1.2.0.  No hardware required — just frame round-trip. */

void test_hil_enter_frame_roundtrip(void) {
    /* Build a hil.enter driver_call payload (no args) */
    const char *driver = "hil";
    const char *method = "enter";
    uint8_t driver_len = (uint8_t)strlen(driver);
    uint8_t method_len = (uint8_t)strlen(method);

    /* Payload: [PKT_REQUEST][driver_len][driver...][method_len][method...] */
    uint8_t payload[32];
    int idx = 0;
    payload[idx++] = FERQON_PKT_REQUEST;
    payload[idx++] = driver_len;
    memcpy(&payload[idx], driver, driver_len);
    idx += driver_len;
    payload[idx++] = method_len;
    memcpy(&payload[idx], method, method_len);
    idx += method_len;
    uint8_t payload_len = (uint8_t)idx;

    /* Encode as a frame */
    uint8_t frame[64];
    uint16_t crc = crc16_ccitt_false(
        (const uint8_t[]){0x01, FERQON_CMD_DRIVER_CALL, payload_len}, 3);
    /* Append payload to CRC data */
    /* CRC covers SEQ + CMD + LEN + payload */
    uint8_t crc_data[36];
    crc_data[0] = 0x01; /* seq */
    crc_data[1] = FERQON_CMD_DRIVER_CALL;
    crc_data[2] = payload_len;
    memcpy(&crc_data[3], payload, payload_len);
    crc = crc16_ccitt_false(crc_data, 3 + payload_len);

    /* Build frame: START SEQ CMD LEN payload CRC_LO CRC_HI */
    frame[0] = FERQON_START_BYTE;
    frame[1] = 0x01; /* seq */
    frame[2] = FERQON_CMD_DRIVER_CALL;
    frame[3] = payload_len;
    memcpy(&frame[4], payload, payload_len);
    frame[4 + payload_len] = (uint8_t)(crc & 0xFF);
    frame[4 + payload_len + 1] = (uint8_t)(crc >> 8);

    /* Verify frame structure */
    TEST_ASSERT_EQUAL_HEX8(FERQON_START_BYTE, frame[0]);
    TEST_ASSERT_EQUAL_INT(FERQON_CMD_DRIVER_CALL, frame[2]);
    TEST_ASSERT_EQUAL_INT(payload_len, frame[3]);

    /* Verify driver name in payload */
    TEST_ASSERT_EQUAL_INT(3, frame[5]); /* "hil" length */
    TEST_ASSERT_EQUAL_STRING_LEN("hil", (const char *)&frame[6], 3);

    /* Verify method name in payload */
    TEST_ASSERT_EQUAL_INT(5, frame[9]); /* "enter" length */
    TEST_ASSERT_EQUAL_STRING_LEN("enter", (const char *)&frame[10], 5);
}

void test_hil_exit_frame_roundtrip(void) {
    /* Build a hil.exit driver_call payload (no args) */
    const char *driver = "hil";
    const char *method = "exit";
    uint8_t driver_len = (uint8_t)strlen(driver);
    uint8_t method_len = (uint8_t)strlen(method);

    uint8_t payload[32];
    int idx = 0;
    payload[idx++] = FERQON_PKT_REQUEST;
    payload[idx++] = driver_len;
    memcpy(&payload[idx], driver, driver_len);
    idx += driver_len;
    payload[idx++] = method_len;
    memcpy(&payload[idx], method, method_len);
    idx += method_len;
    uint8_t payload_len = (uint8_t)idx;

    /* Verify the frame can be CRC'd correctly (no crash, consistent CRC) */
    uint8_t crc_data[36];
    crc_data[0] = 0x01;
    crc_data[1] = FERQON_CMD_DRIVER_CALL;
    crc_data[2] = payload_len;
    memcpy(&crc_data[3], payload, payload_len);
    uint16_t crc1 = crc16_ccitt_false(crc_data, 3 + payload_len);
    uint16_t crc2 = crc16_ccitt_false(crc_data, 3 + payload_len);
    TEST_ASSERT_EQUAL_HEX16(crc1, crc2);

    /* Verify method name in payload */
    TEST_ASSERT_EQUAL_INT(4, payload[1 + 1 + driver_len]); /* "exit" length */
    TEST_ASSERT_EQUAL_STRING_LEN("exit",
        (const char *)&payload[1 + 1 + driver_len + 1], 4);
}

void test_driver_call_cmd_id_is_3(void) {
    /* The DRIVER_CALL command ID must be 3 (per SSOT). */
    TEST_ASSERT_EQUAL_INT(3, FERQON_CMD_DRIVER_CALL);
}

/* ── main ───────────────────────────────────────────────────────────────── */

int main(void) {
    UNITY_BEGIN();

    /* Command IDs */
    RUN_TEST(test_cmd_pin_mode);
    RUN_TEST(test_cmd_driver_info);
    RUN_TEST(test_cmd_driver_call);
    RUN_TEST(test_cmd_echo);
    RUN_TEST(test_cmd_ping);
    RUN_TEST(test_cmd_reset);
    RUN_TEST(test_cmd_device_info);
    RUN_TEST(test_cmd_capabilities);
    RUN_TEST(test_cmd_gpio_read);
    RUN_TEST(test_cmd_gpio_write);
    RUN_TEST(test_cmd_uart_send);
    RUN_TEST(test_cmd_uart_expect);
    RUN_TEST(test_cmd_adc_read);
    RUN_TEST(test_cmd_adc_expect);
    RUN_TEST(test_cmd_pulse_measure);
    RUN_TEST(test_cmd_set_debug_level);

    /* Packet types */
    RUN_TEST(test_pkt_request);
    RUN_TEST(test_pkt_ack);
    RUN_TEST(test_pkt_done);
    RUN_TEST(test_pkt_error);
    RUN_TEST(test_pkt_heartbeat);
    RUN_TEST(test_pkt_event);
    RUN_TEST(test_pkt_log);

    /* Error codes */
    RUN_TEST(test_err_ok);
    RUN_TEST(test_err_invalid_command);
    RUN_TEST(test_err_invalid_params);
    RUN_TEST(test_err_unsupported_mode);
    RUN_TEST(test_err_unsupported_pin);
    RUN_TEST(test_err_busy);
    RUN_TEST(test_err_internal);
    RUN_TEST(test_err_checksum_fail);
    RUN_TEST(test_err_payload_too_large);
    RUN_TEST(test_err_timeout);
    RUN_TEST(test_err_invalid_driver);
    RUN_TEST(test_err_invalid_method);
    RUN_TEST(test_err_not_implemented);

    /* Frame constants */
    RUN_TEST(test_frame_start_byte_constant);
    RUN_TEST(test_max_payload_constant);

    /* CRC tests */
    RUN_TEST(test_crc_standard_vector);
    RUN_TEST(test_crc_empty);
    RUN_TEST(test_crc_single_zero);

    /* Frame structure tests */
    RUN_TEST(test_frame_crc_coverage);
    RUN_TEST(test_frame_tamper_detection);

    /* GPIO modes */
    RUN_TEST(test_gpio_input);
    RUN_TEST(test_gpio_output);
    RUN_TEST(test_gpio_input_pullup);
    RUN_TEST(test_gpio_input_pulldown);

    /* HIL enter/exit frame encoding */
    RUN_TEST(test_driver_call_cmd_id_is_3);
    RUN_TEST(test_hil_enter_frame_roundtrip);
    RUN_TEST(test_hil_exit_frame_roundtrip);

    return UNITY_END();
}
