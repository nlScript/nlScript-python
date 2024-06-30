from __future__ import annotations

from typing import TYPE_CHECKING

from nlScript.core.parsednodefactory import ParsedNodeFactory
from nlScript.parsednode import ParsedNode

if TYPE_CHECKING:
    from nlScript.core.defaultparsednode import DefaultParsedNode
    from nlScript.core.matcher import Matcher
    from nlScript.core.production import Production
    from nlScript.core.symbol import Symbol


class EBNFParsedNodeFactory(ParsedNodeFactory):
    def __init__(self):
        pass

    def createNode(self, matcher: Matcher, symbol: Symbol, production: Production or None) -> DefaultParsedNode:
        return ParsedNode(matcher, symbol, production)


INSTANCE = EBNFParsedNodeFactory()
