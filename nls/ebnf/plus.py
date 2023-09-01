from __future__ import annotations
from typing import TYPE_CHECKING, List, cast

from nls.ebnf.rule import Rule
from nls.evaluator import ALL_CHILDREN_EVALUATOR
from nls.core.production import AstBuilder, ExtensionListener
from nls.parsednode import ParsedNode

if TYPE_CHECKING:
    from nls.core.nonterminal import NonTerminal
    from nls.core.symbol import Symbol
    from nls.core.bnf import BNF
    from nls.core.defaultparsednode import DefaultParsedNode


class Plus(Rule):
    def __init__(self, tgt: NonTerminal, child: Symbol):
        super().__init__("plus", tgt, [child])
        self.setEvaluator(ALL_CHILDREN_EVALUATOR)

    def getEntry(self) -> Symbol:
        return self.children[0]

    def createBNF(self, grammar: BNF):
        p1 = self.addProduction(grammar, self, self.tgt, [self.getEntry(), self.tgt])
        p2 = self.addProduction(grammar, self, self.tgt, [self.getEntry()])

        def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
            nthEntry = cast(ParsedNode, parent).nthEntryInParent
            c0 = cast(ParsedNode, children[0])
            c1 = cast(ParsedNode, children[1])

            c0.nthEntryInParent = nthEntry
            c0.name = self.getNameForChild(nthEntry)
            c1.nthEntryInParent = nthEntry + 1
            c1.name = parent.name
        p1.onExtension = ExtensionListener(onExtension)

        def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
            nthEntry = cast(ParsedNode, parent).nthEntryInParent
            c0 = cast(ParsedNode, children[0])
            c0.nthEntryInParent = nthEntry
            c0.name = self.getNameForChild(nthEntry)
        p2.onExtension = ExtensionListener(onExtension)

        def buildAst(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
            parent.addChildren([children[0]])
            parent.addChildren(children[1].children)
        p1.astBuilder = AstBuilder(buildAst)

        def buildAst(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
            parent.addChildren([children[0]])
        p2.astBuilder = AstBuilder(buildAst)
