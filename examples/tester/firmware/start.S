/* SPDX-License-Identifier: 0BSD */
/* No OS, C library, external memory, constructors, or writable ROM data. */
.section .text.start,"ax",@progbits
.global _start
_start:
    la sp, _stack_top
    la t0, trap
    csrw mtvec, t0
    la t0, _bss_start
    la t1, _bss_end
1:  bgeu t0, t1, 2f
    sw zero, 0(t0)
    addi t0, t0, 4
    j 1b
2:  call main
3:  j 3b
trap:
    li a0, 4
    tail fail
