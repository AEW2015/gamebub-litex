/* SPDX-License-Identifier: 0BSD
 * Runs only in the combined simulation until separately qualified for hardware.
 * External-memory tests are destructive; code, stack and BSS remain in BRAM.
 */
#include <stdint.h>
#include "addresses.h"
static inline uint32_t rd(uint32_t a) { return *(volatile uint32_t *)a; }
static inline void wr(uint32_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static void serial(const char *s)
{
    while (*s) {
        while (rd(GB_UART_TXFULL)) { }
        wr(GB_UART_RXTX, (uint8_t)*s++);
    }
}
__attribute__((noreturn)) void fail(uint32_t reason)
{
    wr(GB_DIAGNOSTIC_RESULT, 0xbad30000u | reason);
    serial("GB3_FAIL\n");
    for (;;) { __asm__ volatile ("nop"); }
}
static void memory_test(uint32_t base, uint32_t bytes, uint32_t reason)
{
    /* Distributed locations detect truncation/aliasing, not just local RAM.
     * All writes precede reads so an aliased address cannot pass its own echo.
     */
    const uint32_t offsets[] = {0, 4, 0x1000, 0x1ffc, 0x2000, 0x8000,
                               bytes >> 1, bytes - 4};
    for (uint32_t pass = 0; pass < 4; ++pass) {
        uint32_t mask = (pass & 1) ? 0xaaaaaaaau : 0x55555555u;
        for (uint32_t i = 0; i < 8; ++i)
            wr(base + offsets[i], mask ^ offsets[i] ^ (i << 24));
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
    serial("GB3_BOOT\n");
    memory_test(GB_EXT_SRAM_BASE, GB_EXT_SRAM_BYTES, 1);
    serial("SRAM_OK\n");
    uint32_t timeout = 1000000;
    while (!rd(GB_DIAGNOSTIC_SDRAM_READY) && --timeout) { }
    if (!timeout) fail(2);
    memory_test(GB_EXT_SDRAM_BASE, GB_EXT_SDRAM_BYTES, 2);
    serial("SDRAM_OK\n");
    /* Observe the actual serial endpoint through its CDC diagnostic window.
     * The testbench separately checks pin transactions, IRQ/ack and LCD pixels.
     */
    if (rd(GB_ESP32_BASE) != 0x56313032u) fail(3);
    wr(GB_ESP32_BASE, 0xffffffffu); /* Read-only diagnostics must stay read-only. */
    if (rd(GB_ESP32_BASE) != 0x56313032u || rd(GB_ESP32_BASE + 0x100) != 0) fail(3);
    timeout = 1000000;
    while (rd(GB_ESP32_BASE + 8) < 5 && --timeout) { }
    if (!timeout) fail(3);
    if (rd(GB_ESP32_BASE + 0x38) == 0) fail(3);
    serial("ESP32_OK\n");
    timeout = 1000000;
    while (rd(GB_DIAGNOSTIC_VIDEO_FRAMES) < 3 && --timeout) { }
    if (!timeout) fail(4);
    serial("VIDEO_OK\n");
    wr(GB_DIAGNOSTIC_RESULT, 0x600d300fu);
    serial("GB3_PASS\n");
    for (;;) { __asm__ volatile ("nop"); }
}
