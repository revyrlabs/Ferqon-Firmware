/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
#pragma once

#include "platform/ferqon_plt_system.h"
#include "platform/ferqon_plt_io.h"
#include "platform/ferqon_plt_config.h"

#ifdef __cplusplus
extern "C" {
#endif

// Arduino platform factory functions
FERQON_PLT_SystemOps arduino_make_system_ops(void);
FERQON_PLT_IoOps arduino_make_io_ops(void);
FERQON_PLT_ConfigOps arduino_make_config_ops(void);

// Arduino platform initialization
void arduino_platform_init(void);

#if defined(ARDUINO_ARCH_ESP32)
// ESP32 only: register the Core 0 (serial RX) entry function before launch_core1 is called.
void arduino_esp32_set_core0_fn(void (*fn)(void));
#endif

#ifdef __cplusplus
}
#endif
