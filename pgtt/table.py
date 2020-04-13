"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Internal deps
from . import args
from . import log


num_allocated_tables = 0


class Table:
    def __init__( self, addr:int, level:int ):
        self.addr = addr
        self.level = level
        self.entries = {}


def alloc( level:int ) -> Table:
    global num_allocated_tables
    addr = args.ttb + num_allocated_tables * args.tg
    t = Table(addr, level)
    num_allocated_tables = num_allocated_tables + 1
    log.debug(f"allocated table #{num_allocated_tables} @ {hex(addr)}")
    return t
