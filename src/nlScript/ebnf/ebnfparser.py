from __future__ import annotations
from typing import TYPE_CHECKING, List, Callable, cast

from nlScript.core.rdparser import RDParser
from nlScript.ebnf import ebnfparsednodefactory
from nlScript.parsednode import ParsedNode

if TYPE_CHECKING:
    from nlScript.core.bnf import BNF
    from nlScript.core.lexer import Lexer
    from nlScript.core.rdparser import SymbolSequence
    from nlScript.core.defaultparsednode import DefaultParsedNode


class EBNFParser(RDParser):
    def __init__(self, grammar: BNF, lexer: Lexer):
        super().__init__(grammar, lexer, ebnfparsednodefactory.INSTANCE)
        self._parseStartListeners: List[ParseStartListener] = []

    def createParsedTree(self,
                         leafSequence: SymbolSequence,
                         retLast: List[DefaultParsedNode] or List[None]) -> DefaultParsedNode:
        self.fireParsingStarted()
        root = super().createParsedTree(leafSequence, retLast)
        cast(ParsedNode, root).notifyListeners()
        return root

    def addParseStartListener(self, listener: ParseStartListener):
        self._parseStartListeners.append(listener)

    def removeParseStartListener(self, listener: ParseStartListener):
        self._parseStartListeners.remove(listener)

    def fireParsingStarted(self):
        for listener in self._parseStartListeners:
            listener.parsingStarted()


class ParseStartListener:
    def __init__(self, parsingStarted: Callable[[], None]):
        self._parsingStarted = parsingStarted

    def parsingStarted(self) -> None:
        self._parsingStarted()
