/* SPDX-License-Identifier: 0BSD
 * Destructive volatile-memory smoke test; ROM, stack and BSS stay in BRAM.
 * No host interaction is required to start video, service QSPI or finish tests.
 */
#include <stdint.h>
#include "addresses.h"
static inline uint32_t rd(uint32_t a) { return *(volatile uint32_t *)a; }
static inline void wr(uint32_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static void log_short(const char *s)
{
    /* A disconnected JTAG UART must never hold up the CPU or board services. */
    while (*s) { if (!rd(GB_UART_TXFULL)) wr(GB_UART_RXTX, (uint8_t)*s); ++s; }
}
__attribute__((noreturn)) void fail(uint32_t code)
{
    wr(GB_DIAGNOSTIC_RESULT, 0xbad40000u | code);
    log_short("GB4_FAIL\n");
    for (;;) { __asm__ volatile("nop"); }
}
static void memory_test(uint32_t base, uint32_t size, uint32_t reason)
{
    const uint32_t offsets[] = {0, 4, 0x1000, 0x1ffc, 0x2000, 0x8000, size >> 1, size - 4};
    for (uint32_t pass = 0; pass < 4; ++pass) {
        uint32_t mask = (pass & 1) ? 0xaaaaaaaau : 0x55555555u;
        for (uint32_t i = 0; i < 8; ++i) wr(base + offsets[i], mask ^ offsets[i] ^ (i << 24));
        for (uint32_t i = 0; i < 8; ++i)
            if (rd(base + offsets[i]) != (mask ^ offsets[i] ^ (i << 24))) fail(reason);
    }
    wr(base + 0x1000, 0x11223344u);
    *(volatile uint8_t *)(base + 0x1001) = 0xa5;
    if (rd(base + 0x1000) != 0x1122a544u) fail(reason);
    *(volatile uint16_t *)(base + 0x1002) = 0x5aa5;
    if (rd(base + 0x1000) != 0x5aa5a544u) fail(reason);
}
int main(void)
{
    wr(GB_DIAGNOSTIC_RESULT, 0x47423400u);
    memory_test(GB_EXT_SRAM_BASE, GB_EXT_SRAM_BYTES, 1);
    wr(GB_DIAGNOSTIC_MEMORY_PASS, 1);
    uint32_t timeout = 1000000;
    while (!rd(GB_DIAGNOSTIC_SDRAM_READY) && --timeout) { }
    if (!timeout) fail(2);
    memory_test(GB_EXT_SDRAM_BASE, GB_EXT_SDRAM_BYTES, 2);
    wr(GB_DIAGNOSTIC_MEMORY_PASS, 3);
    if (rd(GB_ESP32_BASE) != 0x56313032u) fail(3);
    timeout = 1000000;
    while (rd(GB_DIAGNOSTIC_VIDEO_FRAMES) < 3 && --timeout) { }
    if (!timeout) fail(4);
    wr(GB_DIAGNOSTIC_RESULT, 0x600d400fu);
    log_short("GB4_OK\n");
    /* Vivado may probe USER1 after configuration. Repeat without blocking so
     * a monitor attached later can still observe the completed smoke test. */
    uint32_t last_report = rd(GB_DIAGNOSTIC_VIDEO_FRAMES);
    for (;;) {
        uint32_t now = rd(GB_DIAGNOSTIC_VIDEO_FRAMES);
        if (now - last_report >= 60) { log_short("GB4_OK\n"); last_report = now; }
    }
}
