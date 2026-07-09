/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
#include "platform/ferqon_plt_gpio.h"
#include "../generated/pin_macros.h"
#include <Arduino.h>

/**
 * Arduino-specific GPIO implementation.
 *
 * Uses Arduino's digital I/O functions for GPIO control.
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

    switch (mode) {
        case 0: // INPUT
            pinMode(pin, INPUT);
            digitalWrite(pin, LOW);  // Default to pull-down for inputs
            break;
        case 1: // OUTPUT
            pinMode(pin, OUTPUT);
            break;
        case 2: // PULLUP
            pinMode(pin, INPUT_PULLUP);
            break;
        case 3: // PULLDOWN
            pinMode(pin, INPUT_PULLDOWN);
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

    digitalWrite(pin, value ? HIGH : LOW);
    return true;
}

int FERQON_PLT_GPIO_Get(uint8_t pin)
{
    // Check pin validity using generated capability guard
    if (!ferqon_cap_pin_is_valid(pin)) {
        return -1;
    }

    return digitalRead(pin);
}
