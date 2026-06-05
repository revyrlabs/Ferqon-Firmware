/**
 * board_config.h
 * --------------
 * Board-specific configuration for Ferqon firmware (v1 protocol).
 *
 * This file provides board-specific constants for the v1 protocol implementation.
 * Currently only supports Pico/RP2040.
 */

#ifndef FERQON_BOARD_CONFIG_H
#define FERQON_BOARD_CONFIG_H

/* v1 protocol only supports Pico/RP2040 */
#define FERQON_PIN_MAX 29
#define FERQON_BOARD_NAME "RP2040/Pico (v1 protocol)"

#endif /* FERQON_BOARD_CONFIG_H */
