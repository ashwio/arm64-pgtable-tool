"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

"""
Parse command-line arguments.
"""
from . import args

"""
Determine MMU constants incl. runtime values for ttbr0, mair, tcr, and sctlr.
"""
from . import mmu

"""
Parse memory map file into list of non-overlapping Region objects sorted by
ascending base address.
"""
from . import mmap

"""
Generate abstract translation tables in the form of Table objects containing
both Region objects and pointers to next-level Table objects.
"""
from . import table

"""
Generate assembly to program the MMU and translation tables at runtime.
"""
from . import codegen


print(codegen.template)
