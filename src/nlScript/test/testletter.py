from __future__ import annotations

from typing import cast, List

from nlScript.core.parsingstate import ParsingState
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertArrayEquals(exp: List[object], real: List[object]):
    if len(exp) != len(real):
        raise Exception("Expected " + str(exp) + ", but got " + str(real))

    if any(map(lambda x, y: x != y, exp, real)):
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def test01():
    hlp = Parser()

    def evaluate1(pn: ParsedNode) -> object:
        l = cast(str, pn.evaluate("l"))
        assertEquals("B", l)
        return None

    hlp.defineSentence("The first character of my name is {l:letter}.", evaluate1)

    def evaluate2(pn: ParsedNode) -> object:
        l = cast(List[object], pn.evaluate("l"))
        assertArrayEquals(["B", "e"], l)
        return None

    hlp.defineSentence("The first two characters of my name are {l:letter:2}.", evaluate2)

    root = hlp.parse("The first character of my name is B.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()

    root = hlp.parse("The first two characters of my name are Be.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


if __name__ == "__main__":
    test01()
