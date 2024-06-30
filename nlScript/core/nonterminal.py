from __future__ import annotations

from typing import Set, List, cast

from nlScript.core.production import Production
from nlScript.core.symbol import Symbol
from nlScript.util.randomstring import RandomString
from nlScript.core.named import Named


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

    def uses(self, symbol: Symbol, bnf: BNF, progressing: Set[Production]=None) -> bool:
        from nlScript.core.bnf import BNF
        if progressing is None:
            progressing = set()
        productions: List[Production] = bnf.getProductions(self)
        for p in productions:
            if p in progressing:
                continue
            progressing.add(p)
            rhs: List[Symbol] = p.right
            for rSym in rhs:
                if rSym == symbol:
                    return True
                elif isinstance(rSym, NonTerminal):
                    if cast(NonTerminal, rSym).uses(symbol, bnf, progressing):
                        return True
        return False

    def __str__(self) -> str:
        return "<" + self._symbol + ">"

    @staticmethod
    def makeRandomSymbol() -> str:
        return NonTerminal.rs.nextString()


if __name__ == '__main__':
    nt = NonTerminal()
    print(nt)
    print(nt.isNonTerminal())
