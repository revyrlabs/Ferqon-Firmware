/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/**
 * arduino_config.cpp
 * ------------------
 * Arduino implementation of Ferqon platform config API.
 *
 * Uses simple in-memory storage for Arduino (no persistent storage for now).
 * The general layer (DeviceConfig) is responsible for the in-memory layout
 * and magic/version checking; this file only handles the raw I/O.
 *
 * This file is the ONLY place in the codebase that is allowed to include Arduino
 * headers.  All general code must go through the
 * FERQON_PLT_Config* API instead.
 */

#include "platform/ferqon_plt_config.h"
#include "arduino_backend_internal.hpp"

#include <string.h>

// Simple in-memory storage for Arduino (no persistent storage for now)
static uint8_t config_storage[256];
static bool config_initialized = false;

// ============================================================================

static uint8_t arduino_config_load(void* buf, size_t len)
{
	if (!config_initialized) {
		// First load - return empty
		return 0;
	}

	if (len > sizeof(config_storage))
		len = sizeof(config_storage);

	memcpy(buf, config_storage, len);
	return 1;
}

static void arduino_config_save(const void* buf, size_t len)
{
	if (len > sizeof(config_storage))
		len = sizeof(config_storage);

	memcpy(config_storage, buf, len);
	config_initialized = true;
}

// ============================================================================
// Factory function
// ============================================================================

FERQON_PLT_ConfigOps arduino_make_config_ops(void)
{
	FERQON_PLT_ConfigOps ops = {0};
	ops.load = &arduino_config_load;
	ops.save = &arduino_config_save;
	return ops;
}
