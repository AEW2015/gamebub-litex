/* SPDX-License-Identifier: 0BSD
 * First CPU diagnostic: only the generated LiteX CSR map and internal BRAM.
 * Volatile MMIO and scratch accesses prevent compiler-elided self-tests.
 */
#include <stdint.h>
#include "addresses.h"

static inline void wr(uint32_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static inline uint32_t rd(uint32_t a) { return *(volatile uint32_t *)a; }
static volatile uint32_t scratch[256];

static void puts_uart(const char *s)
{
    while (*s) {
        while (rd(GB_UART_TXFULL)) { }
        wr(GB_UART_RXTX, (uint8_t)*s++);
    }
}

__attribute__((noreturn)) void fail(uint32_t reason)
{
    wr(GB_DIAGNOSTIC_RESULT, 0xbad00000u | reason);
    puts_uart("GB_FAIL\n");
    for (;;) { __asm__ volatile ("nop"); }
}

int main(void)
{
    puts_uart("GB_BOOT\n");
    for (uint32_t i = 0; i < 256; ++i)
        if (scratch[i] != 0) fail(1);
    for (uint32_t pass = 0; pass < 4; ++pass) {
        const uint32_t mask = (pass & 1) ? 0x55555555u : 0xaaaaaaaau;
        for (uint32_t i = 0; i < 256; ++i)
            scratch[i] = (i << (pass + 1)) ^ mask;
        for (uint32_t i = 0; i < 256; ++i)
            if (scratch[i] != ((i << (pass + 1)) ^ mask)) fail(1);
    }
    /* Exercise byte enables as well as full-word Wishbone traffic. */
    scratch[0] = 0x11223344u;
    ((volatile uint8_t *)scratch)[1] = 0xa5;
    if (scratch[0] != 0x1122a544u) fail(1);
    ((volatile uint16_t *)scratch)[1] = 0x5aa5;
    if (scratch[0] != 0x5aa5a544u) fail(1);
    puts_uart("RAM_OK\n");
    if (rd(GB_DIAGNOSTIC_IDENTIFIER) != 0x47424c32u) fail(2);
    puts_uart("ID_OK\n");

    /* A real LiteX countdown timer: require both progress and expiration. */
    wr(GB_TIMER0_EN, 0);
    wr(GB_TIMER0_RELOAD, 0);
    wr(GB_TIMER0_LOAD, 2000);
    wr(GB_TIMER0_EN, 1);
    wr(GB_TIMER0_UPDATE_VALUE, 1);
    uint32_t first = rd(GB_TIMER0_VALUE);
    if (first == 0 || first >= 2000) fail(3);
    uint32_t remaining = first;
    for (uint32_t n = 0; n < 10000 && remaining; ++n) {
        wr(GB_TIMER0_UPDATE_VALUE, 1);
        remaining = rd(GB_TIMER0_VALUE);
        if (remaining > first) fail(3);
    }
    if (remaining) fail(3);
    puts_uart("TIMER_OK\n");
    wr(GB_DIAGNOSTIC_RESULT, 0x600d000fu);
    puts_uart("GB_PASS\n");
    for (;;) { __asm__ volatile ("nop"); }
}
