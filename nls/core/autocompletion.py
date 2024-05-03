from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, cast, List

from nls.core.named import Named
from nls.parsednode import ParsedNode

if TYPE_CHECKING:
    from nls.core.defaultparsednode import DefaultParsedNode
    from nls.core.symbol import Symbol
    from nls.ebnf.rule import Rule


class Purpose(Enum):
    FOR_MENU = 0
    FOR_INSERTION = 1


class Autocompletion(ABC):

    def __init__(self, pn: DefaultParsedNode=None, forSymbol: Symbol=None, symbolName: str=None):
        self._symbolName = pn.name if pn is not None else symbolName
        self._forSymbol = pn.symbol if pn is not None else forSymbol
        self._alreadyEntered = ""

    @property
    def symbolName(self) -> str:
        return self._symbolName

    @property
    def forSymbol(self):
        return self._forSymbol

    @staticmethod
    def literal(pn: DefaultParsedNode, literals: [str], prefix="", suffix=""):
        return [Literal(pn=pn, s=prefix + literal + suffix) for literal in literals]

    @staticmethod
    def literalForSymbol(forSymbol: Symbol, symbolName: str, literals: [str], prefix="", suffix=""):
        return [Literal(forSymbol=forSymbol, symbolName=symbolName, s=prefix + literal + suffix) for literal in literals]

    @staticmethod
    def parameterized(pn: DefaultParsedNode, parameterName: str) -> [Autocompletion]:
        return Parameterized(pn=pn, paramName=parameterName).asArray()

    @staticmethod
    def veto(pn: DefaultParsedNode) -> [Autocompletion]:
        return Veto(pn).asArray()

    @staticmethod
    def doesAutocomplete(pn: DefaultParsedNode) -> [Autocompletion]:
        return DoesAutocomplete(pn).asArray()

    @abstractmethod
    def getCompletion(self, purpose: Purpose) -> str:
        pass

    def isEmptyLiteral(self) -> bool:
        return isinstance(self, Literal) and len(self.getCompletion(Purpose.FOR_INSERTION)) == 0

    def setAlreadyEnteredText(self, alreadyEntered) -> None:
        self._alreadyEntered = alreadyEntered

    def getAlreadyEnteredText(self) -> str:
        return self._alreadyEntered

    def asArray(self) -> [Autocompletion]:
        return [self]


class Literal(Autocompletion):
    def __init__(self, pn: DefaultParsedNode = None, forSymbol: Symbol = None, symbolName: str = None, s: str = None):
        super().__init__(pn, forSymbol, symbolName)
        self._literal = s

    # override abstract method
    def getCompletion(self, purpose: Purpose) -> str:
        return self._literal


class Parameterized(Autocompletion):
    def __init__(self, pn: DefaultParsedNode = None, forSymbol: Symbol = None, symbolName: str = None, paramName: str = None):
        super().__init__(pn, forSymbol, symbolName)
        self._paramName = paramName

    # override abstract method
    def getCompletion(self, purpose: Purpose) -> str:
        return "${" + self._paramName + "}"

    @property
    def paramName(self) -> str:
        return self._paramName


class Veto(Autocompletion):
    VETO = "VETO"

    # override abstract method
    def getCompletion(self, purpose: Purpose) -> str:
        return Veto.VETO


class DoesAutocomplete(Autocompletion):
    # override abstract method
    def getCompletion(self, purpose: Purpose) -> str:
        return "Something"  # the return value for DoesAutocomplete shouldn't matter


class EntireSequence(Autocompletion):
    def __init__(self, pn: DefaultParsedNode = None, forSymbol: Symbol = None, symbolName: str = None, sequence: Rule = None):
        super().__init__(pn, forSymbol, symbolName)
        self._sequence = sequence if pn is None else cast(ParsedNode, pn).getRule()
        self._sequenceOfCompletions: List[List[Autocompletion]] = []

    def add(self, completions: [Autocompletion]) -> None:
        self._sequenceOfCompletions.append(completions)

    def getSequenceOfCompletions(self) -> List[List[Autocompletion]]:
        return self._sequenceOfCompletions

    def getSequence(self) -> Rule:
        return self._sequence

    def addLiteral(self, symbol: Symbol, name: str, completion: str) -> None:
        self.add([Literal(forSymbol=symbol, symbolName=name, s=completion)])

    def addParameterized(self, symbol: Symbol, name: str, parameter: str) -> None:
        self.add([Parameterized(forSymbol=symbol, symbolName=name, paramName=parameter)])

    # override abstract method
    def getCompletion(self, purpose: Purpose) -> str:
        autocompletionString: str = ""
        for i, autocompletions in enumerate(self._sequenceOfCompletions):
            n = len(autocompletions)
            if n > 1:
                autocompletionString = autocompletionString + "${" + self._sequence.getNameForChild(i) + "}"
            elif n == 1:
                if purpose == Purpose.FOR_MENU:
                    ac: Autocompletion = autocompletions[0]
                    if isinstance(ac, Literal):
                        ins = ac.getCompletion(Purpose.FOR_INSERTION)
                    else:
                        ins = "${" + self._sequence.getNameForChild(i) + "}"

                    if ins is None or ins == Named.UNNAMED:
                        ins = "${" + self._sequence.children[i].symbol + "}"

                    autocompletionString += ins
                elif purpose == Purpose.FOR_INSERTION:
                    autocompletionString = autocompletionString + autocompletions[0].getCompletion(purpose)
        return autocompletionString
