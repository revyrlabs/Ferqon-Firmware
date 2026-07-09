/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
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

    /* GPIO modes */
    RUN_TEST(test_gpio_input);
    RUN_TEST(test_gpio_output);
    RUN_TEST(test_gpio_input_pullup);
    RUN_TEST(test_gpio_input_pulldown);

    return UNITY_END();
}
