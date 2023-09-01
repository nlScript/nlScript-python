from __future__ import annotations

from typing import TYPE_CHECKING

from nls.core.parsednodefactory import ParsedNodeFactory
from nls.parsednode import ParsedNode

if TYPE_CHECKING:
    from nls.core.defaultparsednode import DefaultParsedNode
    from nls.core.matcher import Matcher
    from nls.core.production import Production
    from nls.core.symbol import Symbol


class EBNFParsedNodeFactory(ParsedNodeFactory):
    def __init__(self):
        pass

    def createNode(self, matcher: Matcher, symbol: Symbol, production: Production or None) -> DefaultParsedNode:
        return ParsedNode(matcher, symbol, production)


INSTANCE = EBNFParsedNodeFactory()
