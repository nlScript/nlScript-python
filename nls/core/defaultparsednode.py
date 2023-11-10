from __future__ import annotations
from typing import TYPE_CHECKING

from nls.core.named import Named
from nls.core.terminal import Terminal, Literal


if TYPE_CHECKING:
    from nls.core.production import Production
    from nls.core.matcher import Matcher
    from nls.core.symbol import Symbol


class DefaultParsedNode:

    def __init__(self, matcher: Matcher, symbol: Symbol, production: Production):
        self._parent: DefaultParsedNode = None
        self._children: list[DefaultParsedNode] = []
        self._matcher = matcher
        self._symbol = symbol
        self._production = production
        self._name: str = None

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def name(self) -> str:
        return self._name if self._name is not None else self._symbol.symbol

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    @property
    def production(self) -> Production:
        return self._production

    @property
    def matcher(self) -> Matcher:
        return self._matcher

    def doesAutocomplete(self) -> bool:
        return self.getAutocompletion(True) is not None

    def getAutocompletion(self, justCheck: bool) -> str or None:
        if self._symbol is None:
            return None

        if isinstance(self._symbol, Literal):
            return self._symbol.symbol

        name: str = self.name
        if name == Named.UNNAMED:
            name = self.symbol.symbol

        if isinstance(self._symbol, Terminal):
            from nls.autocompleter import IAutocompleter
            return IAutocompleter.VETO if len(self.getParsedString()) > 0 else "${" + name + "}"

        return None

    def numChildren(self) -> int:
        return len(self._children)

    @property
    def children(self) -> list:
        return self._children

    def getChildByIndex(self, i: int) -> DefaultParsedNode or None:
        return self._children[i]

    def getChildByName(self, name: str) -> DefaultParsedNode or None:
        for n in self._children:
            if name == n.name:
                return n
        return None

    def getChild(self, arg: int or str):
        if isinstance(arg, int):
            return self.getChildByIndex(arg)
        else:
            return self.getChildByName(arg)

    def addChildren(self, children: list) -> None:
        self._children = self._children + children
        for child in children:
            child._parent = self

    @property
    def parent(self) -> DefaultParsedNode:
        return self._parent

    def removeAllChildren(self) -> None:
        for child in self._children:
            child._parent = None
        self._children.clear()

    def evaluateSelf(self):
        return self.getParsedString()

    def evaluateChildByIndex(self, i: int):
        return self._children[i].evaluateSelf()

    def evaluateChildByNames(self, *names):
        pn = self
        for name in [*names]:
            pn = pn.getChild(name)
            if pn is None:
                return None
        return pn.evaluateSelf()

    def evaluate(self, *arg):
        if len(arg) == 0:
            return self.evaluateSelf()
        elif isinstance(arg[0], int):
            return self.evaluateChildByIndex(arg[0])
        else:
            return self.evaluateChildByNames(*arg)

    def getParsedString(self, *names) -> str:
        pn: DefaultParsedNode = self
        for name in [*names]:
            pn = pn.getChild(name)
            if pn is None:
                return ""
        return pn._matcher.parsed

    def __str__(self) -> str:
        return self.getParsedString()
