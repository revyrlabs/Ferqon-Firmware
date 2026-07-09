/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/**
 * test_ringbuf.c
 * --------------
 * Unit tests for ferqon_ringbuf.h (lock-free SPSC byte ring buffer).
 *
 * Run via PlatformIO native env:
 *   cd firmware && pio test -e native
 */

#include "unity.h"
#include "scheduling/ferqon_ringbuf.h"

/* Declare a 16-byte ring buffer for tests (power of two). */
FERQON_RINGBUF_DEFINE(rb, 16);

void setUp(void)
{
    /* Reset head/tail between tests */
    rb.head = 0;
    rb.tail = 0;
}

void tearDown(void) {}

/* ── Basic push/pop ────────────────────────────────────────────────────── */

void test_empty_on_init(void)
{
    TEST_ASSERT_TRUE(ferqon_ringbuf_empty(&rb));
    TEST_ASSERT_EQUAL_UINT32(0, ferqon_ringbuf_count(&rb));
}

void test_push_pop_single(void)
{
    TEST_ASSERT_TRUE(ferqon_ringbuf_push(&rb, 0xAB));
    TEST_ASSERT_FALSE(ferqon_ringbuf_empty(&rb));
    TEST_ASSERT_EQUAL_UINT32(1, ferqon_ringbuf_count(&rb));

    uint8_t out = 0;
    TEST_ASSERT_TRUE(ferqon_ringbuf_pop(&rb, &out));
    TEST_ASSERT_EQUAL_HEX8(0xAB, out);
    TEST_ASSERT_TRUE(ferqon_ringbuf_empty(&rb));
}

void test_push_pop_fifo_order(void)
{
    for (uint8_t i = 0; i < 8; i++) {
        TEST_ASSERT_TRUE(ferqon_ringbuf_push(&rb, i));
    }
    for (uint8_t i = 0; i < 8; i++) {
        uint8_t out = 0xFF;
        TEST_ASSERT_TRUE(ferqon_ringbuf_pop(&rb, &out));
        TEST_ASSERT_EQUAL_UINT8(i, out);
    }
    TEST_ASSERT_TRUE(ferqon_ringbuf_empty(&rb));
}

/* ── Full / overflow behaviour ─────────────────────────────────────────── */

void test_full_detection(void)
{
    /* Capacity is mask+1 = 16, but SPSC leaves one slot empty as sentinel,
     * so max storable = mask = 15. */
    uint32_t pushed = 0;
    for (uint32_t i = 0; i < 16; i++) {
        if (ferqon_ringbuf_push(&rb, (uint8_t)i)) pushed++;
    }
    TEST_ASSERT_EQUAL_UINT32(15, pushed);  /* 16th push is dropped */
    TEST_ASSERT_EQUAL_UINT32(15, ferqon_ringbuf_count(&rb));
}

void test_push_full_returns_false(void)
{
    for (int i = 0; i < 15; i++) ferqon_ringbuf_push(&rb, 0);
    TEST_ASSERT_FALSE(ferqon_ringbuf_push(&rb, 0xFF)); /* must return false */
}

/* ── Empty / underflow behaviour ───────────────────────────────────────── */

void test_pop_empty_returns_false(void)
{
    uint8_t out = 0xCC;
    TEST_ASSERT_FALSE(ferqon_ringbuf_pop(&rb, &out));
    TEST_ASSERT_EQUAL_HEX8(0xCC, out); /* must not modify *out */
}

/* ── Wrap-around ───────────────────────────────────────────────────────── */

void test_wraparound(void)
{
    /* Fill 8, drain 8, fill 8 more — head/tail both wrap past mask. */
    for (uint8_t i = 0; i < 8; i++) ferqon_ringbuf_push(&rb, i);
    for (uint8_t i = 0; i < 8; i++) {
        uint8_t out;
        ferqon_ringbuf_pop(&rb, &out);
    }
    for (uint8_t i = 10; i < 18; i++) ferqon_ringbuf_push(&rb, i);
    for (uint8_t i = 10; i < 18; i++) {
        uint8_t out = 0;
        TEST_ASSERT_TRUE(ferqon_ringbuf_pop(&rb, &out));
        TEST_ASSERT_EQUAL_UINT8(i, out);
    }
    TEST_ASSERT_TRUE(ferqon_ringbuf_empty(&rb));
}

/* ── count accuracy ────────────────────────────────────────────────────── */

void test_count_tracks_correctly(void)
{
    TEST_ASSERT_EQUAL_UINT32(0, ferqon_ringbuf_count(&rb));
    ferqon_ringbuf_push(&rb, 1);
    TEST_ASSERT_EQUAL_UINT32(1, ferqon_ringbuf_count(&rb));
    ferqon_ringbuf_push(&rb, 2);
    TEST_ASSERT_EQUAL_UINT32(2, ferqon_ringbuf_count(&rb));
    uint8_t out;
    ferqon_ringbuf_pop(&rb, &out);
    TEST_ASSERT_EQUAL_UINT32(1, ferqon_ringbuf_count(&rb));
    ferqon_ringbuf_pop(&rb, &out);
    TEST_ASSERT_EQUAL_UINT32(0, ferqon_ringbuf_count(&rb));
}

/* ── Entry point ───────────────────────────────────────────────────────── */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_empty_on_init);
    RUN_TEST(test_push_pop_single);
    RUN_TEST(test_push_pop_fifo_order);
    RUN_TEST(test_full_detection);
    RUN_TEST(test_push_full_returns_false);
    RUN_TEST(test_pop_empty_returns_false);
    RUN_TEST(test_wraparound);
    RUN_TEST(test_count_tracks_correctly);

    return UNITY_END();
}
