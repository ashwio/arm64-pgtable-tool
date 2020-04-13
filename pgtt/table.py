"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Standard Python deps
from dataclasses import dataclass

# Internal deps
from . import args
from . import log
from . import mmu
from .mmap import MemoryRegion


num_allocated_tables = 0


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


    def map( self, region:MemoryRegion ):
        log.debug(f"mapping region {hex(region.addr)} in level {self.level} table")
        log.debug(region)

        """
        Calculate number of chunks required to map this region.
        A chunk is the area mapped by each individual entry in this table.
        """
        num_chunks = region.length // self.chunk
        log.debug(f"{num_chunks=}")
        start_idx = (region.addr // self.chunk) % mmu.entries_per_table
        log.debug(f"{start_idx=}")

        """
        Check whether the region is "floating".

                    +--------------------+
                  / |                    |
            Chunk - |####################| <-- Floating region
                  \ |                    |
                    +--------------------+
        """
        if num_chunks == 0:
            log.debug(f"floating region")
            if not start_idx in self.entries:
                self.entries[start_idx] = alloc(self.level+1,
                    self.va_base + start_idx * self.chunk)
            self.entries[start_idx].map(region)
            return

        """
        Check for any "underflow".

                    +--------------------+
                  / |####################|
            Chunk - |####################|
                  \ |####################|
                    +--------------------+
                  / |####################| <-- Underflow
            Chunk - |                    |
                  \ |                    |
                    +--------------------+
        """
        underflow = region.addr % self.chunk
        if underflow:
            log.debug(f"{underflow=}")
            if not start_idx in self.entries:
                self.entries[start_idx] = alloc(self.level+1,
                    self.va_base + start_idx * self.chunk)

            self.entries[start_idx].map(MemoryRegion(
                lineno = region.lineno,
                label = region.label,
                addr = region.addr,
                length = self.chunk - underflow,
                is_device = region.is_device,
            ))

            start_idx = start_idx + 1

        """
        Check for any "overflow".

                    +--------------------+
                  / |                    |
            Chunk - |                    |
                  \ |####################| <-- Overflow
                    +--------------------+
                  / |####################|
            Chunk - |####################|
                  \ |####################|
                    +--------------------+
        """
        overflow = (region.addr + region.length) % self.chunk
        if overflow:
            log.debug(f"{overflow=}")

            va_base = ((region.addr + region.length) // self.chunk) * self.chunk
            final_idx = start_idx + num_chunks - (not not underflow)

            if not final_idx in self.entries:
                self.entries[final_idx] = alloc(self.level+1, va_base)

            self.entries[final_idx].map(MemoryRegion(
                lineno = region.lineno,
                label = region.label,
                addr = va_base,
                length = overflow,
                is_device = region.is_device,
            ))

        """
        Now we can handle any remaining complete chunks.
        """
        if underflow + overflow == self.chunk:
            num_chunks = num_chunks - 1

        min_block_level = 1 if args.tg == 4*1024 else 2
        for i in range(start_idx, start_idx + num_chunks):
            log.debug(f"mapping complete chunk at index {i}")
            subregion = MemoryRegion(
                lineno = region.lineno,
                label = region.label,
                addr = self.va_base + i * self.chunk,
                length = self.chunk,
                is_device = region.is_device,
            )

            if self.level < min_block_level:
                if not i in self.entries:
                    self.entries[i] = alloc(self.level+1, self.va_base + i * self.chunk)
                self.entries[i].map(subregion)
            else:
                self.entries[i] = subregion


    def __str__( self ):
        margin = " " * (self.level - mmu.start_level) * 4
        string = f"{margin}level {self.level} table @ {hex(self.addr)}\n"
        for k in sorted(list(self.entries.keys())):
            entry = self.entries[k]
            if type(entry) is Table:
                string += "{}[#{:>4}]\n".format(margin, k)
                string += str(entry)
            else:
                string += "{}[#{:>4}] 0x{:>012}-0x{:>012}, {}, {}\n".format(
                    margin,
                    k,
                    hex(entry.addr)[2:],
                    hex(entry.addr + entry.length - 1)[2:],
                    "Device" if entry.is_device else "Normal",
                    entry.label
                )
        if not string:
            string = f"{margin}<< empty >>\n"
        return string



def alloc( level:int, va_base:int ) -> Table:
    """
    Allocate space for a new translation table.
    """
    global num_allocated_tables
    addr = args.ttb + num_allocated_tables * args.tg
    t = Table(addr, level, va_base)
    num_allocated_tables = num_allocated_tables + 1
    log.debug(f"allocated table #{num_allocated_tables} @ {hex(addr)}")
    return t
