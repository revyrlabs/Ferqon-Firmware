/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * test_sched_multicore.c
 * ----------------------
 * Unit tests for ferqon_sched_multicore.c — the SPSC inter-core queue.
 *
 * We build this on the native host with FERQON_SCHED_MULTICORE=1 and
 * FERQON_SCHED_QUEUE_DEPTH=8 injected by the native env in platformio.ini.
 * Protocol / driver symbols are satisfied by stubs.c.
 */

#include "unity.h"
#include "scheduling/ferqon_sched.h"
#include "protocol.h"

/* Spy: count how many times FERQON_Drivers_HandleRequest is called.
 * We override the stub from stubs.c specifically for these tests by
 * wrapping it — on GCC native we use the -Wl,--wrap flag. */
int g_dispatch_count = 0;
bool __wrap_FERQON_Drivers_HandleRequest(const FERQON_RuntimeRequest_t* req)
{
    (void)req;
    g_dispatch_count++;
    return true;
}

/* Helper — build a minimal request with a specific cmd_id. */
static FERQON_RuntimeRequest_t make_req(uint16_t cmd_id)
{
    FERQON_RuntimeRequest_t r;
    r.cmd_id    = cmd_id;
    r.transport = 1;
    r.call_name[0] = '\0';
    r.driver_name[0] = '\0';
    r.payload[0] = '\0';
    return r;
}

void setUp(void)
{
    g_dispatch_count = 0;
    ferqon_sched_init();
}

void tearDown(void) {}

/* ── submit + core1_loop dispatches ──────────────────────────────────── */

void test_submit_then_core1_dispatches(void)
{
    FERQON_RuntimeRequest_t r = make_req(0x0001);
    ferqon_sched_submit(&r);

    /* One core1_loop iteration should dequeue and dispatch one request. */
    ferqon_sched_core1_loop();
    TEST_ASSERT_EQUAL_INT(1, g_dispatch_count);
}

void test_core1_loop_idle_dispatches_nothing(void)
{
    /* Queue is empty — core1_loop should run without dispatching. */
    ferqon_sched_core1_loop();
    TEST_ASSERT_EQUAL_INT(0, g_dispatch_count);
}

void test_submit_null_is_safe(void)
{
    ferqon_sched_submit(NULL); /* must not crash */
    ferqon_sched_core1_loop();
    TEST_ASSERT_EQUAL_INT(0, g_dispatch_count);
}

/* ── Multiple submit/drain cycles ─────────────────────────────────────── */

void test_multiple_requests_in_order(void)
{
    for (int i = 0; i < 4; i++) {
        FERQON_RuntimeRequest_t r = make_req((uint16_t)i);
        ferqon_sched_submit(&r);
    }
    for (int i = 0; i < 4; i++) {
        ferqon_sched_core1_loop();
        TEST_ASSERT_EQUAL_INT(i + 1, g_dispatch_count);
    }
    /* Queue now empty — extra iterations dispatch nothing */
    ferqon_sched_core1_loop();
    TEST_ASSERT_EQUAL_INT(4, g_dispatch_count);
}

/* ── Queue full (depth = FERQON_SCHED_QUEUE_DEPTH = 8 → 7 usable slots) ── */

void test_queue_drops_when_full(void)
{
    /* Submit 7 (max), 8th should be silently dropped. */
    for (int i = 0; i < 8; i++) {
        FERQON_RuntimeRequest_t r = make_req((uint16_t)i);
        ferqon_sched_submit(&r);
    }
    /* Drain all */
    for (int i = 0; i < 16; i++) ferqon_sched_core1_loop();
    /* Only 7 should have been dispatched */
    TEST_ASSERT_EQUAL_INT(7, g_dispatch_count);
}

/* ── Entry point ───────────────────────────────────────────────────────── */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_submit_then_core1_dispatches);
    RUN_TEST(test_core1_loop_idle_dispatches_nothing);
    RUN_TEST(test_submit_null_is_safe);
    RUN_TEST(test_multiple_requests_in_order);
    RUN_TEST(test_queue_drops_when_full);

    return UNITY_END();
}
