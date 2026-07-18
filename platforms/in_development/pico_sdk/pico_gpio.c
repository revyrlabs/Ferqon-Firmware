/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* ── STUB / NON-COMPILABLE ──────────────────────────────────────────────────
 * This file is part of an in-development Pico-SDK platform abstraction
 * layer (PAL). It references platform/ferqon_plt_*.h headers that are NOT
 * yet present in this repository, so it does NOT compile. It is not built
 * by any PlatformIO environment and is excluded from the production
 * bundle. Kept for future PAL development only — do not depend on it.
 * ──────────────────────────────────────────────────────────────────────── */
#include "platform/ferqon_plt_gpio.h"
#include "../generated/pin_macros.h"
#include "hardware/gpio.h"

/**
 * Pico-specific GPIO implementation.
 *
 * Uses Pico SDK's hardware/gpio.h for direct GPIO control.
 * All operations are guarded by generated capability checks.
 */

bool FERQON_PLT_GPIO_Configure(uint8_t pin, uint8_t mode)
{
    // Check pin validity using generated capability guard
    if (!ferqon_cap_pin_is_valid(pin)) {
        return false;
    }

    // Check if pin is reserved
    if (ferqon_cap_pin_is_reserved(pin)) {
        return false;
    }

    // Initialize the GPIO pin
    gpio_init(pin);

    switch (mode) {
        case 0: // INPUT
            gpio_set_dir(pin, GPIO_IN);
            gpio_pull_down(pin);  // Default to pull-down for inputs
            break;
        case 1: // OUTPUT
            gpio_set_dir(pin, GPIO_OUT);
            break;
        case 2: // PULLUP
            gpio_set_dir(pin, GPIO_IN);
            gpio_pull_up(pin);
            break;
        case 3: // PULLDOWN
            gpio_set_dir(pin, GPIO_IN);
            gpio_pull_down(pin);
            break;
        default:
            return false;
    }

    return true;
}

bool FERQON_PLT_GPIO_Set(uint8_t pin, uint8_t value)
{
    // Check pin validity using generated capability guard
    if (!ferqon_cap_pin_is_valid(pin)) {
        return false;
    }

    gpio_put(pin, value ? 1 : 0);
    return true;
}

int FERQON_PLT_GPIO_Get(uint8_t pin)
{
    // Check pin validity using generated capability guard
    if (!ferqon_cap_pin_is_valid(pin)) {
        return -1;
    }

    return gpio_get(pin) ? 1 : 0;
}
