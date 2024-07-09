from __future__ import annotations
from typing import TYPE_CHECKING

from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from nlScript.core.symbol import Symbol


class RepresentsSymbol(ABC):

    @abstractmethod
    def getRepresentedSymbol(self) -> Symbol:
        pass
