/**
 * arduino_system.cpp
 * ------------------
 * Arduino implementation of Ferqon platform system API.
 *
 * This file is the ONLY place in the codebase that is allowed to include Arduino
 * system / timing headers.  All general code must go through the
 * FERQON_PLT_ API instead.
 */

#include "platform/ferqon_plt_system.h"
#include "arduino_backend_internal.hpp"

#include <Arduino.h>
#include <stdarg.h>
#include <stdio.h>

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

static void arduino_system_init(void)
{
	Serial.begin(115200);
}

// ---------------------------------------------------------------------------
// Character I/O
// ---------------------------------------------------------------------------

static int arduino_getchar_timeout_us(uint32_t timeout_us)
{
	unsigned long start = micros();
	while ((micros() - start) < timeout_us) {
		if (Serial.available() > 0) {
			return Serial.read();
		}
	}
	return FERQON_PLT_NO_CHAR;
}

static int arduino_vprintf(const char* fmt, va_list args)
{
	char buffer[256];
	int written = vsnprintf(buffer, sizeof(buffer), fmt, args);
	if (written > 0) {
		Serial.write(buffer, written);
	}
	return written;
}

static int arduino_write_bytes(const uint8_t* buf, size_t len)
{
	if (!buf || len == 0) {
		return 0;
	}
	size_t written = Serial.write(buf, len);
	Serial.flush();
	return (int)written;
}

static int arduino_get_device_id(char* out, size_t out_len)
{
	if (!out || out_len == 0) {
		return 0;
	}

	// Arduino doesn't have a unique board ID like Pico
	// Use a simple hash of available info or return a default
	const char* default_id = "arduino-device";
	size_t len = strlen(default_id);
	if (out_len < len + 1) {
		out[0] = '\0';
		return 0;
	}
	strncpy(out, default_id, out_len);
	out[out_len - 1] = '\0';
	return 1;
}

// ---------------------------------------------------------------------------
// Timing
// ---------------------------------------------------------------------------

static void arduino_sleep_ms(uint32_t ms)
{
	delay(ms);
}

static uint32_t arduino_time_us_32(void)
{
	return micros();
}

static void arduino_delay_us(uint32_t us)
{
	delayMicroseconds(us);
}

// ---------------------------------------------------------------------------
// LED
// ---------------------------------------------------------------------------

static void arduino_led_init(uint8_t pin)
{
	pinMode(pin, OUTPUT);
	digitalWrite(pin, HIGH);
}

static void arduino_led_set(uint8_t pin, uint8_t on)
{
	digitalWrite(pin, on ? HIGH : LOW);
}

// ---------------------------------------------------------------------------
// Multi-core / ISR scheduling support
// ---------------------------------------------------------------------------

/* ── launch_core1 ────────────────────────────────────────────────────────── */

#if defined(ARDUINO_ARCH_RP2040)
/*
 * RP2040 Arduino (arduino-pico core):
 * The arduino-pico core exposes setup1() / loop1() which run on Core 1.
 * We store the entry pointer and call it from loop1() defined below.
 * Only one launch_core1() call is supported (call once at startup).
 */
static void (*s_core1_entry)(void) = NULL;

static void arduino_launch_core1(void (*entry)(void))
{
    s_core1_entry = entry;
    /* Core 1 is automatically started by arduino-pico; loop1() calls
     * s_core1_entry() if set.  No explicit launch call needed here. */
}

/* loop1() is called by the arduino-pico runtime on Core 1 after setup1(). */
extern "C" void setup1() {}
extern "C" void loop1()
{
    if (s_core1_entry) {
        s_core1_entry(); /* entry must never return */
    }
}

#elif defined(ARDUINO_ARCH_ESP32)
/*
 * ESP32 Arduino + FreeRTOS:
 *
 * The Arduino-ESP32 runtime pins setup()/loop() to Core 1 (APP_CPU).
 * Ferqon needs the opposite split:
 *   Core 0 (PRO_CPU) — serial RX      (ferqon_sched_core0_loop, fast/polling)
 *   Core 1 (APP_CPU) — command exec   (ferqon_sched_core1_loop, can block briefly)
 *
 * We create two explicit FreeRTOS tasks pinned to the correct cores.
 * loop() in arduino_backend.cpp is a no-op on ESP32 — both cores are driven
 * by these tasks. s_core0_fn is set by arduino_backend before calling
 * launch_core1 so the Core 0 task knows what to run.
 */
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static void (*s_esp32_core0_fn)(void) = NULL;
static void (*s_esp32_core1_fn)(void) = NULL;

static void esp32_core0_task(void* /*param*/)
{
    for (;;) { if (s_esp32_core0_fn) s_esp32_core0_fn(); }
}

static void esp32_core1_task(void* /*param*/)
{
    for (;;) { if (s_esp32_core1_fn) s_esp32_core1_fn(); }
}

void arduino_esp32_set_core0_fn(void (*fn)(void))
{
    s_esp32_core0_fn = fn;
}

static void arduino_launch_core1(void (*entry)(void))
{
    s_esp32_core1_fn = entry;

    /* Core 1 (APP_CPU) — command execution */
    xTaskCreatePinnedToCore(esp32_core1_task, "ferqon_core1",
        8192, NULL, 2, NULL, 1);

    /* Core 0 (PRO_CPU) — serial RX loop */
    xTaskCreatePinnedToCore(esp32_core0_task, "ferqon_core0",
        4096, NULL, 1, NULL, 0);
}

#elif defined(ARDUINO_ARCH_RP2040)
/* RP2040 multicore support - store entry for loop1() */
static void (*s_core1_entry)(void) = NULL;

static void arduino_launch_core1(void (*entry)(void))
{
    s_core1_entry = entry;
}

// Arduino-pico core provides loop1() which runs on core1
// We need to call the stored entry point from loop1()
void loop1()
{
    if (s_core1_entry) {
        s_core1_entry();
    }
}

#else
/* Unsupported single-core platform — provide a no-op. */
static void arduino_launch_core1(void (*entry)(void))
{
    (void)entry;
}
#endif /* ARDUINO_ARCH_RP2040 / ESP32 */

/* ── install_rx_isr ──────────────────────────────────────────────────────── */

static void (*s_rx_isr_cb)(uint8_t) = NULL;

static void arduino_serial_rx_event(void)
{
    while (Serial.available() > 0) {
        uint8_t b = (uint8_t)Serial.read();
        if (s_rx_isr_cb) {
            s_rx_isr_cb(b);
        }
    }
}

static void arduino_install_rx_isr(void (*on_byte)(uint8_t byte))
{
    s_rx_isr_cb = on_byte;
    // Note: Arduino mbed doesn't have onReceive - ISR handled via different mechanism
    // For multicore, serial RX is handled on core0 via polling
}

// ---------------------------------------------------------------------------
// System control
// ---------------------------------------------------------------------------

static void arduino_watchdog_reboot(void)
{
	// Arduino watchdog reset
#if defined(ARDUINO_ARCH_ESP32)
	ESP.restart();
#elif defined(ARDUINO_ARCH_ESP8266)
	ESP.restart();
#else
	// Generic fallback - just infinite loop
	while (1) { delay(100); }
#endif
}

static void arduino_enter_bootloader(void)
{
	// Arduino doesn't have a standard bootloader entry
	// For ESP32, we can use the same restart
	arduino_watchdog_reboot();
}

// ---------------------------------------------------------------------------
// Factory function
// ---------------------------------------------------------------------------

FERQON_PLT_SystemOps arduino_make_system_ops(void)
{
	FERQON_PLT_SystemOps ops = {0};
	ops.init = &arduino_system_init;
	ops.getchar_timeout_us = &arduino_getchar_timeout_us;
	ops.vprintf_fn = &arduino_vprintf;
	ops.write_bytes = &arduino_write_bytes;
	ops.get_device_id = &arduino_get_device_id;
	ops.sleep_ms = &arduino_sleep_ms;
	ops.time_us_32 = &arduino_time_us_32;
	ops.delay_us = &arduino_delay_us;
	ops.led_init = &arduino_led_init;
	ops.led_set = &arduino_led_set;
	ops.watchdog_reboot = &arduino_watchdog_reboot;
	ops.enter_bootloader = &arduino_enter_bootloader;
	ops.launch_core1 = &arduino_launch_core1;
	ops.install_rx_isr = &arduino_install_rx_isr;
	return ops;
}
