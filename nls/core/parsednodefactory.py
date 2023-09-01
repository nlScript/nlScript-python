from __future__ import annotations

from typing import TYPE_CHECKING

from abc import ABC, abstractmethod

from nls.core.defaultparsednode import DefaultParsedNode

if TYPE_CHECKING:
    from nls.core.matcher import Matcher
    from nls.core.symbol import Symbol
    from nls.core.production import Production


class ParsedNodeFactory(ABC):
    @abstractmethod
    def createNode(self, matcher: Matcher, symbol: Symbol, production: Production or None) -> DefaultParsedNode:
        pass


class DefaultParsedNodeFactory(ParsedNodeFactory):
    # override abstract method
    def createNode(self, matcher: Matcher, symbol: Symbol, production: Production or None) -> DefaultParsedNode:
        return DefaultParsedNode(matcher, symbol, production)


DEFAULT = DefaultParsedNodeFactory()
