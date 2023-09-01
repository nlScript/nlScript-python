from __future__ import annotations


class Range:
    def __init__(self, lower: int, upper: int = -1):
        self._lower = lower
        self._upper = upper if upper != -1 else lower

    @property
    def lower(self) -> int:
        return self._lower

    @property
    def upper(self) -> int:
        return self._upper

    def __eq__(self, other: Range) -> bool:
        if type(self) != type(other):
            return False
        return self._lower == other.lower and self._upper == other.upper

    def __ne__(self, other: Range) -> bool:
        return not self == other

    def __hash__(self):
        return 31 * self.lower + self.upper

    def __str__(self) -> str:
        return "[" + str(self._lower) + " - " + str(self._upper) + "]"


MAX_VALUE = (2 << 30) - 1  # make it compatible with Java

STAR = Range(0, MAX_VALUE)
PLUS = Range(1, MAX_VALUE)
OPTIONAL = Range(0, 1)
