/* SPDX-License-Identifier: CERN-OHL-S-2.0
 * Supplemental host test of the exact C routines; not CPU/RTL evidence.
 */
#include <assert.h>
#include <stdio.h>
#include <sys/mman.h>
#define main firmware_main
#include "firmware/main.c"
#undef main

static void reserve(uintptr_t address, unsigned bytes) {
    void *p=mmap((void *)address,bytes,PROT_READ|PROT_WRITE,
                 MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    assert(p==(void *)address);
}
static void scratch(unsigned selected, uint32_t base) {
    page=selected;state=1;phase=offset=chunks=progress=bad_address=0;
    wr(base+0xffc,0x11223344);wr(base+0x2000,0x55667788);
    for(unsigned i=0;i<8;++i)memory_step();
    assert(state==2&&progress==156);
    assert(rd(base+0xffc)==0x11223344&&rd(base+0x2000)==0x55667788);
    for(unsigned i=0;i<1024;++i)
        assert(rd(base+0x1000+(i<<2))==pattern(3,base+0x1000+(i<<2)));
    phase=offset=chunks=progress=bad_address=0;state=1;
    memory_step();wr(base+0x1030,rd(base+0x1030)^1);memory_step();
    assert(state==3&&bad_address==base+0x1030);
}
int main(void) {
    reserve(GB_EXT_SRAM_BASE,0x10000);reserve(GB_EXT_SDRAM_BASE,0x10000);
    reserve(GB_APP_OVERLAY_BASE,0x8000);reserve(0xf0000000,0x4000);
    page=state=progress=0;draw();
    volatile uint32_t *fb=(volatile uint32_t *)(uintptr_t)GB_APP_OVERLAY_BASE;
    assert(fb[56*24+5]==0xffff0000u);assert(fb[0]==0);
    assert(((fb[60*24+(100>>4)]>>((100&15)*2))&3)==2);
    assert(((fb[64*24+(160>>4)]>>((160&15)*2))&3)==3);
    scratch(1,GB_EXT_SRAM_BASE);scratch(2,GB_EXT_SDRAM_BASE);
    assert(rd(GB_DIAGNOSTIC_MEMORY_PASS)==3);
    state=1;wr(GB_OUTPUTS_COMMAND,3);stop_all();assert(state==4&&rd(GB_OUTPUTS_COMMAND)==0);
    puts("FIRMWARE_HOST_PASS both4KiB_windows guards patterns corruption UI stop");
}
