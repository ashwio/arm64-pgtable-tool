"""
Copyright (c) 2019 Ash Wilding. All rights reserved.

SPDX-License-Identifier: MIT
"""

# Internal deps
from . import log


class Bitfield:
    """
    Class representing a bitfield in a system register.
    """
    def __init__( self, hi, lo, value=0 ):
        mask = (1 << (hi - lo + 1)) - 1
        self.value = (value & mask) << lo


    def __or__( self, other ):
        """
        Overload logical OR operator to use internal value.
        """
        return self.value | (other.value if type(other) is Bitfield else other)


    def __ror__( self, other ):
        """
        Reuse same overloaded logical OR operator when bitfield is right operand.
        """
        return self.__or__(other)


class Register:
    """
    Class representing a system register.
    """
    def __init__( self, name:str ):
        self.name = name
        self.fields = {}
        self.res1s = []
        log.debug()
        log.debug(f"{name}")


    def field( self, hi:int, lo:int, name:str, value:int ) -> None:
        """
        Add a bitfield to this system register.
        """
        self.fields[name] = Bitfield(hi, lo, value)
        log.debug(f"{self.name}.{name}={value}")


    def res1( self, pos:int ) -> None:
        """
        Add a RES1 bit to this system register.
        """
        self.res1s.append(Bitfield(pos, pos, 1))
        log.debug(f"{self.name}.res1[{pos}]=1")


    def value( self ) -> str:
        """
        Generate the required runtime value for this system register.
        """
        val = 0
        for f in list(self.fields.values()) + self.res1s:
            val = val | f
        log.debug(f"{self.name}={hex(val)}")
        return val
