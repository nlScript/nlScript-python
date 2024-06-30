from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from nlScript.parsednode import ParsedNode


class ParseListener:
    def __init__(self, parsed: Callable[[ParsedNode], None]):
        self._parsed = parsed

    def parsed(self, n: ParsedNode) -> None:
        self._parsed(n)
