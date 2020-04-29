# arm64-pgtable-tool

## Introduction

Tool for automatically generating MMU and translation table setup code, whether to drag and drop into your own bare metal arm64 projects or to assist you in your own learning.

For more information see [my blog post](https://ashw.io/blog/arm64-pgtable-tool).

## Prerequisites

* Python 3.8+
* [chaimleib's IntervalTree](https://github.com/chaimleib/intervaltree)

```
    pip install intervaltree
```


## Usage

The following command-line options are available:

```
    -i SRC                  input memory map file
    -o DST                  output GNU assembly file
    -ttb TTB                desired translation table base address
    -el {1,2,3}             exception level (default: 2)
    -tg {4K,16K,64K}        translation granule (default: 4K)
    -tsz {32,36,40,48}      address space size (default: 32)
```

### Input memory map file

The input memory map file is a simple comma-separated text file with format:

```
    ADDRESS, LENGTH, TYPE, LABEL
```

Where:

* `ADDRESS` is the hexadecimal base address of the region;
* `LENGTH` is the length of the region in bytes, using `K`, `M`, or `G` to specify the unit;
* `TYPE` is either `DEVICE` for Device-nGnRnE or `NORMAL` for Normal Inner/Outer Write-Back RAWA Inner Shareable;
* `LABEL` is a human-friendly label describing what is being mapped.

Several memory map files are provided in the [examples folder](examples).

### Translation table base address

This must be the base address of a granule aligned buffer that is at least large enough to contain the number of translation tables allocated by the tool.

You can see this in the generated GNU assembly file:

```
    /*
     * ...
     *
     * This memory map requires a total of 7 translation tables.
     * Each table occupies 4K of memory (0x1000 bytes).
     * The buffer pointed to by 0x90000000 must therefore be 7x 4K = 0x7000 bytes long.
     * It is the programmer's responsibility to guarantee this.
     *
     * ...
     */
```

It is also your responsibility to ensure the memory region containing the buffer is described as `NORMAL` in the input memory map file.

### Exception level

The tool only programs `TTBR0_ELn` at the specified exception level. Where two virtual address spaces are available, such as at EL1, the higher virtual address space pointed to by `TTBR1_ELn` is disabled.

The tool currently has no concept of two security states. If running in the Secure world, all entries default to Secure.

### Translation granule

The `4K` and `64K` granules have been tested on the Armv8-A Foundation Platform FVP. Unfortunately the `16K` granule is not supported by this FVP so has not been tested.

### Address space size

The tool only generates 1-to-1 mappings, often referred to as a "flat map" or "identity map". With this in mind, only a limited subset of possible virtual address space sizes are supported, corresponding to the available physical address space sizes defined by the Armv8-A architecture.

## Example output

Running the following command:

```
    python3.8 generate.py -i examples/base-fvp-minimal.txt -o fvp.S -ttb 0x90000000 -el 2 -tg 64K -tsz 32
```

Where `examples/fvp-base-minimal.txt` contains:

```
    0x01C090000,   4K, DEVICE, UART0
    0x02C000000,   8K, DEVICE, GICC
    0x02E000000,  64K, NORMAL, Non-Trusted SRAM
    0x02F000000,  64K, DEVICE, GICv3 GICD
    0x02F100000,   1M, DEVICE, GICv3 GICR
    0x080000000,   2G, NORMAL, Non-Trusted DRAM
```

Generates the following `fvp.S` GNU assembly file:

```
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
     *         level 2 table @ 0x90000000
     *         [#   0]---------------------------\
     *                 level 3 table @ 0x90010000
     *                 [#7177] 0x00001c090000-0x00001c09ffff, Device, UART0
     *         [#   1]---------------------------\
     *                 level 3 table @ 0x90020000
     *                 [#3072] 0x00002c000000-0x00002c00ffff, Device, GICC
     *                 [#3584] 0x00002e000000-0x00002e00ffff, Normal, Non-Trusted SRAM
     *                 [#3840] 0x00002f000000-0x00002f00ffff, Device, GICv3 GICD
     *                 [#3856] 0x00002f100000-0x00002f10ffff, Device, GICv3 GICR
     *                 [#3857] 0x00002f110000-0x00002f11ffff, Device, GICv3 GICR
     *                 [#3858] 0x00002f120000-0x00002f12ffff, Device, GICv3 GICR
     *                 [#3859] 0x00002f130000-0x00002f13ffff, Device, GICv3 GICR
     *                 [#3860] 0x00002f140000-0x00002f14ffff, Device, GICv3 GICR
     *                 [#3861] 0x00002f150000-0x00002f15ffff, Device, GICv3 GICR
     *                 [#3862] 0x00002f160000-0x00002f16ffff, Device, GICv3 GICR
     *                 [#3863] 0x00002f170000-0x00002f17ffff, Device, GICv3 GICR
     *                 [#3864] 0x00002f180000-0x00002f18ffff, Device, GICv3 GICR
     *                 [#3865] 0x00002f190000-0x00002f19ffff, Device, GICv3 GICR
     *                 [#3866] 0x00002f1a0000-0x00002f1affff, Device, GICv3 GICR
     *                 [#3867] 0x00002f1b0000-0x00002f1bffff, Device, GICv3 GICR
     *                 [#3868] 0x00002f1c0000-0x00002f1cffff, Device, GICv3 GICR
     *                 [#3869] 0x00002f1d0000-0x00002f1dffff, Device, GICv3 GICR
     *                 [#3870] 0x00002f1e0000-0x00002f1effff, Device, GICv3 GICR
     *                 [#3871] 0x00002f1f0000-0x00002f1fffff, Device, GICv3 GICR
     *         [#   4] 0x000080000000-0x00009fffffff, Normal, Non-Trusted DRAM
     *         [#   5] 0x0000a0000000-0x0000bfffffff, Normal, Non-Trusted DRAM
     *         [#   6] 0x0000c0000000-0x0000dfffffff, Normal, Non-Trusted DRAM
     *         [#   7] 0x0000e0000000-0x0000ffffffff, Normal, Non-Trusted DRAM
     *
     * The following command line arguments were passed to arm64-pgtable-tool:
     *
     *      -i examples/base-fvp-minimal.txt
     *      -ttb 0x90000000
     *      -el 2
     *      -tg 64K
     *      -tsz 32
     *
     * This memory map requires a total of 3 translation tables.
     * Each table occupies 64K of memory (0x10000 bytes).
     * The buffer pointed to by 0x90000000 must therefore be 3x 64K = 0x30000 bytes long.
     * It is the programmer's responsibility to guarantee this.
     *
     * The programmer must also ensure that the virtual memory region containing the
     * translation tables is itself marked as NORMAL in the memory map file.
     */

        .section .data.mmu
        .balign 2

        mmu_lock: .4byte 0                   // lock to ensure only 1 CPU runs init
        #define LOCKED 1

        mmu_init: .4byte 0                   // whether init has been run
        #define INITIALISED 1

        .section .text.mmu_on
        .balign 2
        .global mmu_on
        .type mmu_on, @function

    mmu_on:

        ADRP    x0, mmu_lock                 // get 4KB page containing mmu_lock
        ADD     x0, x0, :lo12:mmu_lock       // restore low 12 bits lost by ADRP
        MOV     w1, #LOCKED
        SEVL                                 // first pass won't sleep
    1:
        WFE                                  // sleep on retry
        LDAXR   w2, [x0]                     // read mmu_lock
        CBNZ    w2, 1b                       // not available, go back to sleep
        STXR    w3, w1, [x0]                 // try to acquire mmu_lock
        CBNZ    w3, 1b                       // failed, go back to sleep

    check_already_initialised:

        ADRP    x1, mmu_init                 // get 4KB page containing mmu_init
        ADD     x1, x1, :lo12:mmu_init       // restore low 12 bits lost by ADRP
        LDR     w2, [x1]                     // read mmu_init
        CBNZ    w2, end                      // init already done, skip to the end

    zero_out_tables:

        LDR     x2, =0x90000000              // address of first table
        LDR     x3, =0x30000                 // combined length of all tables
        LSR     x3, x3, #5                   // number of required STP instructions
        FMOV    d0, xzr                      // clear q0
    1:
        STP     q0, q0, [x2], #32            // zero out 4 table entries at a time
        SUBS    x3, x3, #1
        B.NE    1b

    load_descriptor_templates:

        LDR     x2, =0x40000000000705        // Device block
        LDR     x3, =0x40000000000707        // Device page
        LDR     x4, =0x701                   // Normal block
        LDR     x5, =0x703                   // Normal page

    program_table_0:

        LDR     x8, =0x90000000              // base address of this table
        LDR     x9, =0x20000000              // chunk size

    program_table_0_entry_0:

        LDR     x10, =0                      // idx
        LDR     x11, =0x90010000             // next-level table address
        ORR     x11, x11, #0x3               // next-level table descriptor
        STR     x11, [x8, x10, lsl #3]       // write entry into table

    program_table_0_entry_1:

        LDR     x10, =1                      // idx
        LDR     x11, =0x90020000             // next-level table address
        ORR     x11, x11, #0x3               // next-level table descriptor
        STR     x11, [x8, x10, lsl #3]       // write entry into table

    program_table_0_entry_4_to_7:

        LDR     x10, =4                      // idx
        LDR     x11, =4                      // number of contiguous entries
        LDR     x12, =0x80000000             // output address of entry[idx]
    1:
        ORR     x12, x12, x4                 // merge output address with template
        STR     X12, [x8, x10, lsl #3]       // write entry into table
        ADD     x10, x10, #1                 // prepare for next entry idx+1
        ADD     x12, x12, x9                 // add chunk to address
        SUBS    x11, x11, #1                 // loop as required
        B.NE    1b

    program_table_1:

        LDR     x8, =0x90010000              // base address of this table
        LDR     x9, =0x10000                 // chunk size

    program_table_1_entry_7177:

        LDR     x10, =7177                   // idx
        LDR     x11, =1                      // number of contiguous entries
        LDR     x12, =0x1c090000             // output address of entry[idx]
    1:
        ORR     x12, x12, x3                 // merge output address with template
        STR     X12, [x8, x10, lsl #3]       // write entry into table
        ADD     x10, x10, #1                 // prepare for next entry idx+1
        ADD     x12, x12, x9                 // add chunk to address
        SUBS    x11, x11, #1                 // loop as required
        B.NE    1b

    program_table_2:

        LDR     x8, =0x90020000              // base address of this table
        LDR     x9, =0x10000                 // chunk size

    program_table_2_entry_3072:

        LDR     x10, =3072                   // idx
        LDR     x11, =1                      // number of contiguous entries
        LDR     x12, =0x2c000000             // output address of entry[idx]
    1:
        ORR     x12, x12, x3                 // merge output address with template
        STR     X12, [x8, x10, lsl #3]       // write entry into table
        ADD     x10, x10, #1                 // prepare for next entry idx+1
        ADD     x12, x12, x9                 // add chunk to address
        SUBS    x11, x11, #1                 // loop as required
        B.NE    1b

    program_table_2_entry_3584:

        LDR     x10, =3584                   // idx
        LDR     x11, =1                      // number of contiguous entries
        LDR     x12, =0x2e000000             // output address of entry[idx]
    1:
        ORR     x12, x12, x5                 // merge output address with template
        STR     X12, [x8, x10, lsl #3]       // write entry into table
        ADD     x10, x10, #1                 // prepare for next entry idx+1
        ADD     x12, x12, x9                 // add chunk to address
        SUBS    x11, x11, #1                 // loop as required
        B.NE    1b

    program_table_2_entry_3840:

        LDR     x10, =3840                   // idx
        LDR     x11, =1                      // number of contiguous entries
        LDR     x12, =0x2f000000             // output address of entry[idx]
    1:
        ORR     x12, x12, x3                 // merge output address with template
        STR     X12, [x8, x10, lsl #3]       // write entry into table
        ADD     x10, x10, #1                 // prepare for next entry idx+1
        ADD     x12, x12, x9                 // add chunk to address
        SUBS    x11, x11, #1                 // loop as required
        B.NE    1b

    program_table_2_entry_3856_to_3871:

        LDR     x10, =3856                   // idx
        LDR     x11, =16                     // number of contiguous entries
        LDR     x12, =0x2f100000             // output address of entry[idx]
    1:
        ORR     x12, x12, x3                 // merge output address with template
        STR     X12, [x8, x10, lsl #3]       // write entry into table
        ADD     x10, x10, #1                 // prepare for next entry idx+1
        ADD     x12, x12, x9                 // add chunk to address
        SUBS    x11, x11, #1                 // loop as required
        B.NE    1b

    init_done:

        MOV     w2, #INITIALISED
        STR     w2, [x1]

    end:

        LDR     x1, =0x90000000              // program ttbr0 on this CPU
        MSR     ttbr0_el2, x1
        LDR     x1, =0xff                    // program mair on this CPU
        MSR     mair_el2, x1
        LDR     x1, =0x80807520              // program tcr on this CPU
        MSR     tcr_el2, x1
        ISB
        MRS     x2, tcr_el2                  // verify CPU supports desired config
        CMP     x2, x1
        B.NE    .
        LDR     x1, =0x30c51835              // program sctlr on this CPU
        MSR     sctlr_el2, x1
        ISB                                  // synchronize context on this CPU
        STLR    wzr, [x0]                    // release mmu_lock
        RET                                  // done!
```
