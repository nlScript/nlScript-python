from __future__ import annotations

from enum import Enum


class ParsingState(Enum):
    SUCCESSFUL = 0
    END_OF_INPUT = 1
    FAILED = 2
    NOT_PARSED = 3

    def isBetterThan(self, other: ParsingState) -> bool:
        if self.value < other.value:
            return True
        if self.value > other.value:
            return False
        return False
