from __future__ import annotations
from nls.core.parsingstate import ParsingState


class Matcher:
    def __init__(self, state: ParsingState, pos: int, parsed: str):
        self._state = state
        self._pos = pos
        self._parsed = parsed

    @property
    def state(self) -> ParsingState:
        return self._state

    @property
    def pos(self) -> int:
        return self._pos

    @property
    def parsed(self) -> str:
        return self._parsed

    def isBetterThan(self, other: Matcher) -> bool:
        if other is None:
            return True
        if self.state.isBetterThan(other.state):
            return True
        if other.state.isBetterThan(self.state):
            return False
        tParsedLength = self.pos + len(self.parsed)
        oParsedLength = other.pos + len(other.parsed)
        return tParsedLength >= oParsedLength

    def __str__(self) -> str:
        return str(self._state) + ": '" + self._parsed + "' (" + str(self._pos) + ")"


if __name__ == '__main__':
    m1 = Matcher(ParsingState.END_OF_INPUT, 0, "bla")
    m2 = Matcher(ParsingState.END_OF_INPUT, 3, "blubb")

    print(m1)
    print(m2)

    m1Better = m1.isBetterThan(m2)
    print("is m1 better than m2? " + str(m1Better))

    m2Better = m2.isBetterThan(m1)
    print("is m2 better than m1? " + str(m2Better))
