/* SPDX-License-Identifier: CERN-OHL-S-2.0
 * Basic standalone LiteX testers. Font/layout derived from the GameBub Vivado
 * app tester; see LICENSES/CERN-OHL-S-2.0.txt. No OS or AMD software libraries.
 * ROM, stack and UI working storage stay in internal BRAM. Memory apps only
 * overwrite the explicitly reserved 4 KiB scratch window, never code/stack.
 */
#include <stdint.h>
#include "addresses.h"
static uint32_t rd(uint32_t a) { return *(volatile uint32_t *)a; }
static void wr(uint32_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static void log_short(const char *s) {
    while (*s) { if (!rd(GB_UART_TXFULL)) wr(GB_UART_RXTX, (uint8_t)*s); ++s; }
}
__attribute__((noreturn)) void fail(uint32_t code) {
    wr(GB_OUTPUTS_COMMAND,0); wr(GB_DIAGNOSTIC_RESULT,0xbad50000u|code);
    log_short("GB5_FAIL\n"); for (;;) { __asm__ volatile("nop"); }
}
static const uint8_t letters[26][7] = {
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{15,16,16,16,16,16,15},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {15,16,16,23,17,17,15},{17,17,17,31,17,17,17},{31,4,4,4,4,4,31},
 {7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31}};
static const uint8_t digits[10][7] = {
 {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},
 {30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},
 {14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},
 {14,17,17,15,1,1,14}};
static uint32_t row_words[24];
static unsigned page, state, progress, phase, offset, chunks, color;
static const char *const names[] = {"COLOR", "SRAM", "SDRAM", "AUDIO", "VIBRATION"};
static const char *const states[] = {"READY", "RUNNING", "PASS", "FAIL", "STOPPED"};
static uint32_t bad_address, expected, observed;

static void pixel(unsigned x, unsigned value) {
    unsigned shift = (x & 15u) << 1;
    row_words[x >> 4] = (row_words[x >> 4] & ~(3u << shift)) | (value << shift);
}
static void text(unsigned y, unsigned x, unsigned top, const char *s) {
    if (y < top || y >= top+7) return;
    while (*s) {
        unsigned c = (uint8_t)*s++, bits = 0;
        if (c >= 'A' && c <= 'Z') bits = letters[c-'A'][y-top];
        if (c >= '0' && c <= '9') bits = digits[c-'0'][y-top];
        if (c == '-' && y == top+3) bits = 31;
        for (unsigned i=0; i<5; ++i) if (bits & (16u >> i)) pixel(x+i, 3);
        x += 6;
    }
}
static void draw(void) {
    for (unsigned y=0; y<240; ++y) {
        for (unsigned w=0; w<24; ++w) row_words[w] = 0;
        if (y >= 56 && y < 184) {
            unsigned border = y==56 || y==183;
            row_words[5] = border ? 0xffff0000u : 0xaaaa0000u;
            for (unsigned w=6; w<17; ++w) row_words[w] = border ? 0xffffffffu : 0xaaaaaaaau;
            pixel(88,3); pixel(271,3);
            text(y, 159, 64, "GAMEBUB"); text(y, 144, 74, "LITEX TESTER");
            text(y, 100, 92, names[page]); text(y, 190, 92, states[state]);
            text(y, 100, 108, page==1 || page==2 ? "4 KIB SCRATCH AT 50 MHZ" :
                 page==3 ? "440 HZ LOW LEVEL 1 SEC" : page==4 ? "200 MS PULSE 50 DUTY" : "A CYCLES COLOR PATTERN");
            text(y, 100, 152, "A START   B STOP");
            text(y, 100, 168, "L PREV    R NEXT");
            if (y>=128 && y<138) for (unsigned x=100; x<260; ++x)
                if (y==128 || y==137 || x==100 || x==259 ||
                    (y>=131 && y<135 && x<102+progress)) pixel(x,3);
        }
        for (unsigned w=0; w<24; ++w) wr(GB_APP_OVERLAY_BASE + ((y*24+w)<<2), row_words[w]);
    }
    wr(GB_OUTPUTS_PAGE, page); wr(GB_OUTPUTS_STATE, state); wr(GB_OUTPUTS_PROGRESS, progress);
}
static uint32_t pattern(unsigned p, uint32_t a) {
    return (p==0 ? 0x55555555u : p==1 ? 0xaaaaaaaau : p==2 ? 0u : 0xffffffffu) ^ a;
}
static void memory_step(void) {
    uint32_t base = (page==1 ? GB_EXT_SRAM_BASE : GB_EXT_SDRAM_BASE)+0x1000u;
    for (unsigned i=0; i<1024; ++i) {
        uint32_t a = base+((offset+i)<<2), value = pattern(phase>>1, a);
        if (!(phase & 1u)) wr(a, value);
        else if (rd(a) != value) {
            state=3; bad_address=a; expected=value; observed=rd(a);
            log_short("GB5_FAIL\n"); return;
        }
    }
    offset += 1024; ++chunks; progress = (chunks*156u)>>3;
    if (offset==1024) { offset=0; ++phase; if (phase==8) {state=2; progress=156;
        wr(GB_DIAGNOSTIC_MEMORY_PASS,rd(GB_DIAGNOSTIC_MEMORY_PASS)|(page==1?1u:2u));} }
}
static void stop_all(void) { wr(GB_OUTPUTS_COMMAND,0); if (state==1) state=4; }
int main(void) {
    /* Conservative startup identity check; the interactive tests follow. */
    wr(GB_DIAGNOSTIC_RESULT,0x47423500u);
    while (!rd(GB_DIAGNOSTIC_SDRAM_READY)) { }
    if (rd(GB_ESP32_BASE)!=0x56313032u) { wr(GB_DIAGNOSTIC_RESULT,0xbad50003u); for (;;) {} }
    draw(); wr(GB_DIAGNOSTIC_RESULT,0x600d500fu); log_short("GB5_OK\n");
    uint32_t previous=rd(GB_DIAGNOSTIC_BUTTONS), frame=rd(GB_DIAGNOSTIC_VIDEO_FRAMES), last_log=frame;
    unsigned release = previous==0, last_raw=previous, stable=previous, debounce=0;
    for (;;) {
        uint32_t now=rd(GB_DIAGNOSTIC_VIDEO_FRAMES);
        if (now==frame) continue;
        frame=now;
        uint32_t raw=rd(GB_DIAGNOSTIC_BUTTONS);
        if (raw==last_raw) { if (debounce<2) ++debounce; } else {last_raw=raw; debounce=0;}
        if (debounce>=1) stable=raw;
        uint32_t edge=stable & ~previous; previous=stable;
        if (!stable) release=1;
        unsigned dirty=0;
        if (edge & 0x300u) {
            stop_all(); page = edge&0x200u ? (page==4 ? 0 : page+1) : (page==0 ? 4 : page-1);
            state=0; progress=0; release=0; dirty=1;
        }
        if (stable&2u) { stop_all(); dirty=1; }
        if ((edge&1u) && release) {
            release=0; progress=0; phase=0; offset=0; chunks=0;
            bad_address=0; wr(GB_DIAGNOSTIC_RESULT,0x600d500fu);
            if (page==0) { color=color==5?0:color+1; wr(GB_OUTPUTS_COLOR,color); state=0; }
            else if (page<=2) state=1;
            else {wr(GB_OUTPUTS_COMMAND,page==3?1:2); state=1;}
            dirty=1;
        }
        if (state==1) {
            if (page==1 || page==2) memory_step();
            else if (!(rd(page==3?GB_OUTPUTS_AUDIO_MS:GB_OUTPUTS_MOTOR_MS))) {state=2; progress=156;}
            dirty=1;
        }
        if (dirty) draw();
        if (now-last_log>=60) {log_short("GB5_OK\n"); last_log=now;}
        /* Keep mismatch evidence observable in the debugger without stdio. */
        if (bad_address) { wr(GB_DIAGNOSTIC_RESULT,0xbad50000u|page); (void)expected; (void)observed; }
    }
}
