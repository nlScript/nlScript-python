from __future__ import annotations
from typing import TYPE_CHECKING, List

from nlScript.core.production import Production

if TYPE_CHECKING:
    from nlScript.ebnf.rule import Rule
    from nlScript.core.nonterminal import NonTerminal
    from nlScript.core.symbol import Symbol


class EBNFProduction(Production):
    def __init__(self, rule: Rule, left: NonTerminal, right: List[Symbol]):
        super().__init__(left, right)
        self._rule = rule

    @property
    def rule(self) -> Rule:
        return self._rule
