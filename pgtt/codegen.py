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


asm_header = """
/*
 * This file was automatically generated using arm64-pgtable-tool.
 * See: https://github.com/ashwio/arm64-pgtable-tool
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 * This code programs the following translation table structure:
 *
{}
 *
 * The following command line arguments were passed to arm64-pgtable-tool:
 *
 *      -i {}
 *      -ttb {}
 *      -el {}
 *      -tg {}
 *      -tsz {}
{}
{}
 * It is the programmer's responsibility to guarantee this.
 *
 * The programmer must also ensure that the virtual memory region containing the
 * translation tables is itself marked as NORMAL in the memory map file.
 */
"""


asm_prologue = """

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

mmu_on:"""


asm_acquire_lock = """

    ADRP    x0, mmu_lock                // get 4KB page containing mmu_lock
    ADD     x0, x0, :lo12:mmu_lock      // restore low 12 bits lost by ADRP
    MOV     w1, #LOCKED
    SEVL                                // first pass won't sleep
1:
    WFE                                 // sleep on retry
    LDAXR   w2, [x0]                    // read mmu_lock
    CBNZ    w2, 1b                      // not available, go back to sleep
    STXR    w3, w1, [x0]                // try to acquire mmu_lock
    CBNZ    w3, 1b                      // failed, go back to sleep"""


asm_check_init = """

check_already_initialised:

    ADRP    x1, mmu_init                // get 4KB page containing mmu_init
    ADD     x1, x1, :lo12:mmu_init      // restore low 12 bits lost by ADRP
    LDR     w2, [x1]                    // read mmu_init
    CBNZ    w2, end                     // init already done, skip to the end"""


asm_zero_tables = """

zero_out_tables:

    LDR     x2, ={}                     // address of first table
    LDR     x3, ={}                     // combined length of all tables
    LSR     x3, x3, #5                  // number of required STP instructions
    FMOV    d0, xzr                     // clear q0
1:
    STP     q0, q0, [x2], #32           // zero out 4 table entries at a time
    SUBS    x3, x3, #1
    B.NE    1b"""


asm_load_templates = """

load_descriptor_templates:

    LDR     x2, ={}                     // Device block
    LDR     x3, ={}                     // Device page
    LDR     x4, ={}                     // Normal block
    LDR     x5, ={}                     // Normal page"""


asm_table_header = """

program_table_{}:

    LDR     x8, ={}                     // base address of this table
    LDR     x9, ={}                     // chunk size"""


asm_block_entry_range = """

program_table_{}_entry_{}{}:

    LDR     x10, ={}                    // idx
    LDR     x11, ={}                    // number of contiguous entries
    LDR     x12, ={}                    // output address of entry[idx]
1:
    ORR     x12, x12, {}                // merge output address with template
    STR     X12, [x8, x10, lsl #3]      // write entry into table
    ADD     x10, x10, #1                // prepare for next entry idx+1
    ADD     x12, x12, x9                // add chunk to address
    SUBS    x11, x11, #1                // loop as required
    B.NE    1b"""


asm_next_level_table = """

program_table_{}_entry_{}:

    LDR     x10, ={}                    // idx
    LDR     x11, ={}                    // next-level table address
    ORR     x11, x11, #0x3              // next-level table descriptor
    STR     x11, [x8, x10, lsl #3]      // write entry into table"""
 

asm_epilogue = """

init_done:

    MOV     w2, #INITIALISED
    STR     w2, [x1]

end:
    LDR     x1, ={}                     // program ttbr0 on this CPU
    MSR     ttbr0_el{}, x1
    LDR     x1, ={}                     // program mair on this CPU
    MSR     mair_el{}, x1
    LDR     x1, ={}                     // program tcr on this CPU
    MSR     tcr_el{}, x1
    ISB
    MRS     x2, tcr_el{}                // verify CPU supports desired config
    CMP     x2, x1
    B.NE    .
    LDR     x1, ={}                     // program sctlr on this CPU
    MSR     sctlr_el{}, x1
    ISB                                 // synchronize context on this CPU
    STLR    wzr, [x0]                   // release mmu_lock
    RET                                 // done!"""


def generate_asm() -> str:
    """
    Output asm to generate the translation tables.
    """
    string  = asm_header.format(
        "\n".join([f" * {ln}" for ln in str(table.root).splitlines()]),
        args.i,
        hex(args.ttb),
        args.el,
        {4*1024:"4K", 16*1024:"16K", 64*1024:"64K"}[args.tg],
        args.tsz,
        " * \n * WARNING: -tg 16K has not been tested.\n * " if args.tg == 16*1024 else " * ",
        "\n".join([f" * {ln}" for ln in table.Table.usage().splitlines()]),
    )
    string += asm_prologue
    string += asm_acquire_lock
    string += asm_check_init
    string += asm_zero_tables.format(hex(args.ttb), hex(args.tg * len(table.Table._allocated)))
    string += asm_load_templates.format(
        mmu.block_template(is_device=True),
        mmu.page_template(is_device=True),
        mmu.block_template(is_device=False),
        mmu.page_template(is_device=False)
    )
    for n,t in enumerate(table.Table._allocated):
        string += asm_table_header.format(n, hex(t.addr), hex(t.chunk))
        keys = sorted(list(t.entries.keys()))
        while keys:
            idx = keys[0]
            entry = t.entries[idx]
            if type(entry) is Region:
                if entry.is_device:
                    template_register = "x2" if t.level < 3 else "x3"
                else:
                    template_register = "x4" if t.level < 3 else "x5"  
                string += asm_block_entry_range.format(
                    n,
                    idx,
                    f"_to_{idx + entry.num_contig - 1}" if entry.num_contig > 1 else "",
                    idx,
                    entry.num_contig,
                    hex(entry.addr),
                    template_register
                )
                for k in range(idx, idx+entry.num_contig):
                    keys.remove(k)
            else:
                string += asm_next_level_table.format(n, idx, idx, hex(entry.addr))
                keys.remove(idx)
    string += asm_epilogue.format(
        mmu.ttbr, args.el,
        mmu.mair, args.el,
        mmu.tcr, args.el,
        args.el,
        mmu.sctlr, args.el
    )
    return string


output = ""
_tmp = generate_asm()
for line in _tmp.splitlines():
    if "//" in line and not " * " in line:
        idx = line.index("//")
        code = line[:idx].rstrip()
        comment = line[idx:]
        line = f"{code}{' ' * (41 - len(code))}{comment}"
    output += f"{line}\n"

[log.verbose(line) for line in output.splitlines()]
