/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * board_config.h
 * --------------
 * Board-specific configuration for Ferqon firmware.
 *
 * This header wraps the generated platform_caps.h so driver code continues
 * to use the legacy macro names (FERQON_PIN_MAX, FERQON_ADC_PIN, etc.).
 * All board constants are sourced from the board YAML via platform_caps.h.
 */

#ifndef FERQON_BOARD_CONFIG_H
#define FERQON_BOARD_CONFIG_H

#include "platform_caps.h"

/* Map generated platform capability names to the legacy board config names. */
#define FERQON_PIN_MAX          FERQON_MAX_GPIO
#define FERQON_ADC_CHANNEL_MAX  (FERQON_ADC_PIN_COUNT - 1)
#define FERQON_ADC_PIN(channel) (FERQON_ADC_PINS[channel])

/* Compile-time assertions to catch configuration errors. */
#if FERQON_PIN_MAX < 0 || FERQON_PIN_MAX > 255
    #error "FERQON_PIN_MAX must be between 0 and 255"
#endif

#endif /* FERQON_BOARD_CONFIG_H */
