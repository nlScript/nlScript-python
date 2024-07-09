from __future__ import annotations

from typing import List, TYPE_CHECKING

import logging

from nlScript.core.nonterminal import NonTerminal
from nlScript.core.terminal import END_OF_INPUT

if TYPE_CHECKING:
    from nlScript.core.production import Production
    from nlScript.core.symbol import Symbol


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BNF:
    ARTIFICIAL_START_SYMBOL = NonTerminal("$'")
    ARTIFICIAL_STOP_SYMBOL = END_OF_INPUT

    def __init__(self, other: BNF = None):
        self._symbols: {Symbol}         = {} if other is None else other._symbols.copy()
        self._productions: [Production] = [] if other is None else other._productions.copy()

    def copy(self):
        return BNF(other=self)

    def reset(self) -> None:
        self._symbols.clear()
        self._productions.clear()

    def removeStartProduction(self):
        for i in range(len(self._productions) - 1, -1, -1):
            if self._productions[i].left == BNF.ARTIFICIAL_START_SYMBOL:
                del(self._productions[i])
                break

    def addProduction(self, p: Production) -> Production:
        try:
            pIdx = self._productions.index(p)
            logger.info("production is already there...", str(self._productions[pIdx]))
            return self._productions[pIdx]
        except ValueError:
            self._productions.append(p)
            self._symbols[p.left.symbol] = p.left
            for s in p.right:
                if not s.isEpsilon():
                    self._symbols[s.symbol] = s
            return p

    def getSymbol(self, symbol: str) -> Symbol:
        ret = self._symbols[symbol]
        if ret is None:
            raise Exception("Could not find symbol " + symbol)
        return ret

    def getProductions(self, left: NonTerminal) -> List[Production]:
        return [p for p in self._productions if p.left == left]

    def __str__(self) -> str:
        return "\n".join(list(map(lambda x: str(x), self._productions))) + "\n"
