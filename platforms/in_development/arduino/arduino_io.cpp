/**
 * arduino_io.cpp
 * --------------
 * Arduino implementation of Ferqon platform I/O API.
 *
 * This file is the ONLY place in the codebase that is allowed to include Arduino
 * hardware peripheral headers.  All general code must go through the
 * FERQON_PLT_ API instead.
 */

#include "platform/ferqon_plt_io.h"
#include "arduino_backend_internal.hpp"
#include "../generated/pin_macros.h"

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>

#include <stddef.h>

// ============================================================================
// GPIO
// ============================================================================

static void arduino_gpio_init(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        pinMode(pin, INPUT);
    }
}

static void arduino_gpio_set_dir_in(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        pinMode(pin, INPUT);
    }
}

static void arduino_gpio_set_dir_out(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        pinMode(pin, OUTPUT);
    }
}

static void arduino_gpio_pull_up(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        digitalWrite(pin, HIGH);
        pinMode(pin, INPUT_PULLUP);
    }
}

static void arduino_gpio_pull_down(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        digitalWrite(pin, LOW);
        pinMode(pin, INPUT_PULLDOWN);
    }
}

static void arduino_gpio_disable_pulls(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        pinMode(pin, INPUT);
    }
}

static void arduino_gpio_put(uint8_t pin, uint8_t on)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        digitalWrite(pin, on ? HIGH : LOW);
    }
}

static uint8_t arduino_gpio_get(uint8_t pin)
{
    if (!ferqon_cap_pin_is_valid(pin)) {
        return 0;
    }
    return digitalRead(pin);
}

static uint8_t arduino_gpio_usable(uint8_t pin)
{
	return ferqon_cap_pin_is_valid(pin) && !ferqon_cap_pin_is_reserved(pin);
}

// ============================================================================
// Pin function assignment
// ============================================================================

// Arduino doesn't have explicit pin function assignment like Pico
// These are no-ops for Arduino as pin functions are set by the peripheral libraries
static void arduino_gpio_set_func_spi(uint8_t pin)  { (void)pin; }
static void arduino_gpio_set_func_i2c(uint8_t pin)  { (void)pin; }
static void arduino_gpio_set_func_uart(uint8_t pin) { (void)pin; }
static void arduino_gpio_set_func_pwm(uint8_t pin)  { (void)pin; }

// ============================================================================
// Instance routing
// ============================================================================

// Arduino uses different instance management
// Return simple defaults
static uint8_t arduino_spi_instance_for_pin(uint8_t sck_pin)
{
	(void)sck_pin;
	return 0;  // Arduino typically has one SPI
}

static uint8_t arduino_i2c_instance_for_pin(uint8_t sda_pin)
{
	(void)sda_pin;
	return 0;  // Arduino typically has one I2C (Wire)
}

static uint8_t arduino_uart_instance_for_pin(uint8_t tx_pin)
{
	(void)tx_pin;
	return 1;  // Use Serial1 for peripheral UART
}

// ============================================================================
// PWM
// ============================================================================

static uint8_t arduino_pwm_configure(uint8_t pin, uint16_t wrap, uint16_t duty)
{
	if (!ferqon_cap_pin_supports_pwm(pin)) {
		return 0;
	}
	(void)wrap;  // Arduino analogWrite handles scaling automatically
	analogWrite(pin, duty);
	return 0;  // Return dummy instance
}

static void arduino_pwm_set_duty(uint8_t pin, uint8_t inst, uint16_t duty)
{
	if (!ferqon_cap_pin_supports_pwm(pin)) {
		return;
	}
	(void)inst;  // Unused
	analogWrite(pin, duty);
}

static int arduino_pwm_get_counter(uint8_t pin, uint8_t inst)
{
	(void)pin;  // Unused
	(void)inst;  // Unused
	// Arduino doesn't expose PWM counter directly
	return 0;
}

// ============================================================================
// ADC
// ============================================================================

static void arduino_adc_init(void)
{
	// Arduino doesn't require explicit ADC initialization
	// analogRead() handles this automatically
}

static void arduino_adc_gpio_init(uint8_t pin)
{
	// Arduino doesn't require explicit ADC GPIO initialization
	(void)pin;
}

static uint16_t arduino_adc_read(uint8_t channel)
{
	// Map channel to analog pin (A0 = channel 0, etc.)
	if (!ferqon_cap_pin_supports_adc(channel)) {
		return 0;
	}
	return analogRead(channel);
}

// ============================================================================
// SPI
// ============================================================================

static void arduino_spi_init(uint8_t inst, uint32_t baud)
{
	if (!ferqon_cap_spi_instance_is_valid(inst)) {
		return;
	}
	(void)inst;  // Arduino uses global SPI
	SPI.begin();
	// Note: Arduino SPI.begin() doesn't take baud rate directly
	// It uses default SPI clock
}

static int arduino_spi_write(uint8_t inst, const uint8_t* buf, size_t len)
{
	(void)inst;  // Arduino uses global SPI
	for (size_t i = 0; i < len; i++) {
		SPI.transfer(buf[i]);
	}
	return (int)len;
}

static int arduino_spi_read(uint8_t inst, uint8_t fill, uint8_t* buf, size_t len)
{
	(void)inst;  // Arduino uses global SPI
	for (size_t i = 0; i < len; i++) {
		buf[i] = SPI.transfer(fill);
	}
	return (int)len;
}

// ============================================================================
// I2C
// ============================================================================

static void arduino_i2c_init(uint8_t inst, uint32_t baud)
{
	if (!ferqon_cap_i2c_instance_is_valid(inst)) {
		return;
	}
	(void)inst;  // Arduino uses global Wire
	(void)baud;  // Arduino Wire uses default speed
	Wire.begin();
}

static int arduino_i2c_write(uint8_t inst, uint8_t addr, const uint8_t* buf, size_t len)
{
	(void)inst;  // Arduino uses global Wire
	Wire.beginTransmission(addr);
	Wire.write(buf, len);
	return (Wire.endTransmission() == 0) ? (int)len : -1;
}

static int arduino_i2c_read(uint8_t inst, uint8_t addr, uint8_t* buf, size_t len)
{
	(void)inst;  // Arduino uses global Wire
	Wire.requestFrom(addr, len);
	size_t received = 0;
	while (Wire.available() && received < len) {
		buf[received++] = Wire.read();
	}
	return (int)received;
}

// ============================================================================
// UART
// ============================================================================

static void arduino_uart_init(uint8_t inst, uint32_t baud)
{
	if (!ferqon_cap_uart_instance_is_valid(inst)) {
		return;
	}
	if (inst == 1) {
		Serial1.begin(baud);
	}
	// inst 0 is reserved for USB CDC (Serial)
}

static void arduino_uart_putc(uint8_t inst, char c)
{
	if (inst == 1) {
		Serial1.write(c);
	}
}

static uint8_t arduino_uart_readable(uint8_t inst)
{
	if (inst == 1) {
		return Serial1.available() > 0 ? 1 : 0;
	}
	return 0;
}

static char arduino_uart_getc(uint8_t inst)
{
	if (inst == 1) {
		return Serial1.read();
	}
	return 0;
}

// ============================================================================
// Factory function
// ============================================================================

FERQON_PLT_IoOps arduino_make_io_ops(void)
{
	FERQON_PLT_IoOps ops = {0};
	ops.gpio_init = &arduino_gpio_init;
	ops.gpio_set_dir_in = &arduino_gpio_set_dir_in;
	ops.gpio_set_dir_out = &arduino_gpio_set_dir_out;
	ops.gpio_pull_up = &arduino_gpio_pull_up;
	ops.gpio_pull_down = &arduino_gpio_pull_down;
	ops.gpio_disable_pulls = &arduino_gpio_disable_pulls;
	ops.gpio_put = &arduino_gpio_put;
	ops.gpio_get = &arduino_gpio_get;
	ops.gpio_usable = &arduino_gpio_usable;
	ops.gpio_set_func_spi = &arduino_gpio_set_func_spi;
	ops.gpio_set_func_i2c = &arduino_gpio_set_func_i2c;
	ops.gpio_set_func_uart = &arduino_gpio_set_func_uart;
	ops.gpio_set_func_pwm = &arduino_gpio_set_func_pwm;
	ops.spi_instance_for_pin = &arduino_spi_instance_for_pin;
	ops.i2c_instance_for_pin = &arduino_i2c_instance_for_pin;
	ops.uart_instance_for_pin = &arduino_uart_instance_for_pin;
	ops.pwm_configure = &arduino_pwm_configure;
	ops.pwm_set_duty = &arduino_pwm_set_duty;
	ops.pwm_get_counter = &arduino_pwm_get_counter;
	ops.adc_init = &arduino_adc_init;
	ops.adc_gpio_init = &arduino_adc_gpio_init;
	ops.adc_read = &arduino_adc_read;
	ops.spi_init = &arduino_spi_init;
	ops.spi_write = &arduino_spi_write;
	ops.spi_read = &arduino_spi_read;
	ops.i2c_init = &arduino_i2c_init;
	ops.i2c_write = &arduino_i2c_write;
	ops.i2c_read = &arduino_i2c_read;
	ops.uart_init = &arduino_uart_init;
	ops.uart_putc = &arduino_uart_putc;
	ops.uart_readable = &arduino_uart_readable;
	ops.uart_getc = &arduino_uart_getc;
	return ops;
}
