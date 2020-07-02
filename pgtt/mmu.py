"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Standard Python deps
import math
from dataclasses import dataclass
from typing import List

# Internal deps
from . import args
from . import log
from .register import Register


"""
Tables occupy one granule and each entry is a 64-bit descriptor.
"""
entries_per_table = args.tg // 8
log.debug(f"{entries_per_table=}")


"""
Number of bits required to index each byte in a granule sized page.
"""
block_offset_bits = int(math.log(args.tg, 2))
log.debug(f"{block_offset_bits=}")


"""
Number of bits required to index each entry in a complete table.
"""
table_idx_bits = int(math.log(entries_per_table, 2))
log.debug(f"{table_idx_bits=}")


"""
Starting level of translation.
"""
start_level = 3 - (args.tsz - block_offset_bits) // table_idx_bits
if (args.tsz - block_offset_bits) % table_idx_bits == 0:
    start_level = start_level + 1
    log.debug(f"start_level corrected as {args.tsz=} exactly fits in first table")
log.debug(f"{start_level=}")


def _tcr() -> str:
    """
    Generate required value for TCR_ELn.
    """
    reg = Register(f"tcr_el{args.el}")

    """
    Configurable bitfields present at all exception levels.
    """
    reg.field( 5,  0, "t0sz", 64-args.tsz)
    reg.field( 9,  8, "irgn0", 1)  # Normal WB RAWA
    reg.field(11, 10, "orgn0", 1)  # Normal WB RAWA
    reg.field(13, 12, "sh0", 3)    # Inner Shareable
    reg.field(15, 14, "tg0", {"4K":0, "16K":2, "64K":1}[args.tg_str])

    """
    Bits that are RES1 at all exception levels.
    """
    reg.res1(23) # technically epd1 at EL1 but we'll want =1 then anyway

    """
    Exception level specific differences.
    """
    ps_val = {32:0, 36:1, 40:2, 48:5}[args.tsz]
    if args.el == 1:
        reg.field(34, 32, "ps", ps_val)
    else:
        reg.field(18, 16, "ps", ps_val)
        reg.res1(31)

    return hex(reg.value())

tcr = _tcr()


"""
AttrIndx [0] = Normal Inner/Outer Write-Back RAWA
AttrIndx [1] = Device-nGnRnE
"""
mair = hex(0x00FF)
log.debug(f"mair_el{args.el}={mair}")


ttbr = hex(args.ttb)
log.debug(f"ttbr0_el{args.el}={ttbr}")


def _sctlr() -> str:
    """
    Generate required value for SCTLR_ELn.
    """
    reg = Register(f"sctlr_el{args.el}")

    """
    Configurable bitfields present at all exception levels.
    """
    reg.field( 0,  0, "m", 1)    # MMU enabled
    reg.field( 2,  2, "c", 1)    # D-side access cacheability controlled by pgtables
    reg.field(12, 12, "i", 1),   # I-side access cacheability controlled by pgtables
    reg.field(25, 25, "ee", 0),  # D-side accesses are little-endian

    """
    Bits that are RES1 at all exception levels.
    """
    [reg.res1(x) for x in [4,5,11,16,18,22,23,28,29]]

    """
    Exception level specific differences.
    """
    if args.el == 1:
        reg.res1(20)

    return hex(reg.value())

sctlr = _sctlr()


def _template_block_page( is_device:bool, is_page:bool ):
    """
    Translation table entry fields common across all exception levels.
    """
    pte = Register("pte")
    pte.field( 0,  0, "valid", 1)
    pte.field( 1,  1, "[1]", int(is_page))
    pte.field( 4,  2, "attrindx", int(is_device))
    pte.field( 9,  8, "sh", 3)  # Inner Shareable, ignored by Device memory
    pte.field(10, 10, "af", 1)  # Disable Access Flag faults

    """
    Exception level specific differences.
    """
    if args.el == 1:
        pte.field(53, 53, "pxn", int(is_device))
    else:
        pte.field(54, 54, "xn", int(is_device))

    return hex(pte.value())


def block_template( is_device:bool=True ):
    return _template_block_page(is_device, is_page=False)


def page_template( is_device:bool=True):
    return _template_block_page(is_device, is_page=True)


def table_template():
    return hex(0x3)
