/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * Arduino.cpp
 * ---------
 * Implementation of the Software-in-the-Loop Arduino shim declared in
 * sil/Arduino.h.  See that header for the design overview.
 */
#include "Arduino.h"

#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <poll.h>
#include <errno.h>
#include <signal.h>
#include <iostream>
#include <sstream>
#include <iomanip>

/* ------------------------------------------------------------------ Time */
static std::chrono::steady_clock::time_point s_boot_time(void) {
    static std::chrono::steady_clock::time_point t =
        std::chrono::steady_clock::now();
    return t;
}

unsigned long millis(void) {
    auto now = std::chrono::steady_clock::now();
    return static_cast<unsigned long>(
        std::chrono::duration_cast<std::chrono::milliseconds>(now - s_boot_time())
            .count());
}

unsigned long micros(void) {
    auto now = std::chrono::steady_clock::now();
    return static_cast<unsigned long>(
        std::chrono::duration_cast<std::chrono::microseconds>(now - s_boot_time())
            .count());
}

void delay(unsigned long ms) {
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

void delayMicroseconds(unsigned int us) {
    if (us > 0) {
        std::this_thread::sleep_for(std::chrono::microseconds(us));
    }
}

/* ------------------------------------------------------------------ GPIO */
static constexpr size_t PIN_COUNT = 256;
static uint8_t s_pin_mode[PIN_COUNT] = {0};
static uint8_t s_pin_value[PIN_COUNT] = {0};
static uint16_t s_analog_value[PIN_COUNT] = {0};

void pinMode(uint8_t pin, uint8_t mode) {
    if (pin < PIN_COUNT) {
        s_pin_mode[pin] = mode;
    }
}

int digitalRead(uint8_t pin) {
    if (pin < PIN_COUNT) {
        return (s_pin_value[pin] == LOW) ? LOW : HIGH;
    }
    return LOW;
}

void digitalWrite(uint8_t pin, uint8_t val) {
    if (pin < PIN_COUNT) {
        s_pin_value[pin] = (val == LOW) ? LOW : HIGH;
    }
}

int analogRead(uint8_t pin) {
    if (pin < PIN_COUNT) {
        return static_cast<int>(s_analog_value[pin]);
    }
    return 0;
}

void analogWrite(uint8_t pin, int val) {
    if (pin < PIN_COUNT) {
        s_analog_value[pin] = static_cast<uint16_t>(val & 0xFFFF);
    }
}

unsigned long pulseIn(uint8_t pin, uint8_t state, unsigned long timeout_us) {
    (void)pin;
    (void)state;
    (void)timeout_us;
    /* No external edges in the SIL mock; always report timeout. */
    return 0;
}

void analogReadResolution(uint8_t bits) { (void)bits; }
void analogReference(uint8_t type) { (void)type; }

/* ------------------------------------------------------------------ Misc */
long random(long howbig) {
    if (howbig <= 0) return 0;
    return static_cast<long>(std::rand() % howbig);
}

long random(long howsmall, long howbig) {
    if (howbig <= howsmall) return howsmall;
    return howsmall + static_cast<long>(std::rand() % (howbig - howsmall));
}

long map(long x, long in_min, long in_max, long out_min, long out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

/* ------------------------------------------------------------------ Serial */
static uint16_t s_default_port = 3333;

void SilSerial::set_default_port(uint16_t port) {
    s_default_port = port;
}

SilSerial::SilSerial(bool is_server, uint16_t port)
    : m_is_server(is_server), m_port(port) {
    if (!m_is_server) {
        /* Loopback serial has no network socket. */
        m_sock = -1;
        m_client = -1;
    }
}

SilSerial::~SilSerial() {
    end();
}

void SilSerial::begin(unsigned long baud) {
    (void)baud;
    if (!m_is_server) {
        return;
    }
    if (m_sock >= 0) {
        return; /* already listening */
    }

    if (m_port == 0) {
        const char *env_port = std::getenv("FERQON_SIL_PORT");
        m_port = env_port ? static_cast<uint16_t>(std::atoi(env_port)) : s_default_port;
    }
    if (m_port == 0) {
        m_port = 3333;
    }

    m_sock = ::socket(AF_INET, SOCK_STREAM, 0);
    if (m_sock < 0) {
        std::cerr << "[SIL] socket() failed: " << strerror(errno) << std::endl;
        return;
    }

    int opt = 1;
    if (::setsockopt(m_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        std::cerr << "[SIL] setsockopt() failed: " << strerror(errno) << std::endl;
    }

    int flags = ::fcntl(m_sock, F_GETFL, 0);
    if (flags >= 0) {
        ::fcntl(m_sock, F_SETFL, flags | O_NONBLOCK);
    }

    struct sockaddr_in addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = ::htons(m_port);

    if (::bind(m_sock, reinterpret_cast<struct sockaddr *>(&addr), sizeof(addr)) < 0) {
        std::cerr << "[SIL] bind() failed on port " << m_port << ": "
                  << strerror(errno) << std::endl;
        ::close(m_sock);
        m_sock = -1;
        return;
    }

    if (::listen(m_sock, 1) < 0) {
        std::cerr << "[SIL] listen() failed: " << strerror(errno) << std::endl;
        ::close(m_sock);
        m_sock = -1;
        return;
    }
}

void SilSerial::end() {
    if (m_client >= 0) {
        ::close(m_client);
        m_client = -1;
    }
    if (m_sock >= 0) {
        ::close(m_sock);
        m_sock = -1;
    }
}

void SilSerial::close_client() {
    if (m_client >= 0) {
        ::close(m_client);
        m_client = -1;
    }
}

bool SilSerial::accept_client() {
    struct sockaddr_in cli;
    socklen_t len = sizeof(cli);
    int c = ::accept(m_sock, reinterpret_cast<struct sockaddr *>(&cli), &len);
    if (c < 0) {
        return false;
    }
    if (m_client >= 0) {
        ::close(m_client);
    }
    m_client = c;
    int flags = ::fcntl(m_client, F_GETFL, 0);
    if (flags >= 0) {
        ::fcntl(m_client, F_SETFL, flags | O_NONBLOCK);
    }
    return true;
}

void SilSerial::poll_rx(int timeout_ms) {
    if (!m_is_server) {
        return;
    }
    if (m_sock < 0) {
        begin(115200);
    }
    if (m_sock < 0) {
        return;
    }

    struct pollfd fds[2];
    int nfds = 0;
    fds[nfds].fd = m_sock;
    fds[nfds].events = POLLIN;
    nfds++;

    if (m_client >= 0) {
        fds[nfds].fd = m_client;
        fds[nfds].events = POLLIN | POLLERR | POLLHUP;
        nfds++;
    }

    int rc = ::poll(fds, nfds, timeout_ms);
    if (rc <= 0) {
        return;
    }

    if (fds[0].revents & POLLIN) {
        accept_client();
    }

    if (nfds > 1) {
        if (fds[1].revents & POLLIN) {
            uint8_t buf[512];
            ssize_t n = ::recv(m_client, buf, sizeof(buf), 0);
            if (n > 0) {
                std::lock_guard<std::mutex> lk(m_rx_mtx);
                m_rx.insert(m_rx.end(), buf, buf + n);
            } else if (n == 0 || (errno != EAGAIN && errno != EINTR)) {
                close_client();
            }
        }
        if (fds[1].revents & (POLLERR | POLLHUP)) {
            close_client();
        }
    }
}

int SilSerial::available() {
    poll_rx(0);
    std::lock_guard<std::mutex> lk(m_rx_mtx);
    return static_cast<int>(m_rx.size());
}

int SilSerial::read() {
    poll_rx(0);
    std::lock_guard<std::mutex> lk(m_rx_mtx);
    if (m_rx.empty()) {
        return -1;
    }
    uint8_t b = m_rx.front();
    m_rx.pop_front();
    return static_cast<int>(b);
}

size_t SilSerial::write(const uint8_t *data, size_t len) {
    if (len == 0 || data == nullptr) {
        return 0;
    }
    if (!m_is_server) {
        /* Serial1 loopback: everything written becomes available to read. */
        std::lock_guard<std::mutex> lk(m_rx_mtx);
        m_rx.insert(m_rx.end(), data, data + len);
        return len;
    }

    if (m_client < 0) {
        /* No active TCP client yet; drop the bytes silently. */
        return len;
    }

    size_t written = 0;
    while (written < len) {
        ssize_t n = ::send(m_client, data + written, len - written, MSG_NOSIGNAL);
        if (n < 0) {
            if (errno == EAGAIN || errno == EINTR) {
                continue;
            }
            close_client();
            return written;
        }
        if (n == 0) {
            close_client();
            return written;
        }
        written += static_cast<size_t>(n);
    }
    return written;
}

void SilSerial::flush() {}

void SilSerial::inject_rx(const uint8_t *data, size_t len) {
    if (data && len > 0) {
        std::lock_guard<std::mutex> lk(m_rx_mtx);
        m_rx.insert(m_rx.end(), data, data + len);
    }
}

/* print / println helpers */
size_t SilSerial::print(const char *s) {
    if (!s) return 0;
    return write(reinterpret_cast<const uint8_t *>(s), std::strlen(s));
}

size_t SilSerial::print(int n) { return print(std::to_string(n).c_str()); }
size_t SilSerial::print(unsigned int n) { return print(std::to_string(n).c_str()); }
size_t SilSerial::print(long n) { return print(std::to_string(n).c_str()); }
size_t SilSerial::print(unsigned long n) { return print(std::to_string(n).c_str()); }

size_t SilSerial::print(double n) {
    std::ostringstream oss;
    oss << std::setprecision(6) << n;
    return print(oss.str().c_str());
}

size_t SilSerial::println(const char *s) {
    size_t n = print(s);
    n += print("\r\n");
    return n;
}

size_t SilSerial::println(int n) { return println(std::to_string(n).c_str()); }
size_t SilSerial::println(unsigned int n) { return println(std::to_string(n).c_str()); }
size_t SilSerial::println(long n) { return println(std::to_string(n).c_str()); }
size_t SilSerial::println(unsigned long n) { return println(std::to_string(n).c_str()); }

size_t SilSerial::println(double n) {
    std::ostringstream oss;
    oss << std::setprecision(6) << n;
    return println(oss.str().c_str());
}

size_t SilSerial::println(void) {
    return print("\r\n");
}

/* Global serial objects */
SilSerial Serial(true, 0);
SilSerial Serial1(false, 0);
