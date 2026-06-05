/**
 * ferqon_pico.h
 * -----------
 * Pico (RP2040) platform-specific API and capabilities.
 *
 * This header exposes Pico-specific functions and hardware features that go beyond
 * the generic cross-platform FERQON_PLT_* API. Pico-specific code may call these
 * functions directly for hardware features, device initialization, and driver management.
 *
 * Example use cases:
 * - Multicore operations (core0, core1)
 * - PIO (Programmable I/O) configuration
 * - DMA (Direct Memory Access) setup
 * - Advanced clock configuration
 * - Flash and bootload operations
 * - Driver-specific initialization
 *
 * C-compatible interface.
 */
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Pico Device Information
// ============================================================================

/**
 * Get the Pico device model identifier.
 * Returns a string like "RP2040", "RP2350", etc.
 */
const char* FERQON_PICO_GetModel(void);

/**
 * Get the Pico SDK version string.
 */
const char* FERQON_PICO_GetSdkVersion(void);

/**
 * Get the unique device ID (serial number) from Pico's flash.
 * Stores 8 bytes of unique ID into the provided buffer.
 */
void FERQON_PICO_GetUniqueId(uint8_t* id_out, size_t len);

// ============================================================================
// System & Clock Control
// ============================================================================

/**
 * Get the current CPU clock speed in Hz.
 */
uint32_t FERQON_PICO_GetSysClockHz(void);

/**
 * Get the current reference clock speed in Hz.
 */
uint32_t FERQON_PICO_GetRefClockHz(void);

/**
 * Get PICO_FLASH_SIZE_BYTES constant (total flash size).
 * Typically 2MB for standard Pico, 4MB for Pico H.
 */
uint32_t FERQON_PICO_GetFlashSizeBytes(void);

/**
 * Get the number of GPIO pins available on this Pico variant.
 * Typically 30 for standard Pico, 28 for Pico W.
 */
uint8_t FERQON_PICO_GetGpioPinCount(void);

// ============================================================================
// Multicore Support (RP2040)
// ============================================================================

/**
 * Check if the second core (core1) is available on this device.
 * Returns 1 if available, 0 otherwise.
 */
uint8_t FERQON_PICO_HasCore1(void);

/**
 * Launch a function on core1.
 * The function runs indefinitely or until explicitly stopped.
 * Returns 1 on success, 0 if core1 is already running or unavailable.
 */
uint8_t FERQON_PICO_LaunchCore1(void (*entry)(void));

/**
 * Check if core1 is currently running.
 * Returns 1 if running, 0 otherwise.
 */
uint8_t FERQON_PICO_Core1IsRunning(void);

// ============================================================================
// PIO (Programmable I/O) Access
// ============================================================================

/**
 * Get the number of PIO blocks available.
 * RP2040 has 2 PIO blocks.
 */
uint8_t FERQON_PICO_GetPioBlockCount(void);

/**
 * Check if a PIO block is available for use.
 * pio = 0 or 1.
 * Returns 1 if available, 0 otherwise.
 */
uint8_t FERQON_PICO_PioIsAvailable(uint8_t pio);

/**
 * Reserve a PIO state machine for exclusive use.
 * pio = 0 or 1, sm = 0..3 (state machine index).
 * Returns 1 on success, 0 if already reserved.
 */
uint8_t FERQON_PICO_PioReserveStateMachine(uint8_t pio, uint8_t sm);

/**
 * Release a reserved PIO state machine.
 */
void FERQON_PICO_PioReleaseStateMachine(uint8_t pio, uint8_t sm);

// ============================================================================
// DMA (Direct Memory Access) Support
// ============================================================================

/**
 * Get the number of DMA channels available.
 * RP2040 has 12 DMA channels.
 */
uint8_t FERQON_PICO_GetDmaChannelCount(void);

/**
 * Check if a DMA channel is available.
 * Returns 1 if available, 0 otherwise.
 */
uint8_t FERQON_PICO_DmaChannelIsAvailable(uint8_t channel);

/**
 * Reserve a DMA channel for exclusive use.
 * Returns 1 on success, 0 if already in use.
 */
uint8_t FERQON_PICO_DmaReserveChannel(uint8_t channel);

/**
 * Release a reserved DMA channel.
 */
void FERQON_PICO_DmaReleaseChannel(uint8_t channel);

// ============================================================================
// UART Helper Functions
// ============================================================================

/**
 * Set the baud rate for a UART instance at runtime.
 * inst = 0 or 1.
 */
void FERQON_PICO_UartSetBaudrate(uint8_t inst, uint32_t baudrate);

/**
 * Get the current baud rate for a UART instance.
 */
uint32_t FERQON_PICO_UartGetBaudrate(uint8_t inst);

/**
 * Flush (drain) any pending data in a UART's TX buffer.
 */
void FERQON_PICO_UartFlush(uint8_t inst);

// ============================================================================
// SPI Helper Functions
// ============================================================================

/**
 * Set the baud rate for an SPI instance at runtime.
 * inst = 0 or 1.
 */
void FERQON_PICO_SpiSetBaudrate(uint8_t inst, uint32_t baudrate);

/**
 * Get the current baud rate for an SPI instance.
 */
uint32_t FERQON_PICO_SpiGetBaudrate(uint8_t inst);

// ============================================================================
// I2C Helper Functions
// ============================================================================

/**
 * Set the baud rate for an I2C instance at runtime.
 * inst = 0 or 1.
 */
void FERQON_PICO_I2cSetBaudrate(uint8_t inst, uint32_t baudrate);

/**
 * Get the current baud rate for an I2C instance.
 */
uint32_t FERQON_PICO_I2cGetBaudrate(uint8_t inst);

// ============================================================================
// Driver Management
// ============================================================================

/**
 * Initialize all Pico runtime drivers and subsystems.
 * Called automatically by FERQON_PLT_Init(), but can be called again safely.
 */
void FERQON_PICO_DriverInit(void);

/**
 * Get the driver runtime version.
 */
const char* FERQON_PICO_GetDriverVersion(void);

/**
 * Report Pico system status as JSON.
 * Useful for diagnostics and monitoring.
 */
void FERQON_PICO_PrintStatus(void);

#ifdef __cplusplus
}
#endif
