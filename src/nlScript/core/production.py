from __future__ import annotations

from typing import List, TYPE_CHECKING, Callable

from nlScript.core.terminal import EPSILON

if TYPE_CHECKING:
    from nlScript.core.defaultparsednode import DefaultParsedNode
    from nlScript.core.symbol import Symbol


class AstBuilder:
    def __init__(self, buildAST: Callable[[DefaultParsedNode, List[DefaultParsedNode]], None]):
        self._buildAST = buildAST

    def buildAST(self, parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
        self._buildAST(parent, children)


class DefaultAstBuilder(AstBuilder):
    def buildAST(self, parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
        parent.addChildren(children)


class ExtensionListener:
    def __init__(self, onExtension: Callable[[DefaultParsedNode, List[DefaultParsedNode]], None]):
        self._onExtension = onExtension

    def onExtension(self, parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
        self._onExtension(parent, children)


DEFAULT_ASTBUILDER = AstBuilder(lambda parent, children: parent.addChildren(children))


class Production:
    def __init__(self, left: Symbol, right: List[Symbol]):
        self._left = left
        self._right = Production.removeEpsilon(right)
        self._astBuilder = None
        self._extensionListener = None

    @staticmethod
    def removeEpsilon(arr: List[Symbol]) -> List[Symbol]:
        try:
            arr.remove(EPSILON)
        except ValueError:
            pass
        return arr

    @property
    def left(self) -> Symbol:
        return self._left

    @property
    def right(self) -> List[Symbol]:
        return self._right

    @property
    def astBuilder(self) -> AstBuilder:
        return self._astBuilder

    @astBuilder.setter
    def astBuilder(self, astBuilder: AstBuilder) -> None:
        self._astBuilder = astBuilder

    def buildAST(self, parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
        if self._astBuilder is not None:
            self._astBuilder.buildAST(parent, children)
            return
        parent.addChildren(children)

    def wasExtended(self, parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
        if self._extensionListener is not None:
            self._extensionListener.onExtension(parent, children)

    @property
    def onExtension(self) -> ExtensionListener:
        return self._extensionListener

    @onExtension.setter
    def onExtension(self, listener: ExtensionListener):
        if self._extensionListener is not None:
            raise Exception("ExtensionListener cannot be overwritte")
        self._extensionListener = listener

    def __str__(self) -> str:
        left = str(self.left)
        sb = (50 - len(left)) * " " + left + " -> " + " ".join(map(lambda r: str(r), self._right))
        return sb

    def __eq__(self, other: Production) -> bool:
        # if type(self) != type(other):
        #     return False
        return self._left == other.left and self._right == other.right

    def __ne__(self, other: Production) -> bool:
        return not self == other

    def __hash__(self) -> object:
        return hash(self._left) + 31 * hash(tuple(self._right))
