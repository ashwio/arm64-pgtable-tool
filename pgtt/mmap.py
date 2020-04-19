"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Standard Python deps
import errno
import re
import sys
from dataclasses import dataclass

# Internal deps
from . import args
from . import log

# External deps
from intervaltree import Interval, IntervalTree


@dataclass
class MemoryRegion:
    """
    Class representing a single region in the memory map.
    """
    lineno: int             # line number in source memory map file
    label: str              # name/label e.g. DRAM, GIC, UART, ...
    addr: int               # base address
    length: int             # length in bytes
    is_device: bool         # True for Device-nGnRnE, False for Normal WB RAWA

    def copy( self, **kwargs ):
        """
        Create a duplicate of this MemoryRegion.
        Use kwargs to override this region's corresponding properties.
        """
        region = MemoryRegion(self.lineno, self.label, self.addr, self.length, self.is_device)
        for kw,arg in kwargs.items():
            region.__dict__[kw] = arg
        return region


class MemoryMap():
    """
    Class representing the user's entire specified memory map.
    This is a wrapper around chaimleib's intervaltree library.
    """

    def __init__( self, map_file:str ):
        self._ivtree = IntervalTree()
        try:
            with open(map_file, "r") as map_file_handle:
                map_file_lines = map_file_handle.readlines()

                """
                Loop through each line in the map file.
                """
                for lineno,line in enumerate(map_file_lines):
                    line = line.strip()
                    log.debug()
                    log.debug(f"parsing line {lineno}: {line}")

                    def abort_bad_region( msg:str, variable ) -> None:
                        """
                        Pretty-print an error message and force-exit the script.
                        """
                        log.error(f"in {map_file_handle} on line {lineno+1}: bad region {msg}: {variable}")
                        log.error(f"    {line}")
                        log.error(f"    {' '*line.find(variable)}{'^'*len(variable)}")
                        sys.exit(errno.EINVAL)

                    """
                    Ensure correct number of fields have been specified.
                    """
                    split_line = line.split(",")
                    if len(split_line) < 4:
                        abort_bad_region("format: incomplete", line)
                    if len(split_line) > 4:
                        abort_bad_region("format: unexpected field(s)", line[line.find(split_line[4]):])
                    (addr, length, attrs, label) = split_line
                    addr = addr.strip()
                    length = length.strip()
                    attrs = attrs.strip()
                    label = label.strip()

                    """
                    Parse region base address.
                    """
                    log.debug(f"parsing base address: {addr}")
                    try:
                        addr = int(addr, base=(16 if addr.startswith("0x") else 10))
                    except ValueError:
                        abort_bad_region("base address", addr)

                    """
                    Parse region length.
                    """
                    log.debug(f"parsing length: {length}")
                    x = re.search(r"(\d+)([KMGT])", length)
                    try:
                        qty = x.group(1)
                        log.debug(f"got qty: {qty}")
                        unit = x.group(2)
                        log.debug(f"got unit: {unit}")
                    except AttributeError:
                        abort_bad_region("length", length)
                    length = int(qty) * 1024 ** ("KMGT".find(unit) + 1)

                    """
                    Fudge region to be mappable at chosen granule size.
                    """
                    misalignment = addr % args.tg
                    if misalignment:
                        addr = addr - misalignment
                        length = length + args.tg
                        log.debug("corrected misalignment, new addr={}, length={}".format(hex(addr), hex(length)))
                    
                    overflow = length % args.tg
                    if overflow:
                        length = length + args.tg - overflow
                        log.debug("corrected overflow, new length={}".format(hex(length)))

                    """
                    Parse region attributes.
                    """
                    log.debug(f"parsing attributes: {attrs}")
                    if not attrs in ["NORMAL", "DEVICE"]:
                        abort_bad_region("attributes", attrs)
                    is_device = (attrs == "DEVICE")
                    log.debug(f"{is_device=}")

                    """
                    Check for overlap with other regions.
                    """
                    log.debug(f"checking for overlap with existing regions")
                    overlap = sorted(self._ivtree[addr:addr+length])
                    if overlap:
                        log.error(f"in {map_file} on line {lineno+1}: region overlaps other regions")
                        log.error(f"    {line}")
                        log.error(f"the overlapped regions are:")
                        [log.error(f"    {map_file_lines[iv.data.lineno-1].strip()} (on line {iv.data.lineno})") for iv in overlap]
                        sys.exit(errno.EINVAL)

                    """
                    Add parsed region to memory map.
                    """
                    r = MemoryRegion(lineno+1, label, addr, length, is_device)
                    self._ivtree.addi(addr, addr+length, r)
                    log.debug(f"added {r}")

        except OSError as e:
            log.error(f"failed to open map file: {e}")
            sys.exit(e.errno)


    def regions( self ):
        """
        Return list of MemoryRegion objects sorted by ascending base address.
        """
        return list(map(lambda r: r[2], sorted(self._ivtree)))
