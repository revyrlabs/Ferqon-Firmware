/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * Arduino.h
 * ---------
 * Native host shim for the Arduino runtime used by Ferqon firmware.
 *
 * This header is included by all firmware .cpp files when building the
 * Software-in-the-Loop (SIL) desktop target. It replaces the microcontroller
 * Arduino core with POSIX/Linux equivalents:
 *
 *   - Serial  -> TCP server on localhost (configurable via FERQON_SIL_PORT)
 *   - Serial1 -> in-memory loopback UART for hil_uart_send/expect tests
 *
 * Default TCP port for the SIL control UART. Override with FERQON_SIL_PORT
 * env var or by passing a port argument to host_main.
 *   - GPIO    -> in-memory pin state table
 *   - ADC     -> deterministic mock values
 *   - millis()/delay() -> host monotonic clock / sleep
 *
 * The firmware source files are not modified; this shim is injected at compile
 * time by putting sil/ on the include path before the system Arduino headers.
 */
#ifndef SIL_ARDUINO_H
#define SIL_ARDUINO_H

#include <cstdint>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <string>
#include <deque>
#include <chrono>
#include <thread>
#include <mutex>

/* ------------------------------------------------------------------ Types */
typedef bool boolean;

/* ----------------------------------------------------------------- Macros */
#define PROGMEM
#define F(s) (s)
#define pgm_read_byte(addr) (*(const uint8_t *)(addr))
#define pgm_read_word(addr) (*(const uint16_t *)(addr))

/* Default localhost TCP port for the SIL control UART. */
#define FERQON_SIL_DEFAULT_PORT 3333

/* ----------------------------------------------------------------- Pins */
#define HIGH 0x1
#define LOW  0x0

#define INPUT           0x0
#define OUTPUT          0x1
#define INPUT_PULLUP    0x2
#define INPUT_PULLDOWN  0x3

#define CHANGE  1
#define RISING  2
#define FALLING 3

#define LSBFIRST 0
#define MSBFIRST 1

/* ----------------------------------------------------------------- Time */
unsigned long millis(void);
unsigned long micros(void);
void delay(unsigned long ms);
void delayMicroseconds(unsigned int us);

/* ----------------------------------------------------------------- GPIO */
void pinMode(uint8_t pin, uint8_t mode);
int digitalRead(uint8_t pin);
void digitalWrite(uint8_t pin, uint8_t val);
int analogRead(uint8_t pin);
void analogWrite(uint8_t pin, int val);
unsigned long pulseIn(uint8_t pin, uint8_t state, unsigned long timeout_us);
void analogReadResolution(uint8_t bits);
void analogReference(uint8_t type);

/* ----------------------------------------------------------------- Math/misc */
long random(long howbig);
long random(long howsmall, long howbig);
long map(long x, long in_min, long in_max, long out_min, long out_max);

/* ----------------------------------------------------------------- Serial */
class SilSerial {
public:
    explicit SilSerial(bool is_server = false, uint16_t port = 0);
    ~SilSerial();

    /* Arduino-style API */
    void begin(unsigned long baud);
    void end();
    int available();
    int read();
    size_t write(const uint8_t *data, size_t len);
    void flush();

    size_t print(const char *s);
    size_t print(int n);
    size_t print(unsigned int n);
    size_t print(long n);
    size_t print(unsigned long n);
    size_t print(double n);

    size_t println(const char *s);
    size_t println(int n);
    size_t println(unsigned int n);
    size_t println(long n);
    size_t println(unsigned long n);
    size_t println(double n);
    size_t println(void);

    /* SIL-specific configuration */
    void set_port(uint16_t port) { m_port = port; }

    /* Test helpers */
    void inject_rx(const uint8_t *data, size_t len);
    bool client_connected() const { return m_client >= 0; }

private:
    bool m_is_server;
    uint16_t m_port;

    int m_sock = -1;
    int m_client = -1;

    std::deque<uint8_t> m_rx;
    mutable std::mutex m_rx_mtx;

    /* For the TCP serial: poll the socket for new data/connections. */
    void poll_rx(int timeout_ms);
    bool accept_client();
    void close_client();
};

extern SilSerial Serial;
extern SilSerial Serial1;

#endif /* SIL_ARDUINO_H */
