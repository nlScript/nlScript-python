from __future__ import annotations

from abc import ABC, abstractmethod

from nlScript.core.representssymbol import RepresentsSymbol


class Symbol(RepresentsSymbol):
    def __init__(self, symbol: str):
        self._symbol = symbol

    @property
    def symbol(self) -> str:
        return self._symbol

    # overriding abstract method
    def getRepresentedSymbol(self) -> Symbol:
        return self

    @abstractmethod
    def isTerminal(self) -> bool:
        pass

    @abstractmethod
    def isNonTerminal(self) -> bool:
        pass

    @abstractmethod
    def isEpsilon(self) -> bool:
        pass

    def __str__(self) -> str:
        return self._symbol

    def __eq__(self, other: Symbol) -> bool:
        # if type(self) != type(other):
        #     return False
        return self._symbol == other._symbol

    def __ne__(self, other: Symbol) -> bool:
        return not self == other

    def __hash__(self) -> object:
        return hash(self._symbol)
