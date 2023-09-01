from __future__ import annotations
from typing import TYPE_CHECKING, List

from nls.core.production import Production

if TYPE_CHECKING:
    from nls.ebnf.rule import Rule
    from nls.core.nonterminal import NonTerminal
    from nls.core.symbol import Symbol


class EBNFProduction(Production):
    def __init__(self, rule: Rule, left: NonTerminal, right: List[Symbol]):
        super().__init__(left, right)
        self._rule = rule

    @property
    def rule(self) -> Rule:
        return self._rule
