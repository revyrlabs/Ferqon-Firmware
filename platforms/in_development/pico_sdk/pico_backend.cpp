/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* ── STUB / NON-COMPILABLE ──────────────────────────────────────────────────
 * This file is part of an in-development Pico-SDK platform abstraction
 * layer (PAL). It references platform/ferqon_plt_*.h headers that are NOT
 * yet present in this repository, so it does NOT compile. It is not built
 * by any PlatformIO environment and is excluded from the production
 * bundle. Kept for future PAL development only — do not depend on it.
 * ──────────────────────────────────────────────────────────────────────── */
/**
 * pico_backend.cpp
 * ----------------
 * Pico platform backend initialization.
 *
 * Calls the Pico-specific factory functions to populate the operation tables,
 * and initializes Pico device-specific drivers and subsystems.
 */

#include "platform/ferqon_plt_init.h"

#include "platform/ferqon_plt_system.h"
#include "platform/ferqon_plt_io.h"
#include "platform/ferqon_plt_config.h"
#include "pico_backend_internal.hpp"
#include "ferqon_pico.h"

void FERQON_PLT_Init(void)
{
	static int initialized = 0;
	if (initialized) {
		return;
	}

	// Initialize generic platform abstraction layer
	FERQON_PLT_SystemOps sys_ops = pico_make_system_ops();
	FERQON_PLT_IoOps io_ops = pico_make_io_ops();
	FERQON_PLT_ConfigOps cfg_ops = pico_make_config_ops();

	FERQON_PLT_SystemRegisterOps(&sys_ops);
	FERQON_PLT_IoRegisterOps(&io_ops);
	FERQON_PLT_ConfigRegisterOps(&cfg_ops);

	// Initialize Pico-specific device and driver subsystems
	FERQON_PICO_DriverInit();

	initialized = 1;
}
