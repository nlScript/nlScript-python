from __future__ import annotations
from typing import TYPE_CHECKING, List, cast

from nlScript.ebnf.rule import Rule
from nlScript.evaluator import FIRST_CHILD_EVALUATOR
from nlScript.core.production import ExtensionListener, DEFAULT_ASTBUILDER
from nlScript.parsednode import ParsedNode

if TYPE_CHECKING:
    from nlScript.core.nonterminal import NonTerminal
    from nlScript.core.symbol import Symbol
    from nlScript.core.bnf import BNF
    from nlScript.core.defaultparsednode import DefaultParsedNode


class Or(Rule):
    def __init__(self, tgt: NonTerminal, children: List[Symbol]):
        super().__init__("or", tgt, children)
        self.setEvaluator(FIRST_CHILD_EVALUATOR)

    def getEntry(self) -> Symbol:
        return self.children[0]

    def createBNF(self, grammar: BNF):
        for idx, option in enumerate(self.children):
            p = self.addProduction(grammar, self, self.tgt, [option])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
                c0 = cast(ParsedNode, children[0])
                c0.nthEntryInParent = idx
                c0.name = self.getNameForChild(idx)
            p.onExtension = ExtensionListener(onExtension)

            p.astBuilder = DEFAULT_ASTBUILDER
