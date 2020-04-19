"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Internal deps
from . import args
from . import log
from . import mmu
from . import table
from .mmap import Region


def generate_asm() -> str:
    """
    Output asm to generate the translation tables.
    """
    string = ""
    for n,t in enumerate(table.Table._allocated):
        string +=\
f"""

program_table_{n}:
    LDR     x8, ={hex(t.addr)}          // base address of this table"""
        for idx in sorted(list(t.entries.keys())):
            entry = t.entries[idx]
            string +=\
f"""
program_table_{n}_entry_{idx}:"""
            if type(entry) is Region:
                if entry.is_device:
                    template_reg = "x2" if t.level < 3 else "x4"
                else:
                    template_reg = "x3" if t.level < 3 else "x5"
                string +=\
f"""
    LDR     x9, ={hex(entry.addr)}      // output address
    ORR     x9, x9, {template_reg}      // merge with template"""
            else:
                string +=\
f"""
    LDR     x9, ={hex(entry.addr)}      // next-level table address
    ORR     x9, x9, x6                  // merge with template"""
            string +=\
f"""
    MOV     x10, #{idx}                 // write entry
    STR     x9, [x8, x10, lsl #3]"""
    return string


_tmp =\
"""
/*
 * this file was automatically generated using arm64-pgtable-tool.
 * see: github.com/ashwio/arm64-pgtable-tool
 *
 * your translation tables:
 *
"""

for line in str(table.root).splitlines():
    _tmp += f" * {line}\n"
_tmp += " *\n"

for line in table.Table.usage().splitlines():
    _tmp += f" * {line}\n"
_tmp += " */"

_tmp +=\
f"""

    .section .data.mmu
    .balign 2

    mmu_lock: .4byte 0                  // lock to ensure only 1 CPU runs init
    #define LOCKED 1

    mmu_init: .4byte 0                  // whether init has been run
    #define INITIALISED 1

    .section .text.mmu_on
    .balign 2
    .global mmu_on
    .type mmu_on, @function

mmu_on:
    ADRP    x0, mmu_lock                // get 4KB page containing mmu_lock
    ADD     x0, x0, :lo12:mmu_lock      // restore low 12 bits lost by ADRP
    MOV     w1, #LOCKED
    SEVL                                // first retry pass won't sleep on WFE

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
    LDR     x2, ={mmu.ttbr}             // address of first table
    LDR     x3, ={hex(args.tg * len(table.Table._allocated))}  // combined length of all tables
    LSR     x3, x3, #5                  // number of required STP instructions
    FMOV    d0, xzr

zero_table_loop:
    STP     q0, q0, [x2], #32           // zero out 4 table entries at a time
    SUBS    x3, x3, #1
    B.NE    zero_table_loop

load_templates:
    LDR     x2, ={mmu.block_template(is_device=True)}   // Device block
    LDR     x3, ={mmu.block_template(is_device=False)}  // Normal block
    LDR     x4, ={mmu.page_template(is_device=True)}    // Device page
    LDR     x5, ={mmu.page_template(is_device=False)}   // Normal page
    LDR     x6, ={mmu.table_template()}                 // Next-level table
    {generate_asm()}

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

output = ""
for line in _tmp.splitlines():
    if "//" in line:
        idx = line.index("//")
        code = line[:idx].rstrip()
        comment = line[idx:]
        line = f"{code}{' ' * (41 - len(code))}{comment}"
    output += f"{line}\n"

[log.verbose(line) for line in output.splitlines()]
