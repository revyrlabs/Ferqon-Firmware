/**
 * pico_io.cpp
 * -----------
 * RP2040 / Raspberry Pi Pico implementation of Ferqon platform I/O API.
 *
 * This file is the ONLY place in the codebase that is allowed to include Pico SDK
 * hardware peripheral headers.  All general code must go through the
 * FERQON_PLT_ API instead.
 *
 * RP2040 peripheral pin routing
 * ─────────────────────────────
 * SPI  : SPI0 on pins  0–19,  SPI1 on pins 20–29
 * I2C  : I2C0 on pins where (pin % 4) < 2,  I2C1 otherwise
 * UART : UART0 on GPIO 0/1/12/13/16/17,  UART1 on the rest
 * PWM  : one slice per two GPIO pins;  slice = pin / 2
 * ADC  : channels 0–2 on GPIO 26–28
 */

#include "platform/ferqon_plt_io.h"
#include "pico_backend_internal.hpp"
#include "../generated/pin_macros.h"

#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "hardware/adc.h"
#include "hardware/spi.h"
#include "hardware/i2c.h"
#include "hardware/uart.h"

#include <stddef.h>

// ============================================================================
// Internal helpers — convert instance index → SDK pointer
// ============================================================================

static inline spi_inst_t*  spi_from_inst(uint8_t inst)  { return inst == 0 ? spi0  : spi1;  }
static inline i2c_inst_t*  i2c_from_inst(uint8_t inst)  { return inst == 0 ? i2c0  : i2c1;  }
static inline uart_inst_t* uart_from_inst(uint8_t inst) { return inst == 0 ? uart0 : uart1; }

// ============================================================================
// GPIO
// ============================================================================

static void pico_gpio_init(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_init(pin);
    }
}

static void pico_gpio_set_dir_in(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_set_dir(pin, GPIO_IN);
    }
}

static void pico_gpio_set_dir_out(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_set_dir(pin, GPIO_OUT);
    }
}

static void pico_gpio_pull_up(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_pull_up(pin);
    }
}

static void pico_gpio_pull_down(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_pull_down(pin);
    }
}

static void pico_gpio_disable_pulls(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_disable_pulls(pin);
    }
}

static void pico_gpio_put(uint8_t pin, uint8_t on)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_put(pin, on ? 1 : 0);
    }
}

static uint8_t pico_gpio_get(uint8_t pin)
{
    if (!ferqon_cap_pin_is_valid(pin)) {
        return 0;
    }
    return gpio_get(pin);
}

static uint8_t pico_gpio_usable(uint8_t pin)
{
	return ferqon_cap_pin_is_valid(pin) && !ferqon_cap_pin_is_reserved(pin);
}

// ============================================================================
// Pin function assignment
// ============================================================================

static void pico_gpio_set_func_spi(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_set_function(pin, GPIO_FUNC_SPI);
    }
}

static void pico_gpio_set_func_i2c(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_set_function(pin, GPIO_FUNC_I2C);
    }
}

static void pico_gpio_set_func_uart(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_set_function(pin, GPIO_FUNC_UART);
    }
}

static void pico_gpio_set_func_pwm(uint8_t pin)
{
    if (ferqon_cap_pin_is_valid(pin)) {
        gpio_set_function(pin, GPIO_FUNC_PWM);
    }
}

// ============================================================================
// Instance routing
// ============================================================================

static uint8_t pico_spi_instance_for_pin(uint8_t sck_pin)
{
	// SPI0 clocks live on GP2, GP6, GP10, GP14, GP18 (and also pin ≤19 in general);
	// use the simple split: ≤19 → SPI0, 20+ → SPI1.
	return (sck_pin <= 19) ? 0 : 1;
}

static uint8_t pico_i2c_instance_for_pin(uint8_t sda_pin)
{
	// I2C0 SDA on GP0,4,8,12,16,20; I2C1 SDA on GP2,6,10,14,18,22,26
	return ((sda_pin % 4) < 2) ? 0 : 1;
}

static uint8_t pico_uart_instance_for_pin(uint8_t tx_pin)
{
	// UART0 TX: GP0, GP12, GP16 (and their adjacent RX pairs GP1/13/17)
	if (tx_pin == 0 || tx_pin == 12 || tx_pin == 16 ||
	    tx_pin == 1 || tx_pin == 13 || tx_pin == 17)
		return 0;
	return 1;
}

// ============================================================================
// PWM
// ============================================================================

static uint8_t pico_pwm_configure(uint8_t pin, uint16_t wrap, uint16_t duty)
{
    if (!ferqon_cap_pin_supports_pwm(pin)) {
        return 0;
    }
	gpio_set_function(pin, GPIO_FUNC_PWM);
	uint slice   = pwm_gpio_to_slice_num(pin);
	uint channel = pwm_gpio_to_channel(pin);
	pwm_set_wrap(slice, wrap);
	pwm_set_chan_level(slice, channel, duty);
	pwm_set_enabled(slice, true);
	return (uint8_t)slice;
}

static void pico_pwm_set_duty(uint8_t pin, uint8_t inst, uint16_t duty)
{
    if (!ferqon_cap_pin_supports_pwm(pin)) {
        return;
    }
	uint channel = pwm_gpio_to_channel(pin);
	pwm_set_chan_level((uint)inst, channel, duty);
}

static int pico_pwm_get_counter(uint8_t pin, uint8_t inst)
{
	(void)pin;  // Unused
	return (int)pwm_get_counter((uint)inst);
}

// ============================================================================
// ADC
// ============================================================================

static void pico_adc_init(void)
{
	adc_init();
}

static void pico_adc_gpio_init(uint8_t pin)
{
    if (ferqon_cap_pin_supports_adc(pin)) {
        adc_gpio_init(pin);
    }
}

static uint16_t pico_adc_read(uint8_t channel)
{
	adc_select_input(channel);
	return adc_read();
}

// ============================================================================
// SPI
// ============================================================================

static void pico_spi_init(uint8_t inst, uint32_t baud)
{
    if (!ferqon_cap_spi_instance_is_valid(inst)) {
        return;
    }
	spi_init(spi_from_inst(inst), baud);
}

static int pico_spi_write(uint8_t inst, const uint8_t* buf, size_t len)
{
	return (int)spi_write_blocking(spi_from_inst(inst), buf, len);
}

static int pico_spi_read(uint8_t inst, uint8_t fill, uint8_t* buf, size_t len)
{
	return (int)spi_read_blocking(spi_from_inst(inst), fill, buf, len);
}

// ============================================================================
// I2C
// ============================================================================

static void pico_i2c_init(uint8_t inst, uint32_t baud)
{
    if (!ferqon_cap_i2c_instance_is_valid(inst)) {
        return;
    }
	i2c_init(i2c_from_inst(inst), baud);
}

static int pico_i2c_write(uint8_t inst, uint8_t addr, const uint8_t* buf, size_t len)
{
	return i2c_write_blocking(i2c_from_inst(inst), addr, buf, len, false);
}

static int pico_i2c_read(uint8_t inst, uint8_t addr, uint8_t* buf, size_t len)
{
	return i2c_read_blocking(i2c_from_inst(inst), addr, buf, len, false);
}

// ============================================================================
// UART
// ============================================================================

static void pico_uart_init(uint8_t inst, uint32_t baud)
{
    if (!ferqon_cap_uart_instance_is_valid(inst)) {
        return;
    }
	uart_init(uart_from_inst(inst), baud);
}

static void pico_uart_putc(uint8_t inst, char c)
{
	uart_putc_raw(uart_from_inst(inst), c);
}

static uint8_t pico_uart_readable(uint8_t inst)
{
	return uart_is_readable(uart_from_inst(inst)) ? 1 : 0;
}

static char pico_uart_getc(uint8_t inst)
{
	return uart_getc(uart_from_inst(inst));
}

// ============================================================================
// Factory function
// ============================================================================

FERQON_PLT_IoOps pico_make_io_ops(void)
{
	FERQON_PLT_IoOps ops = {0};
	ops.gpio_init = &pico_gpio_init;
	ops.gpio_set_dir_in = &pico_gpio_set_dir_in;
	ops.gpio_set_dir_out = &pico_gpio_set_dir_out;
	ops.gpio_pull_up = &pico_gpio_pull_up;
	ops.gpio_pull_down = &pico_gpio_pull_down;
	ops.gpio_disable_pulls = &pico_gpio_disable_pulls;
	ops.gpio_put = &pico_gpio_put;
	ops.gpio_get = &pico_gpio_get;
	ops.gpio_usable = &pico_gpio_usable;
	ops.gpio_set_func_spi = &pico_gpio_set_func_spi;
	ops.gpio_set_func_i2c = &pico_gpio_set_func_i2c;
	ops.gpio_set_func_uart = &pico_gpio_set_func_uart;
	ops.gpio_set_func_pwm = &pico_gpio_set_func_pwm;
	ops.spi_instance_for_pin = &pico_spi_instance_for_pin;
	ops.i2c_instance_for_pin = &pico_i2c_instance_for_pin;
	ops.uart_instance_for_pin = &pico_uart_instance_for_pin;
	ops.pwm_configure = &pico_pwm_configure;
	ops.pwm_set_duty = &pico_pwm_set_duty;
	ops.pwm_get_counter = &pico_pwm_get_counter;
	ops.adc_init = &pico_adc_init;
	ops.adc_gpio_init = &pico_adc_gpio_init;
	ops.adc_read = &pico_adc_read;
	ops.spi_init = &pico_spi_init;
	ops.spi_write = &pico_spi_write;
	ops.spi_read = &pico_spi_read;
	ops.i2c_init = &pico_i2c_init;
	ops.i2c_write = &pico_i2c_write;
	ops.i2c_read = &pico_i2c_read;
	ops.uart_init = &pico_uart_init;
	ops.uart_putc = &pico_uart_putc;
	ops.uart_readable = &pico_uart_readable;
	ops.uart_getc = &pico_uart_getc;
	return ops;
}
