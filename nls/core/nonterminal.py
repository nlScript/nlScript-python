from __future__ import annotations

from nls.core.symbol import Symbol
from nls.util.randomstring import RandomString
from nls.core.named import Named


class NonTerminal(Symbol):

    rs = RandomString(8)

    def __init__(self, symbol: str = None):
        super().__init__(symbol if symbol is not None else NonTerminal.makeRandomSymbol())

    # overriding abstract method
    def isTerminal(self) -> bool:
        return False

    # overriding abstract method
    def isNonTerminal(self) -> bool:
        return True

    # overriding abstract method
    def isEpsilon(self) -> bool:
        return False

    def withName(self, name: str = None):
        return Named[NonTerminal](self, name)

    def __str__(self) -> str:
        return "<" + self._symbol + ">"

    @staticmethod
    def makeRandomSymbol() -> str:
        return NonTerminal.rs.nextString()


if __name__ == '__main__':
    nt = NonTerminal()
    print(nt)
    print(nt.isNonTerminal())
