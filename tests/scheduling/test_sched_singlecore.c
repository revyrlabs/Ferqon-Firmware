/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/**
 * test_sched_singlecore.c
 * -----------------------
 * Unit tests for ferqon_sched_singlecore.c — the UART RX ISR ring buffer path.
 *
 * Built on the native host with FERQON_SCHED_UART_ISR=1 and
 * FERQON_ISR_RINGBUF_SIZE=256 injected by the native_singlecore env.
 */

#include "unity.h"
#include "scheduling/ferqon_sched.h"
#include "protocol.h"

/* ── Spy for frame parser ─────────────────────────────────────────────── */

/* We need to control what FERQON_Protocol_FrameFeedByte returns so we can
 * simulate complete frames. Use a simple counter: after N bytes we emit
 * a complete frame (return 2). */
static int g_bytes_until_frame = -1; /* -1 = never emit a frame */
static int g_feed_count        = 0;
static int g_dispatch_count    = 0;

uint8_t __wrap_FERQON_Protocol_FrameFeedByte(uint8_t byte,
                                            FERQON_RuntimeRequest_t* out)
{
    (void)byte;
    g_feed_count++;
    if (g_bytes_until_frame > 0 && g_feed_count >= g_bytes_until_frame) {
        g_feed_count = 0;
        out->cmd_id = 0x0042;
        out->transport = 1;
        out->call_name[0] = '\0';
        out->driver_name[0] = '\0';
        out->payload[0] = '\0';
        return 2; /* complete frame */
    }
    return 1; /* still building */
}

bool __wrap_FERQON_Drivers_HandleRequest(const FERQON_RuntimeRequest_t* req)
{
    (void)req;
    g_dispatch_count++;
    return true;
}

void setUp(void)
{
    g_bytes_until_frame = -1;
    g_feed_count        = 0;
    g_dispatch_count    = 0;
    ferqon_sched_init();
}

void tearDown(void) {}

/* ── ISR push + drain dispatches ─────────────────────────────────────── */

void test_isr_push_drain_no_frame(void)
{
    /* Push bytes that don't complete a frame — drain should not dispatch. */
    ferqon_sched_isr_push_byte(0xA5);
    ferqon_sched_isr_push_byte(0x5A);
    ferqon_sched_drain_and_dispatch();
    TEST_ASSERT_EQUAL_INT(0, g_dispatch_count);
}

void test_isr_push_drain_completes_frame(void)
{
    g_bytes_until_frame = 3; /* frame completes after 3rd byte */

    ferqon_sched_isr_push_byte(0xA5);
    ferqon_sched_isr_push_byte(0x5A);
    ferqon_sched_isr_push_byte(0x01);
    ferqon_sched_drain_and_dispatch();
    TEST_ASSERT_EQUAL_INT(1, g_dispatch_count);
}

void test_multiple_frames_in_one_drain(void)
{
    g_bytes_until_frame = 2; /* frame every 2 bytes */

    /* Push 6 bytes → 3 frames */
    for (int i = 0; i < 6; i++) {
        ferqon_sched_isr_push_byte((uint8_t)i);
    }
    ferqon_sched_drain_and_dispatch();
    TEST_ASSERT_EQUAL_INT(3, g_dispatch_count);
}

void test_drain_empty_buffer_is_safe(void)
{
    /* No bytes pushed — must not crash or dispatch anything. */
    ferqon_sched_drain_and_dispatch();
    TEST_ASSERT_EQUAL_INT(0, g_dispatch_count);
}

void test_bytes_survive_across_drain_calls(void)
{
    g_bytes_until_frame = 4;

    /* Push 2 bytes, drain — no complete frame yet. */
    ferqon_sched_isr_push_byte(0x01);
    ferqon_sched_isr_push_byte(0x02);
    ferqon_sched_drain_and_dispatch();
    TEST_ASSERT_EQUAL_INT(0, g_dispatch_count);

    /* Push 2 more bytes, drain — frame completes. */
    ferqon_sched_isr_push_byte(0x03);
    ferqon_sched_isr_push_byte(0x04);
    ferqon_sched_drain_and_dispatch();
    TEST_ASSERT_EQUAL_INT(1, g_dispatch_count);
}

/* ── Entry point ───────────────────────────────────────────────────────── */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_isr_push_drain_no_frame);
    RUN_TEST(test_isr_push_drain_completes_frame);
    RUN_TEST(test_multiple_frames_in_one_drain);
    RUN_TEST(test_drain_empty_buffer_is_safe);
    RUN_TEST(test_bytes_survive_across_drain_calls);

    return UNITY_END();
}
