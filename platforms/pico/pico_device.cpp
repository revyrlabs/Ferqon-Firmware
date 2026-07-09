/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/**
 * pico_device.cpp
 * ---------------
 * Pico (RP2040) device-specific implementation.
 *
 * Exposes Pico hardware capabilities, system functions, and driver management.
 * Only included in Pico builds; other platforms have their own device-specific files.
 */

#include "ferqon_pico.h"

#include "platform/ferqon_plt_system.h"

#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include "pico/multicore.h"
#include "hardware/clocks.h"
#include "hardware/uart.h"
#include "hardware/spi.h"
#include "hardware/i2c.h"
#include "hardware/dma.h"
#include "hardware/pio.h"

#include <string.h>

// ============================================================================
// Device Information
// ============================================================================

const char* FERQON_PICO_GetModel(void)
{
	return "RP2040";
}

const char* FERQON_PICO_GetSdkVersion(void)
{
	// Pico SDK doesn't expose version directly; we use a fixed string
	return PICO_SDK_VERSION_STRING;
}

void FERQON_PICO_GetUniqueId(uint8_t* id_out, size_t len)
{
	if (!id_out || len == 0)
		return;

	pico_unique_board_id_t board_id;
	pico_get_unique_board_id(&board_id);

	size_t copy_len = (len < PICO_UNIQUE_BOARD_ID_SIZE_BYTES) ? len : PICO_UNIQUE_BOARD_ID_SIZE_BYTES;
	memcpy(id_out, board_id.id, copy_len);
}

// ============================================================================
// System & Clock Control
// ============================================================================

uint32_t FERQON_PICO_GetSysClockHz(void)
{
	return clock_get_hz(clk_sys);
}

uint32_t FERQON_PICO_GetRefClockHz(void)
{
	return clock_get_hz(clk_ref);
}

uint32_t FERQON_PICO_GetFlashSizeBytes(void)
{
	return PICO_FLASH_SIZE_BYTES;
}

uint8_t FERQON_PICO_GetGpioPinCount(void)
{
	// RP2040 has 30 GPIO pins (0-29)
	return 30;
}

// ============================================================================
// Multicore Support
// ============================================================================

static uint8_t g_core1_running = 0;

uint8_t FERQON_PICO_HasCore1(void)
{
	return 1;  // All RP2040 variants have core1
}

uint8_t FERQON_PICO_LaunchCore1(void (*entry)(void))
{
	if (g_core1_running) {
		return 0;  // Core1 already running
	}

	if (!entry) {
		return 0;  // Invalid entry point
	}

	multicore_launch_core1(entry);
	g_core1_running = 1;
	return 1;
}

uint8_t FERQON_PICO_Core1IsRunning(void)
{
	return g_core1_running;
}

// ============================================================================
// PIO Support
// ============================================================================

static uint8_t g_pio_sm_reserved[2][4] = {{0}};  // 2 PIO blocks, 4 SMs each

uint8_t FERQON_PICO_GetPioBlockCount(void)
{
	return 2;  // RP2040 has PIO0 and PIO1
}

uint8_t FERQON_PICO_PioIsAvailable(uint8_t pio)
{
	return (pio < 2) ? 1 : 0;
}

uint8_t FERQON_PICO_PioReserveStateMachine(uint8_t pio, uint8_t sm)
{
	if (pio >= 2 || sm >= 4) {
		return 0;  // Invalid PIO or SM
	}

	if (g_pio_sm_reserved[pio][sm]) {
		return 0;  // Already reserved
	}

	g_pio_sm_reserved[pio][sm] = 1;
	return 1;
}

void FERQON_PICO_PioReleaseStateMachine(uint8_t pio, uint8_t sm)
{
	if (pio < 2 && sm < 4) {
		g_pio_sm_reserved[pio][sm] = 0;
	}
}

// ============================================================================
// DMA Support
// ============================================================================

static uint8_t g_dma_reserved[12] = {0};  // RP2040 has 12 DMA channels

uint8_t FERQON_PICO_GetDmaChannelCount(void)
{
	return 12;  // RP2040 has 12 DMA channels
}

uint8_t FERQON_PICO_DmaChannelIsAvailable(uint8_t channel)
{
	return (channel < 12 && !g_dma_reserved[channel]) ? 1 : 0;
}

uint8_t FERQON_PICO_DmaReserveChannel(uint8_t channel)
{
	if (channel >= 12 || g_dma_reserved[channel]) {
		return 0;  // Invalid or already reserved
	}

	g_dma_reserved[channel] = 1;
	return 1;
}

void FERQON_PICO_DmaReleaseChannel(uint8_t channel)
{
	if (channel < 12) {
		g_dma_reserved[channel] = 0;
	}
}

// ============================================================================
// UART Helpers
// ============================================================================

// Last baud rate set for each UART instance (updated by both init and runtime
// set calls so GetBaudrate() always reflects the active configuration).
static uint32_t g_uart_baudrate[2] = {115200, 115200};

void FERQON_PICO_UartSetBaudrate(uint8_t inst, uint32_t baudrate)
{
	if (inst >= 2) return;
	uart_inst_t* hw = (inst == 0) ? uart0 : uart1;
	g_uart_baudrate[inst] = uart_set_baudrate(hw, baudrate);
}

uint32_t FERQON_PICO_UartGetBaudrate(uint8_t inst)
{
	return (inst < 2) ? g_uart_baudrate[inst] : 0;
}

void FERQON_PICO_UartFlush(uint8_t inst)
{
	if (inst >= 2) return;
	uart_inst_t* hw = (inst == 0) ? uart0 : uart1;
	uart_tx_wait_blocking(hw);
}

// ============================================================================
// SPI Helpers
// ============================================================================

static uint32_t g_spi_baudrate[2] = {1000000, 1000000};

void FERQON_PICO_SpiSetBaudrate(uint8_t inst, uint32_t baudrate)
{
	if (inst >= 2) return;
	spi_inst_t* hw = (inst == 0) ? spi0 : spi1;
	g_spi_baudrate[inst] = spi_set_baudrate(hw, baudrate);
}

uint32_t FERQON_PICO_SpiGetBaudrate(uint8_t inst)
{
	return (inst < 2) ? g_spi_baudrate[inst] : 0;
}

// ============================================================================
// I2C Helpers
// ============================================================================

static uint32_t g_i2c_baudrate[2] = {100000, 100000};

void FERQON_PICO_I2cSetBaudrate(uint8_t inst, uint32_t baudrate)
{
	if (inst >= 2) return;
	i2c_inst_t* hw = (inst == 0) ? i2c0 : i2c1;
	g_i2c_baudrate[inst] = i2c_set_baudrate(hw, baudrate);
}

uint32_t FERQON_PICO_I2cGetBaudrate(uint8_t inst)
{
	return (inst < 2) ? g_i2c_baudrate[inst] : 0;
}

// ============================================================================
// Driver Management
// ============================================================================

static uint8_t g_driver_initialized = 0;

void FERQON_PICO_DriverInit(void)
{
	if (g_driver_initialized) {
		return;  // Already initialized
	}

	// Initialize all Pico-specific hardware resources
	// This is called during FERQON_PLT_Init() and can be called independently

	g_driver_initialized = 1;
}

const char* FERQON_PICO_GetDriverVersion(void)
{
	return "1.0.0";
}

void FERQON_PICO_PrintStatus(void)
{
	FERQON_PLT_Printf(
		"{\"device\":\"Pico RP2040\","
		"\"sys_clock_hz\":%u,"
		"\"ref_clock_hz\":%u,"
		"\"flash_size_bytes\":%u,"
		"\"gpio_pins\":%d,"
		"\"pio_blocks\":%d,"
		"\"dma_channels\":%d,"
		"\"multicore\":%s}\n",
		(unsigned)FERQON_PICO_GetSysClockHz(),
		(unsigned)FERQON_PICO_GetRefClockHz(),
		(unsigned)FERQON_PICO_GetFlashSizeBytes(),
		FERQON_PICO_GetGpioPinCount(),
		FERQON_PICO_GetPioBlockCount(),
		FERQON_PICO_GetDmaChannelCount(),
		FERQON_PICO_HasCore1() ? "true" : "false");
}
