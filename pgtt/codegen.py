"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Internal deps
from . import args
from . import mmu
from . import table



def asm( t:table.Table=table.root ) -> str:
    return ""




template =\
f"""
    #define LOCKED      1
    #define INITIALISED 1

    .section .data.mmu
    .balign 2
    mmu_lock: .4byte 0                  // lock to ensure only 1 CPU runs init
    mmu_init: .4byte 0                  // whether init has been run

    .global mmu_on
    .type mmu_on, @function
    .section .text.mmu_on
    .balign 2
mmu_on:
    ADRP    x0, mmu_lock                // get 4KB page containing mmu_lock
    ADD     x0, x0, :lo12:mmu_lock      // restore low 12 bits lost by ADRP
    MOV     w1, #LOCKED
    SEVL                                // first pass through retry won't sleep
retry_lock:
    WFE                                 // go to sleep until an event
    LDAXR   w2, [x0]                    // read mmu_lock
    CBNZ    w2, retry_lock              // not available, go back to sleep
    STXR    w3, w1, [x0]                // try to acquire mmu_lock
    CBNZ    w3, retry_lock              // failed, go back to sleep
check_already_initialised:
    ADRP    x1, mmu_init                // get 4KB page containing mmu_init
    ADD     x1, x1, :lo12:mmu_init      // restore low 12 bits lost by ADRP
    LDR     w2, [x1]                    // read mmu_init
    CBNZ    w2, end                     // init already run, skip to the end
zero_tables:
    LDR     x2, ={mmu.ttbr}
    LDR     x3, ={hex(args.tg * len(table.Table._allocated))}
    LSR     x3, x3, #5
    EOR     q0, q0, q0
    EOR     q1, q1, q1
zero_loop:
    STP     q0, q1, [x2], #32
    SUBS    x3, x3, #32
    B.NE    zero_loop
load_templates:
    LDR     x2, ={mmu.block_template(is_device=True)}   // Device block
    LDR     x3, ={mmu.block_template(is_device=False)}  // Normal block
    LDR     x4, ={mmu.page_template(is_device=True)}    // Device page
    LDR     x5, ={mmu.page_template(is_device=False)}   // Normal page
    LDR     x6, ={mmu.table_template()}                 // Next-level table
program_tables:
    {asm()}
init_complete:
    MOV     w2, #INITIALISED
    STR     w2, [x1]
end:
    LDR     x1, ={mmu.ttbr}             // program ttbr0 on this CPU
    MSR     ttbr0_el{args.el}, x1
    LDR     x1, ={mmu.mair}             // program mair on this CPU
    MSR     mair_el{args.el}, x1
    LDR     x1, ={mmu.tcr}              // program tcr on this CPU
    MSR     tcr_el{args.el}, x1
    LDR     x1, ={mmu.sctlr}            // program sctlr on this CPU
    MSR     sctlr_el{args.el}, x1
    ISB                                 // synchronize context on this CPU
    STLR    wzr, [x0]                   // release mmu_lock
    RET                                 // done!
"""
