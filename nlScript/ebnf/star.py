from __future__ import annotations
from typing import TYPE_CHECKING, List, cast

from nlScript.ebnf.rule import Rule
from nlScript.evaluator import ALL_CHILDREN_EVALUATOR
from nlScript.core.production import AstBuilder, ExtensionListener
from nlScript.parsednode import ParsedNode

if TYPE_CHECKING:
    from nlScript.core.nonterminal import NonTerminal
    from nlScript.core.symbol import Symbol
    from nlScript.core.bnf import BNF
    from nlScript.core.defaultparsednode import DefaultParsedNode


class Star(Rule):
    def __init__(self, tgt: NonTerminal or None, child: Symbol):
        super().__init__("star", tgt, [child])
        self.setEvaluator(ALL_CHILDREN_EVALUATOR)

    def getEntry(self) -> Symbol:
        return self.children[0]

    def createBNF(self, grammar: BNF):
        p1 = self.addProduction(grammar, self, self.tgt, [self.getEntry(), self.tgt])
        self.addProduction(grammar, self, self.tgt, [])

        def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
            nthEntry = cast(ParsedNode, parent).nthEntryInParent
            c0 = cast(ParsedNode, children[0])
            c1 = cast(ParsedNode, children[1])

            c0.nthEntryInParent = nthEntry
            c0.name = self.getNameForChild(nthEntry)
            c1.nthEntryInParent = nthEntry + 1
            c1.name = parent.name
        p1.onExtension = ExtensionListener(onExtension)

        def buildAst(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
            parent.addChildren([children[0]])
            parent.addChildren(children[1].children)
        p1.astBuilder = AstBuilder(buildAst)
