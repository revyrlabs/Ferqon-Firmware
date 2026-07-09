/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * pico_system.cpp
 * ----------------
 * RP2040 / Raspberry Pi Pico implementation of Ferqon platform system API.
 *
 * This file is the ONLY place in the codebase that is allowed to include Pico SDK
 * system / timing / bootrom headers.  All general code must go through the
 * FERQON_PLT_ API instead.
 */

#include "platform/ferqon_plt_system.h"
#include "pico_backend_internal.hpp"

#include "pico/stdlib.h"
#include "pico/time.h"
#include "pico/bootrom.h"
#include "pico/stdio_usb.h"
#include "pico/unique_id.h"
#include "pico/multicore.h"
#include "hardware/watchdog.h"
#include "hardware/gpio.h"

#include <stdarg.h>
#include <stdio.h>

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

static void pico_system_init(void)
{
	stdio_init_all();
}

// ---------------------------------------------------------------------------
// Character I/O
// ---------------------------------------------------------------------------

static int pico_getchar_timeout_us(uint32_t timeout_us)
{
	int c = getchar_timeout_us(timeout_us);
	return (c == PICO_ERROR_TIMEOUT) ? FERQON_PLT_NO_CHAR : c;
}

static int pico_vprintf(const char* fmt, va_list args)
{
	int written = vprintf(fmt, args);
	return written;
}

static int pico_write_bytes(const uint8_t* buf, size_t len)
{
	if (!buf || len == 0) {
		return 0;
	}
	// Use fwrite to stdout to preserve null bytes (unlike printf)
	size_t written = fwrite(buf, 1, len, stdout);
	fflush(stdout);
	return (int)written;
}

static int pico_get_device_id(char* out, size_t out_len)
{
	if (!out || out_len == 0) {
		return 0;
	}

	pico_unique_board_id_t board_id;
	pico_get_unique_board_id(&board_id);

	const size_t required_len = (2U * PICO_UNIQUE_BOARD_ID_SIZE_BYTES) + 1U;
	if (out_len < required_len) {
		out[0] = '\0';
		return 0;
	}

	for (size_t i = 0; i < PICO_UNIQUE_BOARD_ID_SIZE_BYTES; ++i) {
		snprintf(&out[i * 2U], 3, "%02x", board_id.id[i]);
	}
	out[required_len - 1U] = '\0';
	return 1;
}

// ---------------------------------------------------------------------------
// Timing
// ---------------------------------------------------------------------------

static void pico_sleep_ms(uint32_t ms)
{
	sleep_ms(ms);
}

static uint32_t pico_time_us_32(void)
{
	return time_us_32();
}

static void pico_delay_us(uint32_t us)
{
	sleep_us(us);
}

// ---------------------------------------------------------------------------
// LED
// ---------------------------------------------------------------------------

static void pico_led_init(uint8_t pin)
{
	gpio_init(pin);
	gpio_set_dir(pin, GPIO_OUT);
	gpio_put(pin, 1);
}

static void pico_led_set(uint8_t pin, uint8_t on)
{
	gpio_put(pin, on ? 1 : 0);
}

// ---------------------------------------------------------------------------
// System control
// ---------------------------------------------------------------------------

static void pico_watchdog_reboot(void)
{
	watchdog_reboot(0, 0, 0);
	// Spin until the watchdog fires; should be nearly instant.
	while (1) { tight_loop_contents(); }
}

static void pico_enter_bootloader(void)
{
	// Critical: Disable USB stdio and flush all output before calling reset_usb_boot
	// This ensures USB CDC is properly shut down before bootrom takes over

	// Flush all buffered output
	fflush(stdout);
	fflush(stderr);

	// Give time for any buffered data to transmit
	sleep_us(100);

	// Disable USB stdio to release USB resources
	stdio_usb_deinit();

	// Wait for USB to fully disconnect
	sleep_us(200);

	// Now enter bootloader via reset_usb_boot
	// Parameters: (usb_activity_gpio_pin_mask, disable_interface_mask)
	// Both 0 = default behavior (both interfaces enabled, no LED)
	reset_usb_boot(0, 0);

	// Should not reach here - bootrom takes over
	while (1) { tight_loop_contents(); }
}

// ---------------------------------------------------------------------------
// Multi-core support (RP2040 is always dual-core)
// ---------------------------------------------------------------------------

static void pico_launch_core1(void (*entry)(void))
{
	if (entry) {
		multicore_launch_core1(entry);
	}
}

// ---------------------------------------------------------------------------
// Factory function
// ---------------------------------------------------------------------------

FERQON_PLT_SystemOps pico_make_system_ops(void)
{
	FERQON_PLT_SystemOps ops = {0};
	ops.init = &pico_system_init;
	ops.getchar_timeout_us = &pico_getchar_timeout_us;
	ops.vprintf_fn = &pico_vprintf;
	ops.write_bytes = &pico_write_bytes;
	ops.get_device_id = &pico_get_device_id;
	ops.sleep_ms = &pico_sleep_ms;
	ops.time_us_32 = &pico_time_us_32;
	ops.delay_us = &pico_delay_us;
	ops.led_init = &pico_led_init;
	ops.led_set = &pico_led_set;
	ops.watchdog_reboot = &pico_watchdog_reboot;
	ops.enter_bootloader = &pico_enter_bootloader;
	ops.launch_core1 = &pico_launch_core1;
	ops.install_rx_isr = NULL; /* RP2040: multicore, no ISR strategy */
	return ops;
}
