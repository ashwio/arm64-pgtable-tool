"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Standard Python deps
import math

# Submodules
from . import args
from . import log
from . import mmu
from . import mmap
from . import table



master_table = table.alloc(mmu.start_level, 0)
for region in mmap.MemoryMap(args.i).regions():
    master_table.map(region)

print(master_table)
