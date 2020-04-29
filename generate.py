"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT

Run the arm64-pgtable-tool.
"""

from sys import version_info
if version_info < (3, 8):
    print("arm64-pgtable-tool requires Python 3.8+")
    exit()

try:
    import IntervalTree
except ModuleNotFoundError as e:
    print("arm64-pgtable-tool requires IntervalTree: `pip install intervaltree`")
    exit()

import pgtt
