/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * board_config.h
 * --------------
 * Board-specific configuration for Ferqon firmware.
 *
 * This file provides board-specific constants that are configured at compile time
 * based on the target platform. It uses PlatformIO build flags to set the correct
 * values for each board.
 *
 * Supported boards:
 * - Pico (RP2040): max_gpio = 29
 * - ESP32: max_gpio = 39
 * - ESP32-S3: max_gpio = 48
 * - RP2040: max_gpio = 29
 * - STM32F4: max_gpio = varies by board
 * - STM32F7: max_gpio = varies by board
 * - Teensy 4.0: max_gpio = 40
 * - Teensy 4.1: max_gpio = 55
 */

#ifndef FERQON_BOARD_CONFIG_H
#define FERQON_BOARD_CONFIG_H

/* Default to Pico if not specified */
#ifndef FERQON_BOARD
#define FERQON_BOARD "pico"
#endif

/* Board-specific pin ranges */
#if defined(FERQON_BOARD_PICO) || defined(FERQON_BOARD_RP2040)
    /* Raspberry Pi Pico / RP2040 */
    #define FERQON_PIN_MAX 29
    #define FERQON_LED_PIN 25
    #define FERQON_ADC_CHANNEL_MAX 3
    #define FERQON_ADC_BASE_PIN 26
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "RP2040/Pico"

#elif defined(FERQON_BOARD_ESP32)
    /* ESP32 */
    #define FERQON_PIN_MAX 39
    #define FERQON_LED_PIN 2
    #define FERQON_ADC_CHANNEL_MAX 6
    #define FERQON_ADC_BASE_PIN 32
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "ESP32"

#elif defined(FERQON_BOARD_ESP32S3)
    /* ESP32-S3 */
    #define FERQON_PIN_MAX 48
    #define FERQON_LED_PIN 2
    #define FERQON_ADC_CHANNEL_MAX 10
    #define FERQON_ADC_BASE_PIN 32
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "ESP32-S3"

#elif defined(FERQON_BOARD_STM32F4)
    /* STM32F4 - use conservative default, can be overridden */
    #define FERQON_PIN_MAX 50
    #define FERQON_LED_PIN 13
    #define FERQON_ADC_CHANNEL_MAX 16
    #define FERQON_ADC_BASE_PIN 0
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "STM32F4"

#elif defined(FERQON_BOARD_STM32F7)
    /* STM32F7 - use conservative default, can be overridden */
    #define FERQON_PIN_MAX 50
    #define FERQON_LED_PIN 13
    #define FERQON_ADC_CHANNEL_MAX 16
    #define FERQON_ADC_BASE_PIN 0
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "STM32F7"

#elif defined(FERQON_BOARD_TEENSY40)
    /* Teensy 4.0 */
    #define FERQON_PIN_MAX 40
    #define FERQON_LED_PIN 13
    #define FERQON_ADC_CHANNEL_MAX 14
    #define FERQON_ADC_BASE_PIN 14
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "Teensy 4.0"

#elif defined(FERQON_BOARD_TEENSY41)
    /* Teensy 4.1 */
    #define FERQON_PIN_MAX 55
    #define FERQON_LED_PIN 13
    #define FERQON_ADC_CHANNEL_MAX 14
    #define FERQON_ADC_BASE_PIN 14
    #define FERQON_ADC_VREF_MV 3300
    #define FERQON_ADC_RESOLUTION 12
    #define FERQON_BOARD_NAME "Teensy 4.1"

#else
    /* Force build failure if board is not explicitly specified */
    #error "No FERQON_BOARD_* macro defined. Please specify the target board in platformio.ini build_flags."
#endif

/* Helper macros for ADC pin calculation */
#define FERQON_ADC_PIN(channel) (FERQON_ADC_BASE_PIN + (channel))

/* Compile-time assertions to catch configuration errors */
#if FERQON_PIN_MAX < 0 || FERQON_PIN_MAX > 255
    #error "FERQON_PIN_MAX must be between 0 and 255"
#endif

#if FERQON_ADC_CHANNEL_MAX < 0 || FERQON_ADC_CHANNEL_MAX > 255
    #error "FERQON_ADC_CHANNEL_MAX must be between 0 and 255"
#endif

#endif /* FERQON_BOARD_CONFIG_H */
