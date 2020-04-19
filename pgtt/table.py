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
from . import mmap


class Table:
    """
    Class representing a translation table.
    """
    _allocated = []


    def __init__( self, level:int=mmu.start_level, va_base:int=0 ):
        """
        Constructor.

        args
        ====

            level
                        level of translation

            va_base
                        base virtual address mapped by entry [0] in this table

        """
        self.addr = args.ttb + len(Table._allocated) * args.tg
        self.level = level
        self.chunk = args.tg << ((3 - self.level) * mmu.table_idx_bits)
        self.va_base = va_base
        self.entries = {}
        Table._allocated.append(self)


    def prepare_next( self, idx:int, va_base:int=None ) -> None:
        """
        Allocate next-level table at entry [idx] if it does not already point
        to a next-level table.

        Leave va_base=None to default to self.va_base + idx * self.chunk.
        """
        if not idx in self.entries:
            self.entries[idx] = Table(
                self.level + 1,
                va_base if not va_base is None else (self.va_base + idx * self.chunk)
            )


    def map( self, region:mmap.Region ) -> None:
        """
        Map a region of memory in this translation table.
        """
        log.debug()
        log.debug(f"mapping region {hex(region.addr)} in level {self.level} table")
        log.debug(region)
        assert(region.addr >= self.va_base)
        assert(region.addr + region.length <= self.va_base + mmu.entries_per_table * self.chunk)

        """
        Calculate number of chunks required to map this region.
        A chunk is the area mapped by each individual entry in this table.
        start_idx is the first entry in this table mapping part of the region.
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
            self.prepare_next(start_idx)
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
            self.prepare_next(start_idx)
            self.entries[start_idx].map(region.copy(length=(self.chunk - underflow)))
            start_idx = start_idx + 1

        """
        Check for any "overflow".
        If so, dispatch the overflow to next-level table and proceed.

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
            self.prepare_next(final_idx, va_base)
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
                self.prepare_next(i)
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
        return string


    @classmethod
    def usage( cls ) -> str:
        """
        Generate memory allocation usage information for the user.
        """
        granule_string = {4*1024:"4K", 16*1024:"16K", 64*1024:"64K"}[args.tg]
        string  = f"this memory map requires {len(cls._allocated)} translation tables\n"
        string += f"each table occupies {granule_string} of memory ({hex(args.tg)} bytes)\n"
        string += f"buffer pointed to by {hex(args.ttb)} must therefore be {len(cls._allocated)}x {granule_string} = {hex(args.tg * len(cls._allocated))} bytes long"
        return string


root = Table()
[root.map(r) for r in mmap.regions]
