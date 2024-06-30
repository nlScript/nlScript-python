from __future__ import annotations

from typing import TYPE_CHECKING

from abc import ABC, abstractmethod

from nlScript.core.defaultparsednode import DefaultParsedNode

if TYPE_CHECKING:
    from nlScript.core.matcher import Matcher
    from nlScript.core.symbol import Symbol
    from nlScript.core.production import Production


class ParsedNodeFactory(ABC):
    @abstractmethod
    def createNode(self, matcher: Matcher, symbol: Symbol, production: Production or None) -> DefaultParsedNode:
        pass


class DefaultParsedNodeFactory(ParsedNodeFactory):
    # override abstract method
    def createNode(self, matcher: Matcher, symbol: Symbol, production: Production or None) -> DefaultParsedNode:
        return DefaultParsedNode(matcher, symbol, production)


DEFAULT = DefaultParsedNodeFactory()
