"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT

Parse command-line arguments to be accessible by any other importing file in the
project. A module is only actually imported once per Python interpreter instance
so this code only runs once regardless of how many times it is later imported.
"""

# Standard Python deps
import argparse


_parser = argparse.ArgumentParser()

_parser.add_argument(
    "-i",
    metavar="SRC",
    help="input memory map file",
    type=str,
    required=True,
)

_parser.add_argument(
    "-o",
    metavar="DST",
    help="output GNU assembly file",
    type=str,
    required=True,
)

_parser.add_argument(
    "-ttb",
    help="desired translation table base address",
    type=lambda v: int(v, 0),
    required=True,
)

_parser.add_argument(
    "-el",
    help="exception level (default: 2)",
    type=int,
    choices=[1,2,3],
    default=2,
)

_parser.add_argument(
    "-tg",
    help="translation granule (default: 4K)",
    type=str,
    choices=["4K", "16K", "64K"],
    default="4K",
)

_parser.add_argument(
    "-tsz",
    help="address space size (default: 32)",
    type=int,
    choices=[32,36,40,48],
    default=32,
)

_parser.add_argument(
    "-v",
    help="-v for verbose, -vv for debug",
    action="count",
    default=0,
)

_args = _parser.parse_args()

i = _args.i
o = _args.o
ttb = _args.ttb
el = _args.el
tg = {"4K":4*1024, "16K":16*1024, "64K":64*1024}[_args.tg]
tsz = _args.tsz
verbose = _args.v >= 1
debug = _args.v >= 2
