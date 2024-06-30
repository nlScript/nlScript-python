from __future__ import annotations
from typing import TYPE_CHECKING, List, cast

from nlScript.ebnf.rule import Rule
from nlScript.core.production import AstBuilder, ExtensionListener, DEFAULT_ASTBUILDER
from nlScript.parsednode import ParsedNode

if TYPE_CHECKING:
    from nlScript.core.nonterminal import NonTerminal
    from nlScript.core.symbol import Symbol
    from nlScript.core.bnf import BNF
    from nlScript.core.defaultparsednode import DefaultParsedNode


class Sequence(Rule):
    def __init__(self, tgt: NonTerminal | None, children: List[Symbol]):
        super().__init__("sequence", tgt, children)

    def createBNF(self, grammar: BNF):
        p = self.addProduction(grammar, self, self.tgt, self._children)

        def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
            for idx, child in enumerate(children):
                ch = cast(ParsedNode, child)
                ch.nthEntryInParent = idx
                ch.name = self.getNameForChild(idx)
        p.onExtension = ExtensionListener(onExtension)

        p.astBuilder = DEFAULT_ASTBUILDER
