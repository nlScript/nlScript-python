from __future__ import annotations
from typing import TYPE_CHECKING

from nls.core.defaultparsednode import DefaultParsedNode
from nls.core.parsingstate import ParsingState

from nls.ebnf.ebnfproduction import EBNFProduction

if TYPE_CHECKING:
    from typing import List
    from nls.core.matcher import Matcher
    from nls.core.symbol import Symbol
    from nls.core.production import Production
    from nls.ebnf.rule import Rule
    from nls.core.autocompletion import Autocompletion


class ParsedNode(DefaultParsedNode):
    def __init__(self, matcher: Matcher, symbol: Symbol, production: Production):
        super().__init__(matcher, symbol, production)
        self._nthEntryInParent = 0

    @property
    def nthEntryInParent(self) -> int:
        return self._nthEntryInParent

    @nthEntryInParent.setter
    def nthEntryInParent(self, nthEntry: int) -> None:
        self._nthEntryInParent = nthEntry

    def getRule(self) -> Rule or None:
        production = super().production
        if production is not None and isinstance(production, EBNFProduction):
            return production.rule
        return None

    def parentHasSameRule(self) -> bool:
        thisRule = self.getRule()
        if thisRule is None:
            return False
        parent = self.parent
        if parent is None:
            return False
        parentRule = parent.getRule()
        if parentRule is None:
            return False
        return thisRule == parentRule

    def getAutocompletion(self, justCheck: bool) -> List[Autocompletion] or None:
        rule = self.getRule()
        if rule is not None and rule.getAutocompleter() is not None and not self.parentHasSameRule():
            return rule.getAutocompleter().getAutocompletion(self, justCheck)
        return super().getAutocompletion(justCheck)

    def notifyListeners(self) -> None:
        for child in self.children:
            child.notifyListeners()

        state: ParsingState = self.matcher.state
        if state != ParsingState.SUCCESSFUL and state != ParsingState.END_OF_INPUT:
            return
        rule = self.getRule()
        if rule is not None and not self.parentHasSameRule():
            listener = rule.getOnSuccessfulParsed()
            if listener is not None:
                listener.parsed(self)

    def evaluateSelf(self) -> object:
        rule = self.getRule()
        if rule is not None and rule.getEvaluator() is not None:
            return rule.getEvaluator().evaluate(self)

        return super().evaluateSelf()
