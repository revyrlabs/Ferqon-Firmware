/**
 * pico_config.cpp
 * ----------------
 * RP2040 / Raspberry Pi Pico implementation of Ferqon platform config API.
 *
 * Uses the last 4 KiB flash sector as a single-page persistent store.
 * The general layer (DeviceConfig) is responsible for the in-memory layout
 * and magic/version checking; this file only handles the raw flash I/O.
 *
 * This file is the ONLY place in the codebase that is allowed to include RP2040
 * flash / sync SDK headers.  All general code must go through the
 * FERQON_PLT_Config* API instead.
 */

#include "platform/ferqon_plt_config.h"
#include "pico_backend_internal.hpp"

#include "hardware/flash.h"
#include "hardware/sync.h"
#include "pico/stdlib.h"

#include <string.h>

// ── Flash layout ────────────────────────────────────────────────────────────
// Reserve the very last sector of flash for configuration storage.
// PICO_FLASH_SIZE_BYTES and FLASH_SECTOR_SIZE are SDK constants (2 MiB and
// 4096 bytes respectively on the standard RP2040 module).
static const uint32_t CONFIG_FLASH_OFFSET =
	PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE;  // 0x1FF000 on a 2 MiB Pico

// The XIP (execute-in-place) base address lets us read flash like RAM.
static const uint8_t* flash_read_ptr =
	(const uint8_t*)(XIP_BASE + CONFIG_FLASH_OFFSET);

// ============================================================================

static uint8_t pico_config_load(void* buf, size_t len)
{
	if (len > FLASH_PAGE_SIZE)
		len = FLASH_PAGE_SIZE;

	memcpy(buf, flash_read_ptr, len);

	// A freshly-erased flash sector reads as all 0xFF; detect that here so
	// the general layer knows to fall back to compile-time defaults.
	const uint8_t* p = (const uint8_t*)buf;
	for (size_t i = 0; i < len; ++i) {
		if (p[i] != 0xFF)
			return 1;  // found real data
	}
	return 0;  // blank sector — no valid config stored yet
}

static void pico_config_save(const void* buf, size_t len)
{
	// Pad the write buffer to a full flash page (256 bytes), filling unused
	// space with 0xFF so repeated save() calls remain idempotent for
	// unwritten bytes.
	uint8_t page[FLASH_PAGE_SIZE];
	memset(page, 0xFF, FLASH_PAGE_SIZE);
	if (len > FLASH_PAGE_SIZE)
		len = FLASH_PAGE_SIZE;
	memcpy(page, buf, len);

	// Flash writes require interrupts to be disabled (SDK requirement).
	uint32_t saved = save_and_disable_interrupts();
	flash_range_erase(CONFIG_FLASH_OFFSET, FLASH_SECTOR_SIZE);
	flash_range_program(CONFIG_FLASH_OFFSET, page, FLASH_PAGE_SIZE);
	restore_interrupts(saved);
}

// ============================================================================
// Factory function
// ============================================================================

FERQON_PLT_ConfigOps pico_make_config_ops(void)
{
	FERQON_PLT_ConfigOps ops = {0};
	ops.load = &pico_config_load;
	ops.save = &pico_config_save;
	return ops;
}
