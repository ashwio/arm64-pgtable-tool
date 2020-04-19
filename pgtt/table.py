"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Standard Python deps
from dataclasses import dataclass
from typing import List

# Internal deps
from . import args
from . import log
from . import mmu
from .mmap import MemoryRegion


_allocated_tables = []


class Table:
    """
    Class representing a translation table.
    """
    def __init__( self, addr:int, level:int, va_base:int ):
        self.addr = addr
        self.level = level
        self.chunk = args.tg << ((3 - self.level) * mmu.table_idx_bits)
        self.va_base = va_base
        self.entries = {}


    def map( self, region:MemoryRegion ) -> None:
        """
        Map a region of memory in this translation table.
        """
        log.debug()
        log.debug(f"mapping region {hex(region.addr)} in level {self.level} table")
        log.debug(region)
        assert(region.addr >= self.va_base)
        assert(region.addr + region.length <= self.va_base + mmu.entries_per_table * self.chunk)


        def prepare_next_table( idx:int, va_base:int=None ) -> None:
            if not idx in self.entries:
                self.entries[idx] = alloc(
                    self.level + 1,
                    va_base if not va_base is None else (self.va_base + idx * self.chunk)
                )


        """
        Calculate number of chunks required to map this region.
        A chunk is the area mapped by each individual entry in this table.
        """
        num_chunks = region.length // self.chunk
        start_idx = (region.addr // self.chunk) % mmu.entries_per_table

        """
        Check whether the region is "floating".
        If so, dispatch to next-level table and we're finished.

                    +--------------------+
                 // |                    |
            Chunk - |####################| <-- Floating region
                 \\ |                    |
                    +--------------------+
        """
        if num_chunks == 0:
            log.debug(f"floating region, dispatching to next-level table")
            prepare_next_table(start_idx)
            self.entries[start_idx].map(region)
            return

        """
        Check for any "underflow".
        If so, dispatch the underflow to next-level table and proceed.

                    +--------------------+
                 // |####################|
            Chunk - |####################|
                 \\ |####################|
                    +--------------------+
                 // |####################| <-- Underflow
            Chunk - |                    |
                 \\ |                    |
                    +--------------------+
        """
        underflow = region.addr % self.chunk
        if underflow:
            log.debug(f"{underflow=}, dispatching to next-level table")
            prepare_next_table(start_idx)
            self.entries[start_idx].map(region.copy(length=(self.chunk - underflow)))
            start_idx = start_idx + 1

        """
        Check for any "overflow".

                    +--------------------+
                 // |                    |
            Chunk - |                    |
                 \\ |####################| <-- Overflow
                    +--------------------+
                 // |####################|
            Chunk - |####################|
                 \\ |####################|
                   +--------------------+
        """
        overflow = (region.addr + region.length) % self.chunk
        if overflow:
            log.debug(f"{overflow=}, dispatching to next-level table")
            final_idx = start_idx + num_chunks - (not not underflow)
            va_base = ((region.addr + region.length) // self.chunk) * self.chunk
            prepare_next_table(final_idx, va_base)
            self.entries[final_idx].map(region.copy(addr=va_base, length=overflow))

        """
        Handle any remaining complete chunks.
        """
        region.length = self.chunk
        blocks_allowed = self.level >= (1 if args.tg == 4*1024 else 2)
        if underflow + overflow == self.chunk:
            num_chunks = num_chunks - 1
        for i in range(start_idx, start_idx + num_chunks):
            log.debug(f"mapping complete chunk at index {i}")
            r = region.copy(addr=(self.va_base + i * self.chunk))
            if not blocks_allowed:
                prepare_next_table(i)
                self.entries[i].map(r)
            else:
                self.entries[i] = r


    def __str__( self ) -> str:
        """
        Recursively crawl this table to generate a pretty-printable string.
        """
        margin = " " * (self.level - mmu.start_level + 1) * 8
        string = f"{margin}level {self.level} table @ {hex(self.addr)}\n"
        for k in sorted(list(self.entries.keys())):
            entry = self.entries[k]
            if type(entry) is Table:
                header = "{}[#{:>4}]".format(margin, k)
                nested_table = str(entry)
                hyphens = "-" * (len(nested_table.splitlines()[0]) - len(header))
                string += f"{header}" + hyphens + f"\\\n{nested_table}"
            else:
                string += "{}[#{:>4}] 0x{:>012}-0x{:>012}, {}, {}\n".format(
                    margin,
                    k,
                    hex(entry.addr)[2:],
                    hex(entry.addr + entry.length - 1)[2:],
                    "Device" if entry.is_device else "Normal",
                    entry.label
                )
        assert string
        return string


    def contiguous_blocks( self ) -> List[MemoryRegion]:
        """
        Get list of contiguous index ranges that can be looped through by the
        code generator.
        """
        ranges = []
        keys = sorted(self.entries.keys())
        while keys:
            if keys[1] - keys[0] == 1:
                # Keys are consecutive
            else:
                ranges.append(keys[0], keys[0], )


def alloc( level:int, va_base:int ) -> Table:
    """
    We need to track how many tables are "allocated" by the tool as the user
    will need reserve space for them in the buffer pointed to by ttbr0_eln.
    """
    global _allocated_tables
    addr = args.ttb + len(_allocated_tables) * args.tg
    _allocated_tables.append(Table(addr, level, va_base))
    log.debug(f"allocated table #{len(_allocated_tables)} @ {hex(addr)}")
    return _allocated_tables[-1]
