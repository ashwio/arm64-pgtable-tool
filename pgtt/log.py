"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Internal deps
from . import args


def info( msg:str="" ) -> None:
    print(f"[INFO] {msg if msg else ''}")

def verbose( msg:str="" ) -> None:
    if (args.verbose):
        print(f"[VERBOSE] {msg if msg else ''}")

def debug( msg:str="" ) -> None:
    if (args.debug):
        print(f"[DEBUG] {msg if msg else ''}")

def error( msg:str="" ) -> None:
    print(f"[ERROR] {msg if msg else ''}")
