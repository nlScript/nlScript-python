from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Generic

from nlScript.core.representssymbol import RepresentsSymbol

if TYPE_CHECKING:
    from nlScript.core.symbol import Symbol

T = TypeVar('T', bound=RepresentsSymbol)


class Named(Generic[T]):

    UNNAMED = "UNNAMED"

    def __init__(self, obj: T, name: str or None = None):
        self._object = obj
        self._name = name if name is not None else Named.UNNAMED

    @property
    def name(self) -> str:
        return self._name

    def get(self) -> T:
        return self._object

    def getSymbol(self) -> Symbol:
        return self._object.getRepresentedSymbol()
