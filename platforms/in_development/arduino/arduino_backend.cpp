/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/**
 * arduino_backend.cpp
 * -------------------
 * Arduino platform backend initialization and registration.
 *
 * Execution model (selected at compile time from generated platform_caps.h):
 *
 *   FERQON_SCHED_MULTICORE == 1  (RP2040, ESP32, ESP32-S3)
 *     setup()  — init platform + scheduler, launch Core 1 via launch_core1()
 *     loop()   — Core 0: serial RX only (ferqon_sched_core0_loop)
 *     loop1()  — Core 1: command execution (ferqon_sched_core1_loop)
 *                Defined in arduino_system.cpp for the RP2040 arduino-pico core;
 *                for ESP32, Core 1 runs as a FreeRTOS task pinned there.
 *
 *   FERQON_SCHED_UART_ISR == 1  (STM32F4/F7, Teensy 4.x)
 *     setup()  — init platform + scheduler, install UART RX ISR
 *     loop()   — drain ISR ring buffer, parse frames, dispatch commands
 */

#include "arduino_backend_internal.hpp"
#include "platform/ferqon_plt_init.h"
#include "platform/ferqon_plt_system.h"
#include "ferqon_sched.h"
#include "platform_caps.h"

#include <Arduino.h>
#if defined(ARDUINO_ARCH_ESP32)
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#endif

// Arduino platform ops tables - defined in individual implementation files
extern FERQON_PLT_SystemOps arduino_make_system_ops(void);
extern FERQON_PLT_IoOps arduino_make_io_ops(void);
extern FERQON_PLT_ConfigOps arduino_make_config_ops(void);

// Forward declarations from Ferqon runtime
extern "C" void FERQON_Drivers_Init(void);

// ============================================================================
// Platform registration
// ============================================================================

void arduino_platform_init(void)
{
	FERQON_PLT_SystemOps system_ops = arduino_make_system_ops();
	FERQON_PLT_IoOps     io_ops     = arduino_make_io_ops();
	FERQON_PLT_ConfigOps config_ops = arduino_make_config_ops();

	FERQON_PLT_SystemRegisterOps(&system_ops);
	FERQON_PLT_IoRegisterOps(&io_ops);
	FERQON_PLT_ConfigRegisterOps(&config_ops);
}

// ============================================================================
// Arduino entry points
// ============================================================================

void setup()
{
	arduino_platform_init();
	FERQON_PLT_Init();
	FERQON_PLT_SystemInit();

	ferqon_sched_init();
	FERQON_Drivers_Init();

#if FERQON_SCHED_MULTICORE
#if defined(ARDUINO_ARCH_ESP32)
	// ESP32: setup()/loop() run on Core 1 (APP_CPU) courtesy of the Arduino-ESP32
	// FreeRTOS runtime. We cannot move loop() to Core 0, so we take over both
	// cores explicitly: register the Core 0 serial RX fn, then launch_core1
	// creates pinned tasks for both cores. loop() below becomes idle.
	arduino_esp32_set_core0_fn(ferqon_sched_core0_loop);
	FERQON_PLT_LaunchCore1((void (*)(void))ferqon_sched_core1_loop);
#else
	// RP2040 arduino-pico: stores the Core 1 entry for loop1() to call.
	FERQON_PLT_LaunchCore1((void (*)(void))ferqon_sched_core1_loop);
#endif
#elif FERQON_SCHED_UART_ISR
	// Single-core: install the UART RX ISR; main loop drains the ring buffer.
	FERQON_PLT_InstallRxIsr(ferqon_sched_isr_push_byte);
#endif
}

void loop()
{
#if FERQON_SCHED_MULTICORE && defined(ARDUINO_ARCH_ESP32)
	// Both cores are driven by FreeRTOS tasks created in setup().
	// loop() runs on Core 1 but must yield so the RTOS tasks can execute.
	vTaskDelay(portMAX_DELAY);
#elif FERQON_SCHED_MULTICORE
	// RP2040: Core 0 serial RX loop (loop1() handles Core 1 dispatch).
	ferqon_sched_core0_loop();
#elif FERQON_SCHED_UART_ISR
	// Single-core: drain ISR ring buffer, parse frames, dispatch commands.
	ferqon_sched_drain_and_dispatch();
#else
#error "No scheduling strategy defined. Check platform_caps.h generation."
#endif
}
