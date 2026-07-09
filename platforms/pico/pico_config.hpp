/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/**
 * pico_config.hpp
 * ---------------
 * Persistent key/value store backed by the RP2040's flash memory.
 *
 * Reserves the last 4 KiB sector of flash for a tiny configuration block.
 * Currently stores:
 *   - USB Product-ID  (16-bit)
 *   - USB Vendor-ID   (16-bit)
 *
 * The block is versioned so that future firmware can migrate gracefully.
 *
 * IMPORTANT: flash writes erase a full 4 KiB sector.  Do not call
 * save() in a tight loop — only on user-initiated SET_PID commands.
 */
#pragma once

#include <cstdint>
#include "hardware/flash.h"
#include "hardware/sync.h"
#include "pico/stdlib.h"
#include <cstring>
#include <cstdio>

namespace ferqon {

// We store our config in the *last* flash sector.
// RP2040 has 2 MiB flash by default ( PICO_FLASH_SIZE_BYTES ).
static constexpr uint32_t CONFIG_FLASH_OFFSET =
    PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE;          // e.g. 0x1FF000

static constexpr uint32_t CONFIG_MAGIC = 0x484C5843;    // "HLXC"
static constexpr uint8_t  CONFIG_VERSION = 1;

struct __attribute__((packed)) ConfigBlock {
    uint32_t magic;          // CONFIG_MAGIC
    uint8_t  version;        // CONFIG_VERSION
    uint16_t usb_vid;        // stored VID
    uint16_t usb_pid;        // stored PID
    uint8_t  _reserved[247]; // pad to 256 bytes (FLASH_PAGE_SIZE)
};

static_assert(sizeof(ConfigBlock) == 256, "ConfigBlock must equal FLASH_PAGE_SIZE");

class PicoConfig {
public:
    /**
     * Load config from flash.  If the magic/version don't match we keep
     * the compile-time defaults and mark dirty=false (no auto-save).
     */
    void load() {
        const uint8_t* flash_data =
            (const uint8_t*)(XIP_BASE + CONFIG_FLASH_OFFSET);
        std::memcpy(&m_block, flash_data, sizeof(m_block));

        if (m_block.magic != CONFIG_MAGIC || m_block.version != CONFIG_VERSION) {
            // First boot or format mismatch — use compile-time defaults
            m_block.magic   = CONFIG_MAGIC;
            m_block.version = CONFIG_VERSION;
            m_block.usb_vid = USBD_VID;
            m_block.usb_pid = USBD_PID;
            m_dirty = false;
        }
    }

    /** Save config to flash (erases + programs one sector). */
    void save() {
        uint8_t page[FLASH_PAGE_SIZE];
        std::memset(page, 0xFF, sizeof(page));
        std::memcpy(page, &m_block, sizeof(m_block));

        uint32_t ints = save_and_disable_interrupts();
        flash_range_erase(CONFIG_FLASH_OFFSET, FLASH_SECTOR_SIZE);
        flash_range_program(CONFIG_FLASH_OFFSET, page, FLASH_PAGE_SIZE);
        restore_interrupts(ints);

        m_dirty = false;
    }

    uint16_t vid() const { return m_block.usb_vid; }
    uint16_t pid() const { return m_block.usb_pid; }

    void set_vid(uint16_t v) { m_block.usb_vid = v; m_dirty = true; }
    void set_pid(uint16_t p) { m_block.usb_pid = p; m_dirty = true; }
    bool dirty() const { return m_dirty; }

    /**
     * Print the current config as JSON over USB-CDC.
     */
    void print_pid() const {
        printf("{\"ok\":true,\"vid\":\"0x%04X\",\"pid\":\"0x%04X\"}\n",
               m_block.usb_vid, m_block.usb_pid);
    }

    void print_version() const {
        printf("{\"ok\":true,\"firmware_version\":\"%s\","
               "\"vid\":\"0x%04X\",\"pid\":\"0x%04X\"}\n",
               FERQON_FW_VERSION, m_block.usb_vid, m_block.usb_pid);
    }

private:
    ConfigBlock m_block{};
    bool m_dirty = false;
};

} // namespace ferqon
