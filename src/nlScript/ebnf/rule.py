from __future__ import annotations
from typing import TYPE_CHECKING, List
from abc import abstractmethod

from nlScript.core.nonterminal import NonTerminal
from nlScript.core.representssymbol import RepresentsSymbol
from nlScript.ebnf.ebnfproduction import EBNFProduction
from nlScript.core.named import Named

if TYPE_CHECKING:
    from nlScript.core.bnf import BNF
    from nlScript.core.symbol import Symbol
    from nlScript.autocompleter import IAutocompleter
    from nlScript.evaluator import IEvaluator
    from nlScript.ebnf.parselistener import ParseListener


class Rule(RepresentsSymbol):
    def __init__(self, typ: str, tgt: NonTerminal or None, children: List[Symbol]):
        self._type = typ
        self._tgt = tgt if tgt is not None else NonTerminal(typ + ":" + NonTerminal.makeRandomSymbol())
        self._children = children
        self._parsedChildNames: List[str] or None = None
        self._evaluator = None
        self._autocompleter = None
        self._onSuccessfulParsed = None

    def withName(self, name: str or None = None) -> NamedRule:
        return NamedRule(self, name)

    @property
    def tgt(self) -> NonTerminal:
        return self._tgt

    # implement abstract method
    def getRepresentedSymbol(self) -> Symbol:
        return self.tgt

    @property
    def children(self) -> List[Symbol]:
        return self._children

    def getEvaluator(self) -> IEvaluator:
        return self._evaluator

    def setEvaluator(self, evaluator: IEvaluator) -> Rule:
        self._evaluator = evaluator
        return self

    def getAutocompleter(self) -> IAutocompleter:
        return self._autocompleter

    def setAutocompleter(self, autocompleter: IAutocompleter) -> Rule:
        self._autocompleter = autocompleter
        return self

    def onSuccessfulParsed(self, listener: ParseListener) -> Rule:
        self._onSuccessfulParsed = listener
        return self

    def getOnSuccessfulParsed(self) -> ParseListener:
        return self._onSuccessfulParsed

    @staticmethod
    def addProduction(grammar: BNF, rule: Rule, left: NonTerminal, right: List[Symbol]) -> EBNFProduction:
        production = EBNFProduction(rule, left, right)
        grammar.addProduction(production)
        return production

    def getNameForChild(self, idx: int) -> str or None:
        if self._parsedChildNames is None:
            return None
        if len(self._parsedChildNames) == 1:
            return self._parsedChildNames[0]
        if idx >= len(self._parsedChildNames):
            return "no name"
        return self._parsedChildNames[idx]

    def setParsedChildNames(self, parsedChildNames: List[str]) -> None:
        self._parsedChildNames = parsedChildNames

    @abstractmethod
    def createBNF(self, grammar: BNF):
        pass


class NamedRule(Named[Rule]):
    def __init__(self, obj: Rule, name: str or None = None):
        super().__init__(obj, name)

    def onSuccessfulParsed(self, listener: ParseListener) -> None:
        self.get().onSuccessfulParsed(listener)
