from __future__ import annotations
from typing import TYPE_CHECKING, List, cast

from nls.ebnf.rule import Rule
from nls.evaluator import ALL_CHILDREN_EVALUATOR
from nls.core.production import AstBuilder, ExtensionListener, DEFAULT_ASTBUILDER
from nls.parsednode import ParsedNode

if TYPE_CHECKING:
    from nls.core.nonterminal import NonTerminal
    from nls.core.symbol import Symbol
    from nls.core.bnf import BNF
    from nls.core.defaultparsednode import DefaultParsedNode


class Optional(Rule):
    def __init__(self, tgt: NonTerminal, child: Symbol):
        super().__init__("optional", tgt, [child])
        self.setEvaluator(ALL_CHILDREN_EVALUATOR)

    def getEntry(self) -> Symbol:
        return self.children[0]

    def createBNF(self, grammar: BNF):
        p1 = self.addProduction(grammar, self, self.tgt, [self.getEntry()])
        self.addProduction(grammar, self, self.tgt, [])

        def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
            c0 = cast(ParsedNode, children[0])
            c0.nthEntryInParent = 0
            c0.name = self.getNameForChild(0)
        p1.onExtension = ExtensionListener(onExtension)

        p1.astBuilder = DEFAULT_ASTBUILDER
