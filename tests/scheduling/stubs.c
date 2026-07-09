/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * stubs.c
 * -------
 * Minimal stubs to satisfy linker when compiling scheduling tests on native host.
 * None of these are called during unit tests — they exist only to resolve symbols
 * that the scheduling .c files reference.
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>

/* ── protocol.h symbols ──────────────────────────────────────────────── */

#include "protocol.h"

uint8_t FERQON_Protocol_FrameFeedByte(uint8_t byte, FERQON_RuntimeRequest_t* out)
{
    (void)byte; (void)out;
    return 0;
}

void FERQON_Protocol_FrameIdleTick(void) {}
void FERQON_Protocol_Init(void) {}
bool FERQON_Protocol_ReadRequest(FERQON_RuntimeRequest_t* r) { (void)r; return false; }
void FERQON_Protocol_WriteResponse(const FERQON_RuntimeResponse_t* r) { (void)r; }

bool FERQON_Protocol_ExtractParamString(const char* s, const char* k, char* o, size_t l)
{ (void)s; (void)k; (void)o; (void)l; return false; }
bool FERQON_Protocol_ExtractParamInt(const char* s, const char* k, int* o)
{ (void)s; (void)k; (void)o; return false; }

/* ── driver_api.h symbols ─────────────────────────────────────────────── */

#include "driver_api.h"

void  FERQON_Drivers_Init(void) {}
void  FERQON_Drivers_Loop(void) {}
bool  FERQON_Drivers_HandleRequest(const FERQON_RuntimeRequest_t* r) { (void)r; return true; }
bool  FERQON_Registry_Register(const FERQON_Driver_t* d) { (void)d; return true; }
const FERQON_Driver_t* FERQON_Registry_Find(const char* n) { (void)n; return NULL; }
int   FERQON_Registry_Count(void) { return 0; }
const FERQON_Driver_t* FERQON_Registry_Get(int i) { (void)i; return NULL; }
void  FERQON_Registry_Init(void) {}
void  FERQON_Runtime_Tick(void) {}

/* ── ferqon_plt_system.h symbols ────────────────────────────────────────── */

#include "platform/ferqon_plt_system.h"

/* Enough for the scheduler to call FERQON_PLT_Getchar without aborting. */
static int  stub_getchar(uint32_t t) { (void)t; return -1; }
static int  stub_vprintf(const char* f, va_list a) { (void)f; (void)a; return 0; }
static int  stub_write(const uint8_t* b, size_t l) { (void)b; (void)l; return 0; }
static int  stub_devid(char* o, size_t l) { (void)o; (void)l; return 0; }
static void stub_void(void) {}
static void stub_sleep(uint32_t v) { (void)v; }
static uint32_t stub_time(void) { return 0; }
static void stub_delay(uint32_t v) { (void)v; }
static void stub_led_init(uint8_t p) { (void)p; }
static void stub_led_set(uint8_t p, uint8_t v) { (void)p; (void)v; }

__attribute__((constructor)) static void register_stub_ops(void)
{
    FERQON_PLT_SystemOps ops = {0};
    ops.init              = stub_void;
    ops.getchar_timeout_us= stub_getchar;
    ops.vprintf_fn        = stub_vprintf;
    ops.write_bytes       = stub_write;
    ops.get_device_id     = stub_devid;
    ops.sleep_ms          = stub_sleep;
    ops.time_us_32        = stub_time;
    ops.delay_us          = stub_delay;
    ops.led_init          = stub_led_init;
    ops.led_set           = stub_led_set;
    ops.watchdog_reboot   = stub_void;
    ops.enter_bootloader  = stub_void;
    ops.launch_core1      = NULL;
    ops.install_rx_isr    = NULL;
    FERQON_PLT_SystemRegisterOps(&ops);
}
